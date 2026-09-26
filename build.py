#!/usr/bin/env python3
"""Build song pages from ChordPro sources: web/<Song>/<lang>.html and pdf/<Song>/<lang>.pdf.

Usage:
  python build.py                 build HTML for all songs + refresh index.html / README.md
  python build.py --pdf           also print PDFs (needs: pip install playwright)
  python build.py --song "Кукла Маша" --pdf
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from songbook import catalog, i18n, site
from songbook.catalog import CatalogError
from songbook.chordpro import ChordProError
from songbook.render import render_page

ROOT = catalog.ROOT
WEB_DIR = ROOT / "web"
PDF_DIR = ROOT / "pdf"

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


def build_html(names: list[str] | None) -> list[Path]:
    settings = catalog.load_settings()
    try:
        i18n.validate()
    except CatalogError as e:
        fail(str(e))
        sys.exit(1)
    albums = catalog.load_albums()
    entries: list[catalog.SongEntry] = []
    pages: list[Path] = []
    errors = 0

    for folder in catalog.song_folders():
        if names and folder.name not in names:
            continue
        print(f"\n  {BOLD}{folder.name}{RESET}")
        try:
            entry = catalog.load_song(folder, albums)
        except (CatalogError, ChordProError) as e:
            for line in str(e).splitlines():
                fail(line)
            errors += 1
            continue

        entries.append(entry)
        album = albums.get(entry.album_id) if entry.album_id else None
        for lang, variant in entry.variants.items():
            html, warnings = render_page(entry, variant, album, settings)
            out = WEB_DIR / folder.name / f"{lang}.html"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(html, encoding="utf-8")
            pages.append(out)
            chords = len(variant.song.chords_in_order())
            ok(f"{rel(out)}  {DIM}{chords} chords · key {variant.song.get('key')} · capo {variant.song.capo}{RESET}")
            for w in warnings:
                warn(w)

    if errors:
        print(f"\n  {RED}{BOLD}{errors} song(s) failed{RESET}\n")
        sys.exit(1)

    if not names:
        print(f"\n  {BOLD}Site{RESET}")
        changed = site.write_all(entries, list(albums.values()))
        for path in changed:
            ok(f"{rel(path)}  {DIM}updated{RESET}")
        if not changed:
            ok(f"index.html, README.md  {DIM}up to date{RESET}")
    return pages


def build_pdfs(pages: list[Path]) -> None:
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
        for html in pages:
            out = PDF_DIR / html.parent.name / f"{html.stem}.pdf"
            out.parent.mkdir(parents=True, exist_ok=True)
            print(f"  {DIM}$ chromium --print-to-pdf={rel(out)} {rel(html)}{RESET}")
            page.goto(html.as_uri(), wait_until="networkidle")
            page.emulate_media(media="print")
            page.pdf(path=str(out), prefer_css_page_size=True, print_background=True)
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
