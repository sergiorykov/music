#!/usr/bin/env python3
"""Publish a song: compile .typ -> .pdf using typst."""

import os
import re
import sys
import subprocess
import argparse
from pathlib import Path


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
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"

_HEADER_LINES = 2


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
    # No trailing newline — keeps cursor on last line, prevents terminal scroll
    sys.stdout.write("\n".join(rows))
    sys.stdout.flush()


def _redraw(songs: list[dict], idx: int, lang_sels: list[int]) -> None:
    # \r to column 0, then up (lines-1) rows to reach the first line
    lines = _HEADER_LINES + len(songs)
    sys.stdout.write(f"\r\033[{lines - 1}A")
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

    sys.stdout.write(HIDE_CURSOR)
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
                sys.stdout.write("\n" + SHOW_CURSOR)
                options = ["all"] + songs[idx]["langs"]
                return songs[idx]["folder"], options[lang_sels[idx]]
            elif key == "quit":
                sys.stdout.write("\n" + SHOW_CURSOR)
                return None
    except Exception:
        sys.stdout.write("\n" + SHOW_CURSOR)
        raise

    sys.stdout.write("\n" + SHOW_CURSOR)
    return None


# ── Discovery ─────────────────────────────────────────────────────────────────

def _parse_song_meta(song_typ: Path) -> tuple[str | None, str | None]:
    """Return (default_lang, default_title) from song.typ, or (None, None)."""
    text = song_typ.read_text(encoding="utf-8")
    for m in re.finditer(r'^\s{2}(\w+):\s*\((.*?)\n\s{2}\),', text, re.MULTILINE | re.DOTALL):
        lang, block = m.group(1), m.group(2)
        if re.search(r'\bdefault_language:\s*true\b|\bdefault:\s*true\b', block):
            title_m = re.search(r'title:\s*"([^"]+)"', block)
            return lang, (title_m.group(1) if title_m else None)
    return None, None


def discover_songs(songs_dir: Path) -> list[dict]:
    """One dict per song folder: title (default lang), default lang, ordered langs."""
    result = []
    for folder in sorted(songs_dir.iterdir()):
        if not folder.is_dir():
            continue
        all_langs = sorted(t.stem for t in folder.glob("*.typ") if t.name != "song.typ")
        if not all_langs:
            continue

        default_lang, title = None, None
        song_typ = folder / "song.typ"
        if song_typ.exists():
            default_lang, title = _parse_song_meta(song_typ)

        default_lang = default_lang or all_langs[0]
        title        = title or folder.name

        # Cycle order: default first, then remaining langs sorted
        ordered = [default_lang] + [l for l in all_langs if l != default_lang]

        result.append({"folder": folder.name, "title": title,
                       "default_lang": default_lang, "langs": ordered})
    return result


# ── Compile ───────────────────────────────────────────────────────────────────

def compile_variant(root: Path, folder: str, lang: str) -> bool:
    """Compile one lang variant. Returns True on success."""
    song_file   = root / "songs" / folder / f"{lang}.typ"
    output_dir  = root / "pdf" / folder
    output_file = output_dir / f"{lang}.pdf"

    if not song_file.exists():
        print(c(f"  ERROR: file not found — {song_file}", RED, BOLD))
        return False

    output_dir.mkdir(parents=True, exist_ok=True)
    cmd     = ["typst", "compile", "--root", str(root), str(song_file), str(output_file)]
    cmd_str = " ".join(f'"{a}"' if " " in a else a for a in cmd)
    print(c("  Compiling", BOLD) + c(f"  {cmd_str}", DIM))

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode == 0:
        print(c(f"  ✓ {output_file}", GREEN, BOLD))
        return True
    print(c("  ✗ Compilation failed:", RED, BOLD))
    for line in (result.stderr or result.stdout).strip().splitlines():
        print(c(f"    {line}", RED))
    return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    root      = Path(__file__).parent.resolve()
    songs_dir = root / "songs"

    parser = argparse.ArgumentParser(description="Publish a song variant (typst → pdf)")
    parser.add_argument("song_name", nargs="?", help="Song folder name")
    parser.add_argument("lang",      nargs="?", help="Language code or 'all'", default="all")
    args = parser.parse_args()

    songs = discover_songs(songs_dir)
    if not songs:
        print(c("  No songs found in songs/", RED, BOLD))
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

    print(c("  Song : ", DIM) + c(f"{folder}  {lang}", BOLD, WHITE))
    print()

    song          = next((s for s in songs if s["folder"] == folder), None)
    compile_langs = (song["langs"] if song else [lang]) if lang == "all" else [lang]

    ok = all(compile_variant(root, folder, l) for l in compile_langs)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
