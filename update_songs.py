#!/usr/bin/env python3
"""Sync song list in index.html and README.md from songs/*/song.typ metadata."""

import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).parent.resolve()
SONGS_DIR = ROOT / "songs"
INDEX_HTML = ROOT / "index.html"
README_MD  = ROOT / "README.md"
PAGES_BASE = "https://sergiorykov.github.io/songs"

SVG_PLAY = (
    '<svg width="11" height="13" viewBox="0 0 11 13" fill="white">'
    '<polygon points="0,0 11,6.5 0,13"/>'
    "</svg>"
)
SVG_SC = (
    '<svg width="22" height="11" viewBox="0 0 60 28" fill="white">'
    '<path d="M0 20q0-2 1.4-3.4Q2.8 15.2 5 15.2q.5 0 1 .1.3-3.4 2.8-5.6'
    "Q11.3 7.5 15 7.5q2.4 0 4.4 1.1 2 1.1 3.2 3 1-.4 2.1-.4 2.6 0 4.4 1.8"
    " 1.8 1.8 1.8 4.4 0 2.5-1.8 4.3Q27.3 23.5 24.7 23.5H5q-2.1 0-3.55-1.5"
    'Q0 20.5 0 20z"/>'
    "</svg>"
)

_CHORD_TOKEN = re.compile(
    r'^[A-G][#b]?(?:m(?:aj7|in7)?|7|dim7?|aug|sus[24]|add9)?(?:/[A-G][#b]?)?(?:\([^)]+\))?$'
    r'|^\([^)]+\)$'
)


def _is_chord_line(line: str) -> bool:
    tokens = line.rstrip("\\").split()
    return bool(tokens) and all(_CHORD_TOKEN.match(t) for t in tokens)


def _str(text: str, key: str) -> str | None:
    m = re.search(rf'{re.escape(key)}:\s*"([^"]+)"', text)
    return m.group(1) if m else None


def _bool(text: str, key: str) -> bool:
    m = re.search(rf'{re.escape(key)}:\s*(true|false)', text)
    return m.group(1) == "true" if m else False


def extract_lyrics(lang_file: Path) -> str:
    """Return song lyrics from a lang .typ file, stripping chords and typst markup."""
    text = lang_file.read_text(encoding="utf-8")
    # Find end of #show: song-template.with(...) — single-line or multi-line
    match = re.search(r'#show:.*?song-template\.with\(.*?\)\s*\n', text, re.DOTALL)
    if not match:
        # Fallback: standalone closing paren on its own line
        match = re.search(r'^\)\s*\n', text, re.MULTILINE)
    if not match:
        return ""
    body = text[match.end():]

    lines = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            lines.append("")
            continue
        if _is_chord_line(stripped):
            continue
        lines.append(stripped.rstrip("\\").rstrip())

    result = "\n".join(lines).strip()
    return re.sub(r"\n{3,}", "\n\n", result)


def parse_variant_block(block: str) -> dict:
    """Parse string fields from a single variant block of song.typ."""
    return {
        "title":             _str(block, "title"),
        "default":           _bool(block, "default"),
        "soundcloud":        _str(block, "soundcloud"),
        "lyrics-author":     _str(block, "lyrics-author"),
        "lyrics-author-url": _str(block, "lyrics-author-url"),
        "music-author":      _str(block, "music-author"),
        "music-author-url":  _str(block, "music-author-url"),
        "music-date":        _str(block, "music-date"),
    }


def parse_song_dir(song_dir: Path) -> dict:
    """Parse a song folder: song.typ config + per-language lyrics."""
    song_typ = song_dir / "song.typ"
    if not song_typ.exists():
        return {}

    config_text = song_typ.read_text(encoding="utf-8")

    # Extract each variant block: "  ru: (\n    ...\n  ),"
    variants = {}
    for m in re.finditer(r'^\s{2}(\w+):\s*\((.*?)\n\s{2}\),', config_text, re.MULTILINE | re.DOTALL):
        lang  = m.group(1)
        block = m.group(2)
        lang_file = song_dir / f"{lang}.typ"
        meta = parse_variant_block(block)
        meta["lang"]   = lang
        meta["lyrics"] = extract_lyrics(lang_file) if lang_file.exists() else ""
        variants[lang] = meta

    return variants


def load_songs() -> list[tuple[str, dict]]:
    """Return list of (folder_name, variants_dict) sorted by folder name."""
    result = []
    for d in sorted(SONGS_DIR.iterdir()):
        if d.is_dir():
            variants = parse_song_dir(d)
            if variants:
                result.append((d.name, variants))
    return result


# ── index.html ────────────────────────────────────────────────────────────────

def _credits_html(meta: dict) -> str:
    la  = meta.get("lyrics-author")
    lau = meta.get("lyrics-author-url")
    ma  = meta.get("music-author")
    mau = meta.get("music-author-url")
    md  = meta.get("music-date")
    parts = []
    if la:
        link = f'<a href="{lau}" target="_blank" rel="noopener">{la}</a>' if lau else la
        parts.append(f"Lyrics: {link}")
    if ma:
        ma_link = f'<a href="{mau}" target="_blank" rel="noopener">{ma}</a>' if mau else ma
        parts.append(f"Music: {ma_link}" + (f" · {md}" if md else ""))
    return f'<div class="lyrics-credits">{"  ·  ".join(parts)}</div>\n        ' if parts else ""


def render_html_variant(folder: str, lang: str, meta: dict, variants: dict) -> str:
    """Render one <li> for a single language variant."""
    song_name   = meta.get("title") or folder
    is_default  = meta.get("default", False)

    # PDF badge inline with title
    pdf_href  = f"pdf/{folder}/{lang}.pdf"
    pdf_badge = (
        f'<a class="icon-btn lang-btn"'
        f' href="{pdf_href}"'
        f' target="_blank" rel="noopener"'
        f' data-tooltip="Sheet music PDF ({lang})">{lang}</a>'
    )

    # Subtext for non-default variants: find the default title
    original_html = ""
    if not is_default:
        default_meta  = next((m for m in variants.values() if m.get("default")),
                             next(iter(variants.values())))
        default_title = default_meta.get("title") or folder
        original_html = f' <span class="song-original">original: {default_title}</span>'

    # SoundCloud button (actions area, right side)
    sc      = meta.get("soundcloud")
    actions = ""
    if sc:
        actions = (
            f'<a class="icon-btn sc-btn"'
            f' href="{sc}"'
            f' target="_blank" rel="noopener"'
            f' data-tooltip="Listen on SoundCloud">'
            f"{SVG_PLAY}{SVG_SC}</a>"
        )

    # Lyrics panel
    lyr          = meta.get("lyrics", "")
    lyrics_block = ""
    if lyr:
        escaped      = lyr.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        cred         = _credits_html(meta)
        lyrics_block = f'\n        <div class="lyrics">{cred}<pre>{escaped}</pre></div>'

    data_default = "true" if is_default else "false"
    return (
        f'      <li data-lang="{lang}" data-default="{data_default}">\n'
        f'        <details class="song-details">\n'
        f'          <summary class="song-row">\n'
        f'            <span class="song-title">{song_name}{pdf_badge}{original_html}</span>\n'
        f'            <div class="song-actions">{actions}</div>\n'
        f"          </summary>"
        f"{lyrics_block}\n"
        f"        </details>\n"
        f"      </li>"
    )


def update_html(songs: list[tuple[str, dict]]) -> bool:
    text  = INDEX_HTML.read_text(encoding="utf-8")
    items = [
        render_html_variant(folder, lang, meta, variants)
        for folder, variants in songs
        for lang, meta in variants.items()
    ]
    inner     = "\n".join(items)
    new_block = f"      <!-- songs:start -->\n{inner}\n      <!-- songs:end -->"
    updated = re.sub(
        r"      <!-- songs:start -->.*?      <!-- songs:end -->",
        new_block,
        text,
        flags=re.DOTALL,
    )
    if updated == text:
        return False
    INDEX_HTML.write_text(updated, encoding="utf-8")
    return True


# ── README.md ─────────────────────────────────────────────────────────────────

def render_md_rows(folder: str, variants: dict) -> str:
    encoded = quote(folder)
    br = "<br>"

    def _md_link(name, url): return f"[{name}]({url})" if url else name

    # Song: one line per language — "RU Береги себя"
    titles = br.join(
        f"{lang.upper()} {m.get('title') or folder}"
        for lang, m in variants.items()
    )

    # Sheet music: one line per language — "Chords RU"
    pdf_links = br.join(
        f"[Chords {lang.upper()}]({PAGES_BASE}/pdf/{encoded}/{lang}.pdf)"
        for lang in variants
    )

    # SoundCloud: one line per variant that has it — "Listen RU"
    sc_lines = [
        f"[Listen {lang.upper()}]({m['soundcloud']})"
        for lang, m in variants.items()
        if m.get("soundcloud")
    ]
    sc_links = br.join(sc_lines) if sc_lines else "—"

    # Authors: Lyrics on line 1, Music on line 2 (from first variant that has each)
    la = lau = ma = mau = ld = md = None
    for m in variants.values():
        if la  is None and m.get("lyrics-author"): la,  lau = m["lyrics-author"], m.get("lyrics-author-url")
        if ma  is None and m.get("music-author"):  ma,  mau = m["music-author"],  m.get("music-author-url")
        if ld  is None: ld = m.get("lyrics-date")
        if md  is None: md = m.get("music-date")

    authors = []
    if la:
        entry = f"Lyrics: {_md_link(la, lau)}"
        if ld: entry += f" · {ld}"
        authors.append(entry)
    if ma:
        entry = f"Music: {_md_link(ma, mau)}"
        if md: entry += f" · {md}"
        authors.append(entry)
    authors_col = br.join(authors) if authors else "—"

    return f"| {titles} | {pdf_links} | {sc_links} | {authors_col} |"


def update_readme(songs: list[tuple[str, dict]]) -> bool:
    text = README_MD.read_text(encoding="utf-8")
    header = "| Song | Sheet music | SoundCloud | Authors |\n|------|-------------|------------|---------|"
    rows   = "\n".join(render_md_rows(f, v) for f, v in songs)
    inner  = f"{header}\n{rows}"
    new_block = f"<!-- songs:start -->\n{inner}\n<!-- songs:end -->"
    updated = re.sub(
        r"<!-- songs:start -->.*?<!-- songs:end -->",
        new_block,
        text,
        flags=re.DOTALL,
    )
    if updated == text:
        return False
    README_MD.write_text(updated, encoding="utf-8")
    return True


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    songs = load_songs()
    if not songs:
        print("No songs found.", file=sys.stderr)
        sys.exit(1)

    changed = []
    if update_html(songs):
        changed.append("index.html")
    if update_readme(songs):
        changed.append("README.md")

    if changed:
        print(f"Updated: {', '.join(changed)}")
    else:
        print("Already up to date.")


if __name__ == "__main__":
    main()
