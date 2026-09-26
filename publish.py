#!/usr/bin/env python3
"""Publish a song: build its HTML page and PDF from ChordPro (interactive picker if no args)."""

import os
import sys
import argparse

import build
from songbook import catalog
from songbook.catalog import CatalogError
from songbook.chordpro import ChordProError


# ── ANSI colours ──────────────────────────────────────────────────────────────
RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
CYAN    = "\033[36m"
GREEN   = "\033[32m"
RED     = "\033[31m"
WHITE   = "\033[97m"
BG_BLUE = "\033[44m"


def supports_color() -> bool:
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def c(text: str, *codes: str) -> str:
    if not supports_color():
        return text
    return "".join(codes) + text + RESET


# ── Interactive selector ───────────────────────────────────────────────────────
HIDE_CURSOR   = "\033[?25l"
SHOW_CURSOR   = "\033[?25h"
ALT_ON        = "\033[?1049h"   # switch to alternate screen buffer (no scroll)
ALT_OFF       = "\033[?1049l"   # restore main screen buffer
HOME          = "\033[H"        # cursor to top-left of screen


def _lang_tabs(options: list[str], sel_idx: int, active_row: bool) -> str:
    """Render language tabs: all visible, selected one bright."""
    parts = []
    for i, opt in enumerate(options):
        if i == sel_idx:
            parts.append(c(opt, BOLD, CYAN) if active_row else c(opt, BOLD, WHITE))
        else:
            parts.append(c(opt, DIM))
    return "  " + c("·", DIM) + " " + ("  " if active_row else "  ").join(parts)


def _draw_list(songs: list[dict], selected: int, lang_sels: list[int]) -> None:
    rows = []
    rows.append(f"  {c('Select a song', BOLD, BG_BLUE, WHITE)}")
    rows.append(c("  ↑/↓  navigate   ←/→  language   Enter  confirm   q  cancel", DIM))
    for i, song in enumerate(songs):
        lang_options = ["all"] + song["langs"]
        tabs = _lang_tabs(lang_options, lang_sels[i], i == selected)
        if i == selected:
            rows.append(f"  {c('❯ ', BOLD, CYAN)}{c(song['title'], BOLD, WHITE)}{tabs}")
        else:
            rows.append(c(f"    {song['title']}", DIM) + tabs)
    # \033[K clears to end of line after each row so stale chars don't bleed through
    sys.stdout.write("\033[K\n".join(rows) + "\033[K")
    sys.stdout.flush()


def _redraw(songs: list[dict], idx: int, lang_sels: list[int]) -> None:
    sys.stdout.write(HOME)
    _draw_list(songs, idx, lang_sels)


def _read_key_unix(fd: int):
    import tty, termios
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while True:
            ch = os.read(fd, 1)
            if ch == b"\x1b":
                seq = os.read(fd, 2)
                if   seq == b"[A": yield "up"
                elif seq == b"[B": yield "down"
                elif seq == b"[D": yield "left"
                elif seq == b"[C": yield "right"
            elif ch in (b"\r", b"\n"):
                yield "enter"; return
            elif ch in (b"q", b"\x03"):
                yield "quit"; return
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _read_key_windows():
    import msvcrt
    while True:
        ch = msvcrt.getch()
        if ch in (b"\xe0", b"\x00"):
            ch2 = msvcrt.getch()
            if   ch2 == b"H": yield "up"
            elif ch2 == b"P": yield "down"
            elif ch2 == b"K": yield "left"
            elif ch2 == b"M": yield "right"
        elif ch in (b"\r", b"\n"):
            yield "enter"; return
        elif ch in (b"q", b"\x03"):
            yield "quit"; return


def pick_song(songs: list[dict]) -> tuple[str, str] | None:
    """Arrow-key selector. Returns (folder, lang) or None if cancelled."""
    idx       = 0
    lang_sels = [0] * len(songs)   # every song starts at "all"

    def _exit(restore: bool = True) -> None:
        if restore:
            sys.stdout.write(ALT_OFF + SHOW_CURSOR)
        sys.stdout.flush()

    sys.stdout.write(ALT_ON + HIDE_CURSOR + HOME)
    _draw_list(songs, idx, lang_sels)

    try:
        keys = _read_key_windows() if sys.platform == "win32" else _read_key_unix(sys.stdin.fileno())
        for key in keys:
            if key == "up":
                idx = (idx - 1) % len(songs)
                _redraw(songs, idx, lang_sels)
            elif key == "down":
                idx = (idx + 1) % len(songs)
                _redraw(songs, idx, lang_sels)
            elif key == "left":
                n = 1 + len(songs[idx]["langs"])
                lang_sels[idx] = (lang_sels[idx] - 1) % n
                _redraw(songs, idx, lang_sels)
            elif key == "right":
                n = 1 + len(songs[idx]["langs"])
                lang_sels[idx] = (lang_sels[idx] + 1) % n
                _redraw(songs, idx, lang_sels)
            elif key == "enter":
                _exit()
                options = ["all"] + songs[idx]["langs"]
                return songs[idx]["folder"], options[lang_sels[idx]]
            elif key == "quit":
                _exit()
                return None
    except Exception:
        _exit()
        raise

    _exit()
    return None


# ── Discovery ─────────────────────────────────────────────────────────────────

def discover_songs() -> list[dict]:
    """One dict per song folder: title (default lang), default lang, ordered langs."""
    albums = catalog.load_albums()
    result = []
    for folder in catalog.song_folders():
        try:
            entry = catalog.load_song(folder, albums)
        except (CatalogError, ChordProError):
            langs = sorted(p.stem for p in folder.glob("*.cho"))
            result.append({"folder": folder.name, "title": folder.name + "  (has errors)",
                           "default_lang": langs[0] if langs else "", "langs": langs})
            continue
        result.append({
            "folder":       folder.name,
            "title":        entry.variants[entry.default_language].song.get("title"),
            "default_lang": entry.default_language,
            "langs":        list(entry.variants),
        })
    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Publish a song: ChordPro -> HTML page + PDF")
    parser.add_argument("song_name", nargs="?", help="Song folder name")
    parser.add_argument("lang",      nargs="?", help="Language code or 'all'", default="all")
    args = parser.parse_args()

    songs = discover_songs()
    if not songs:
        print(c("  No songs found in songs/ (a song folder needs song.json)", RED, BOLD))
        sys.exit(1)

    folder: str | None = args.song_name
    lang:   str        = args.lang

    if not folder:
        print()
        choice = pick_song(songs)
        print()
        if choice is None:
            print(c("  Cancelled.", DIM))
            sys.exit(0)
        folder, lang = choice

    if not any(s["folder"] == folder for s in songs):
        print(c(f"  Unknown song folder: {folder}", RED, BOLD))
        sys.exit(1)

    print(c("  Song : ", DIM) + c(f"{folder}  {lang}", BOLD, WHITE))
    cmd = f'python build.py --song "{folder}" --pdf'
    print(c("  Build", BOLD) + c(f"  {cmd}" + (f"   (PDF for '{lang}' only)" if lang != "all" else ""), DIM))

    pages = build.build_html([folder])
    if lang != "all":
        pages = [p for p in pages if p.stem == lang]
        if not pages:
            print(c(f"  No '{lang}' version of {folder}", RED, BOLD))
            sys.exit(1)
    build.build_pdfs(pages)
    print()


if __name__ == "__main__":
    main()
