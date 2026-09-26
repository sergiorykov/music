"""Site index: regenerate marked blocks of index.html and README.md from the catalog.

index.html and README.md are hand-written; only the regions between
<!-- songs:start --> / <!-- songs:end --> (and albums markers) are generated.
"""

from __future__ import annotations

import re
from html import escape
from pathlib import Path
from urllib.parse import quote

from . import chordpro
from .catalog import ROOT, Album, SongEntry

INDEX_HTML = ROOT / "index.html"
README_MD = ROOT / "README.md"
EMBED_DIR = ROOT / "pages"
PAGES_BASE = "https://sergiorykov.github.io/music"


# ── Plain lyrics (no chords) ──────────────────────────────────────────────────

def plain_lyrics(song: chordpro.Song) -> str:
    """Lyrics text for the index: sections separated by blank lines, chorus repeats expanded."""
    blocks: list[str] = []
    last_chorus: str | None = None
    for block in song.body:
        if isinstance(block, chordpro.Section):
            lines = []
            for item in block.items:
                if isinstance(item, chordpro.Line):
                    text = "".join(s.text for s in item.segments).strip()
                    if text:
                        lines.append(text)
                elif isinstance(item, chordpro.Blank) and lines:
                    lines.append("")
            text = "\n".join(lines).strip()
            if text:
                blocks.append(text)
                if block.kind == "chorus":
                    last_chorus = text
        elif isinstance(block, chordpro.ChorusRef) and last_chorus:
            blocks.append(last_chorus)
    return "\n\n".join(blocks)


# ── SoundCloud embed pages ────────────────────────────────────────────────────

def write_embed_page(folder: str, lang: str, embed_url: str) -> str:
    """Write pages/<folder>/<lang>.html with just the SoundCloud player; return its URL path."""
    out = EMBED_DIR / folder / f"{lang}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "<!DOCTYPE html>\n"
        "<html><head><meta charset=\"UTF-8\">"
        "<style>*{margin:0;padding:0}body{background:#0d0d0d}</style></head>\n"
        "<body>"
        f'<iframe width="100%" height="166" scrolling="no" frameborder="no" allow="autoplay"'
        f' src="{escape(embed_url)}"></iframe>'
        "</body></html>\n",
        encoding="utf-8",
    )
    return f"pages/{quote(folder)}/{lang}.html"


# ── index.html ────────────────────────────────────────────────────────────────

def _svg_play_btn(uid: str) -> str:
    """SoundCloud-style circular play button SVG. uid keeps gradient id unique per song."""
    gid = f"scg_{uid}"
    return (
        f'<svg width="32" height="32" viewBox="0 0 43 43" xmlns="http://www.w3.org/2000/svg">'
        f'<defs><linearGradient id="{gid}" x1="0%" y1="0%" x2="0%" y2="100%">'
        f'<stop offset="0%" stop-color="#ff5500" stop-opacity="1"/>'
        f'<stop offset="100%" stop-color="#ff2200" stop-opacity="1"/>'
        f'</linearGradient></defs>'
        f'<circle fill="url(#{gid})" stroke="#cc4400" cx="21.5" cy="21.5" r="21"/>'
        f'<path fill="#fff" d="M31,21.5L17,33l2.5-11.5L17,10L31,21.5z"/>'
        f'</svg>'
    )


def _a(text: str, url: str | None) -> str:
    return f'<a href="{escape(url)}" target="_blank" rel="noopener">{escape(text)}</a>' if url else escape(text)


def _credits_html(entry: SongEntry, song: chordpro.Song) -> str:
    parts = []
    if song.get("lyricist"):
        parts.append(f"Lyrics: {_a(song.get('lyricist'), song.get('lyricist_url'))}")
    if song.get("composer"):
        music = f"Music: {_a(song.get('composer'), entry.data.get('music-author-url'))}"
        music += f" · {escape(entry.display_date)}"
        parts.append(music)
    return f'<div class="lyrics-credits">{"  ·  ".join(parts)}</div>' if parts else ""


def _song_item(entry: SongEntry, lang: str) -> str:
    song = entry.variants[lang].song
    is_default = lang == entry.original.lang
    folder_q = quote(entry.folder)
    title = escape(song.get("title"))

    original = ""
    if not is_default:
        default_title = entry.variants[entry.original.lang].song.get("title")
        original = f' <span class="song-original">original: {escape(default_title)}</span>'

    actions = (
        f'<a class="icon-btn lang-btn" href="web/{folder_q}/{lang}.html"'
        f' data-tooltip="Chords &amp; lyrics ({lang})">chords {lang}</a>'
        f'<a class="icon-btn lang-btn" href="pdf/{folder_q}/{lang}.pdf" target="_blank" rel="noopener"'
        f' data-tooltip="Printable PDF ({lang})">pdf</a>'
    )
    sc = entry.data.get("soundcloud")
    if sc:
        uid = re.sub(r"[^a-z0-9]", "_", f"{entry.data.get('song-id', entry.folder)}_{lang}".lower())
        actions += (
            f'<a class="icon-btn play-btn" href="{escape(sc)}" target="_blank" rel="noopener"'
            f' data-tooltip="Listen on SoundCloud">{_svg_play_btn(uid)}</a>'
        )

    embed = ""
    if entry.data.get("soundcloud-embed"):
        src = write_embed_page(entry.folder, lang, entry.data["soundcloud-embed"])
        embed = (
            f'<iframe class="sc-embed" src="{src}" width="100%" height="166" scrolling="no"'
            f' frameborder="no" loading="lazy"></iframe>'
        )
    lyrics = escape(plain_lyrics(song))
    album_id = entry.album_id or ""

    return (
        f'      <li data-lang="{lang}" data-default="{"true" if is_default else "false"}" data-album-id="{album_id}">\n'
        f'        <details class="song-details">\n'
        f'          <summary class="song-row">\n'
        f'            <span class="song-title">{title}{original}</span>\n'
        f'            <div class="song-actions">{actions}</div>\n'
        f'          </summary>\n'
        f'        <div class="lyrics">{embed}{_credits_html(entry, song)}<pre>{lyrics}</pre></div>\n'
        f'        </details>\n'
        f'      </li>'
    )


def _albums_filter_html(albums: list[Album]) -> str:
    btns = ['        <button class="lang-filter-btn active" data-album="all">all</button>']
    for a in albums:
        label = a.title("ru") + (f" · {a.year}" if a.year else "")
        btns.append(f'        <button class="lang-filter-btn" data-album="{a.id}">{escape(label)}</button>')
    return (
        '    <div class="albums-heading-row">\n'
        '      <h2>albums</h2>\n'
        '      <div class="album-filter" id="album-filter">\n'
        + "\n".join(btns) + "\n"
        '      </div>\n'
        '    </div>'
    )


def _album_cards_html(albums: list[Album]) -> str:
    cards = []
    for a in albums:
        name = escape(a.title("ru"))
        cover = a.data.get("cover-image")
        img = (
            f'<img src="albums/{quote(a.folder)}/{cover}" class="album-card-cover" alt="{name}">'
            if cover else '<div class="album-card-cover album-card-cover--placeholder"></div>'
        )
        cards.append(
            f'      <button class="album-card" data-album="{a.id}">\n'
            f'        {img}\n'
            f'        <div class="album-card-name">{name}</div>\n'
            f'        <div class="album-card-year">{escape(a.year)}</div>\n'
            f'      </button>'
        )
    return '    <div class="album-strip">\n' + "\n".join(cards) + "\n    </div>"


def _replace_block(text: str, marker: str, indent: str, inner: str) -> str:
    pattern = rf"{indent}<!-- {marker}:start -->.*?{indent}<!-- {marker}:end -->"
    if not re.search(pattern, text, flags=re.DOTALL):
        raise ValueError(f"marker <!-- {marker}:start/end --> not found")
    block = f"{indent}<!-- {marker}:start -->\n{inner}\n{indent}<!-- {marker}:end -->"
    return re.sub(pattern, lambda _: block, text, flags=re.DOTALL)


def update_index(entries: list[SongEntry], albums: list[Album]) -> bool:
    text = INDEX_HTML.read_text(encoding="utf-8")
    items = "\n".join(_song_item(e, lang) for e in entries for lang in e.variants)
    updated = _replace_block(text, "songs", "      ", items)
    updated = _replace_block(updated, "albums", "    ", _albums_filter_html(albums))
    updated = _replace_block(updated, "album-cards", "    ", _album_cards_html(albums))
    if updated == text:
        return False
    INDEX_HTML.write_text(updated, encoding="utf-8")
    return True


# ── README.md ─────────────────────────────────────────────────────────────────

def _md_link(text: str, url: str | None) -> str:
    return f"[{text}]({url})" if url else text


def _readme_row(entry: SongEntry) -> str:
    br = "<br>"
    folder_q = quote(entry.folder)
    titles = br.join(f"{lang.upper()} {v.song.get('title')}" for lang, v in entry.variants.items())
    sheets = br.join(
        f"[Chords {lang.upper()}]({PAGES_BASE}/web/{folder_q}/{lang}.html)"
        f" · [PDF]({PAGES_BASE}/pdf/{folder_q}/{lang}.pdf)"
        for lang in entry.variants
    )
    sc = entry.data.get("soundcloud")
    listen = _md_link("Listen", sc) if sc else "—"

    song = entry.variants[entry.original.lang].song
    authors = []
    if song.get("lyricist"):
        authors.append(f"Lyrics: {_md_link(song.get('lyricist'), song.get('lyricist_url'))}")
    if song.get("composer"):
        music = f"Music: {_md_link(song.get('composer'), entry.data.get('music-author-url'))}"
        music += f" · {entry.display_date}"
        authors.append(music)
    return f"| {titles} | {sheets} | {listen} | {br.join(authors) or '—'} |"


def update_readme(entries: list[SongEntry]) -> bool:
    text = README_MD.read_text(encoding="utf-8")
    table = "| Song | Sheet music | SoundCloud | Authors |\n|------|-------------|------------|---------|\n"
    table += "\n".join(_readme_row(e) for e in entries)
    updated = _replace_block(text, "songs", "", table)
    if updated == text:
        return False
    README_MD.write_text(updated, encoding="utf-8")
    return True


def write_all(entries: list[SongEntry], albums: list[Album]) -> list[Path]:
    changed = []
    if update_index(entries, albums):
        changed.append(INDEX_HTML)
    if update_readme(entries):
        changed.append(README_MD)
    return changed
