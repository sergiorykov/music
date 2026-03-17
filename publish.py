#!/usr/bin/env python3
"""Publish a song: compile .typ -> .pdf using typst."""

import os
import sys
import subprocess
import argparse
from pathlib import Path


# ── ANSI colours ──────────────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
CYAN   = "\033[36m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
BLUE   = "\033[34m"
WHITE  = "\033[97m"
BG_BLUE   = "\033[44m"
BG_DARK   = "\033[48;5;235m"


def supports_color() -> bool:
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def c(text: str, *codes: str) -> str:
    if not supports_color():
        return text
    return "".join(codes) + text + RESET


# ── Interactive selector ───────────────────────────────────────────────────────
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"

# Number of lines _draw_list outputs: 2 header + len(songs)
_HEADER_LINES = 2


def _draw_list(songs: list[str], selected: int) -> None:
    out = sys.stdout
    out.write(f"  {c('Select a song', BOLD, BG_BLUE, WHITE)}\n")
    out.write(c("  ↑/↓  navigate   Enter  confirm   q  cancel\n", DIM))
    for i, name in enumerate(songs):
        if i == selected:
            out.write(f"  {c('❯ ', BOLD, CYAN)}{c(name, BOLD, WHITE)}\n")
        else:
            out.write(c(f"    {name}\n", DIM))
    out.flush()


def _redraw(songs: list[str], idx: int) -> None:
    lines = _HEADER_LINES + len(songs)
    sys.stdout.write(f"\033[{lines}A")   # move cursor up
    _draw_list(songs, idx)


def _read_key_unix(fd: int):
    """Yields 'up', 'down', 'enter', or 'quit' from stdin on Unix."""
    import tty, termios
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while True:
            ch = os.read(fd, 1)
            if ch == b"\x1b":
                seq = os.read(fd, 2)
                if seq == b"[A":
                    yield "up"
                elif seq == b"[B":
                    yield "down"
            elif ch in (b"\r", b"\n"):
                yield "enter"
                return
            elif ch in (b"q", b"\x03"):
                yield "quit"
                return
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _read_key_windows():
    """Yields 'up', 'down', 'enter', or 'quit' from stdin on Windows."""
    import msvcrt
    while True:
        ch = msvcrt.getch()
        if ch in (b"\xe0", b"\x00"):    # special key prefix
            ch2 = msvcrt.getch()
            if ch2 == b"H":
                yield "up"
            elif ch2 == b"P":
                yield "down"
        elif ch in (b"\r", b"\n"):
            yield "enter"
            return
        elif ch in (b"q", b"\x03"):
            yield "quit"
            return


def pick_song(songs: list[str]) -> str | None:
    """Arrow-key selector. Returns chosen song name or None if cancelled."""
    idx = 0
    sys.stdout.write(HIDE_CURSOR)
    _draw_list(songs, idx)

    try:
        if sys.platform == "win32":
            keys = _read_key_windows()
        else:
            keys = _read_key_unix(sys.stdin.fileno())

        for key in keys:
            if key == "up":
                idx = (idx - 1) % len(songs)
                _redraw(songs, idx)
            elif key == "down":
                idx = (idx + 1) % len(songs)
                _redraw(songs, idx)
            elif key == "enter":
                sys.stdout.write(SHOW_CURSOR + "\n")
                return songs[idx]
            elif key == "quit":
                sys.stdout.write(SHOW_CURSOR + "\n")
                return None
    except Exception:
        sys.stdout.write(SHOW_CURSOR + "\n")
        raise

    sys.stdout.write(SHOW_CURSOR + "\n")
    return None


# ── Discovery ─────────────────────────────────────────────────────────────────

def discover_variants(songs_dir: Path) -> list[tuple[str, str]]:
    """Return sorted list of (song_folder, lang) pairs from songs/*/lang.typ."""
    variants = []
    for folder in sorted(songs_dir.iterdir()):
        if not folder.is_dir():
            continue
        for typ in sorted(folder.glob("*.typ")):
            if typ.name != "song.typ":
                variants.append((folder.name, typ.stem))
    return variants


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    root = Path(__file__).parent.resolve()
    songs_dir = root / "songs"

    parser = argparse.ArgumentParser(description="Publish a song variant (typst → pdf)")
    parser.add_argument("song_name", nargs="?", help="Song folder name")
    parser.add_argument("lang", nargs="?", help="Language code (e.g. ru)")
    args = parser.parse_args()

    all_variants = discover_variants(songs_dir)
    if not all_variants:
        print(c("  No songs found in songs/", RED, BOLD))
        sys.exit(1)

    song_name: str | None = args.song_name
    lang: str | None = args.lang

    if not song_name or not lang:
        labels = [f"{folder}  {c(lng, BOLD, CYAN)}" for folder, lng in all_variants]
        print()
        chosen = pick_song(labels)
        print()
        if not chosen:
            print(c("  Cancelled.", DIM))
            sys.exit(0)
        idx = labels.index(chosen)
        song_name, lang = all_variants[idx]

    song_file   = songs_dir / song_name / f"{lang}.typ"
    output_dir  = root / "pdf" / song_name
    output_file = output_dir / f"{lang}.pdf"

    print(c(f"  Song : ", DIM) + c(f"{song_name} / {lang}", BOLD, WHITE))
    print(c(f"  File : ", DIM) + c(str(song_file), CYAN))
    print()

    if not song_file.exists():
        print(c(f"  ERROR: file not found — {song_file}", RED, BOLD))
        print(c("  Available:", YELLOW))
        for folder, lng in all_variants:
            print(f"    {c('·', DIM)} {folder} / {lng}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = ["typst", "compile", "--root", str(root), str(song_file), str(output_file)]
    print(c("  Compiling", BOLD) + c(f"  {' '.join(cmd)}", DIM))
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print(c(f"  ✓ Done: {output_file}", GREEN, BOLD))
    else:
        print(c("  ✗ Compilation failed:", RED, BOLD))
        err = (result.stderr or result.stdout).strip()
        for line in err.splitlines():
            print(c(f"    {line}", RED))
        sys.exit(1)


if __name__ == "__main__":
    main()
