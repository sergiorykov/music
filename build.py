#!/usr/bin/env python3
"""Build the site from ChordPro sources and JSON metadata.

Outputs (git-ignored except index.html and README.md):
  <ui>/                     home, album pages, song pages per UI language
  print/<song>/<lyrics>.html -> pdf/<author>-<song id>-<lyrics>.pdf
  print/songbook/<ui>.html    -> pdf/<author>-songs-<ui>.pdf   (all songs with chords)
  index.html                root redirect to the visitor's UI language
  README.md                 song table

Usage:
  python build.py                 build all pages + refresh index.html / README.md
  python build.py --pdf           also print PDFs (needs: pip install playwright)
  python build.py --song "Кукла Маша" --pdf
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from pathlib import Path

from songbook import catalog, i18n, pages, render, site
from songbook.catalog import CatalogError
from songbook.chordpro import ChordProError

ROOT = catalog.ROOT

RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
GREEN, YELLOW, RED, CYAN = "\033[32m", "\033[33m", "\033[31m", "\033[36m"


def ok(msg: str) -> None:
    print(f"  {GREEN}✓{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"  {YELLOW}!{RESET} {msg}")


def fail(msg: str) -> None:
    print(f"  {RED}✗{RESET} {msg}")


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def load_catalog(names: list[str] | None) -> tuple[dict, list[catalog.SongEntry]]:
    """Load and validate everything; exit with a readable report on errors."""
    try:
        i18n.validate()
        albums = catalog.load_albums()
    except CatalogError as e:
        fail(str(e))
        sys.exit(1)
    entries: list[catalog.SongEntry] = []
    errors = 0
    for folder in catalog.song_folders():
        if names and folder.name not in names:
            continue
        try:
            entries.append(catalog.load_song(folder, albums))
        except (CatalogError, ChordProError) as e:
            print(f"\n  {BOLD}{folder.name}{RESET}")
            for line in str(e).splitlines():
                fail(line)
            errors += 1
    if not errors and not names:
        try:
            catalog.check_song_slugs(entries)
            catalog.check_language_versions(entries)
        except CatalogError as e:
            fail(str(e))
            errors += 1
    if errors:
        print(f"\n  {RED}{BOLD}{errors} problem(s) found{RESET}\n")
        sys.exit(1)
    return albums, entries


PrintJob = tuple[Path, Path, bool]   # print page, PDF output, page numbers in the footer


def build_html(names: list[str] | None) -> list[PrintJob]:
    """Build every page; return the print jobs for the PDFs."""
    albums, entries = load_catalog(names)
    langs = catalog.ui_languages()
    full = not names
    if full:
        for d in [*langs, "print"]:
            shutil.rmtree(ROOT / d, ignore_errors=True)

    prints: list[PrintJob] = []
    for entry in entries:
        album = albums.get(entry.album_id) if entry.album_id else None
        print(f"\n  {BOLD}{entry.title(entry.original.lang) if entry.original.lang in langs else entry.folder}{RESET}"
              f"  {DIM}{entry.folder} · sung in {', '.join(entry.song_languages)}{RESET}")
        shown: set[str] = set()
        for v in entry.variants.values():
            html, warnings = render.print_page(entry, v, album)
            prints.append((write(ROOT / pages.print_path(entry, v.lang), html),
                           ROOT / pages.pdf_path(entry, v.lang), False))
            kind = "original" if v.is_original else "translation"
            ok(f"{pages.print_path(entry, v.lang)}  {DIM}{kind} · {len(v.song.chords_in_order())} chords · "
               f"key {v.song.get('key')} · capo {v.song.capo}{RESET}")
            for w in warnings:
                if w not in shown:
                    warn(w)
                    shown.add(w)
        for ui in langs:
            html, _ = pages.song_page(ui, entry, album)
            write(ROOT / pages.song_path(entry, ui) / "index.html", html)
        ok(f"{DIM}song pages:{RESET} " + "  ".join(pages.song_path(entry, ui) for ui in langs))

    if full:
        print(f"\n  {BOLD}Site{RESET}")
        album_list = sorted(albums.values(), key=lambda a: a.year, reverse=True)
        for ui in langs:
            write(ROOT / ui / "index.html", pages.home_page(ui, entries, album_list))
            for album in album_list:
                write(ROOT / pages.album_path(album, ui) / "index.html", pages.album_page(ui, album, entries))
        ok(f"home + {len(album_list)} album page(s) × {len(langs)} UI languages  {DIM}{', '.join(langs)}{RESET}")
        for ui in langs:
            html = render.songbook_page(ui, entries, albums)
            prints.append((write(ROOT / pages.songbook_print_path(ui), html), ROOT / pages.songbook_pdf_path(ui), True))
        ok(f"songbook print pages  {DIM}{', '.join(pages.songbook_print_path(ui) for ui in langs)}{RESET}")
        root_changed = (ROOT / "index.html").read_text(encoding="utf-8") != pages.root_redirect() \
            if (ROOT / "index.html").exists() else True
        write(ROOT / "index.html", pages.root_redirect())
        readme_changed = site.update_readme(entries)
        changed = [n for n, c in (("index.html", root_changed), ("README.md", readme_changed)) if c]
        ok(f"{', '.join(changed)}  {DIM}updated{RESET}" if changed else f"index.html, README.md  {DIM}up to date{RESET}")
    return prints


PAGE_NUMBER_FOOTER = (
    '<div style="width:100%;text-align:center;font:8px Georgia,serif;color:#888">'
    '<span class="pageNumber"></span></div>'
)


def build_pdfs(prints: list[PrintJob]) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        fail("playwright is not installed — run: pip install playwright && playwright install chromium")
        sys.exit(1)

    print(f"\n  {BOLD}PDF{RESET}  {DIM}headless Chromium, print media, A5{RESET}")
    with sync_playwright() as pw:
        # CHROMIUM_PATH lets a machine reuse an already installed Chromium build.
        browser = pw.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)
        page = browser.new_page()
        # The SoundCloud player is hidden in print; do not wait for it to load.
        page.route("**/*soundcloud.com/**", lambda route: route.abort())
        for html, out, numbered in prints:
            out.parent.mkdir(parents=True, exist_ok=True)
            print(f"  {DIM}$ chromium --print-to-pdf={rel(out)} {rel(html)}{RESET}")
            page.goto(html.as_uri(), wait_until="networkidle")
            page.emulate_media(media="print")
            page.pdf(
                path=str(out), prefer_css_page_size=True, print_background=True,
                display_header_footer=numbered, header_template="<div></div>",
                footer_template=PAGE_NUMBER_FOOTER,
            )
            ok(rel(out))
        browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pdf", action="store_true", help="also print PDFs via headless Chromium")
    parser.add_argument("--song", action="append", help="build only this song folder (repeatable)")
    args = parser.parse_args()

    started = time.time()
    print(f"\n  {BOLD}{CYAN}songbook build{RESET}  {DIM}ChordPro → HTML{' → PDF' if args.pdf else ''}{RESET}")
    pages = build_html(args.song)
    if args.pdf and pages:
        build_pdfs(pages)
    print(f"\n  {GREEN}{BOLD}Done{RESET} {DIM}in {time.time() - started:.1f}s · {len(pages)} page(s){RESET}\n")


if __name__ == "__main__":
    main()
