#!/usr/bin/env python3
"""Sync song list in index.html and README.md from songs/*/song.typ metadata."""

import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).parent.resolve()
SONGS_DIR  = ROOT / "songs"
ALBUMS_DIR = ROOT / "albums"
INDEX_HTML = ROOT / "index.html"
README_MD  = ROOT / "README.md"
PAGES_BASE = "https://sergiorykov.github.io/music"

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


def parse_block(block: str) -> dict:
    """Parse string/bool fields from a Typst dict block."""
    return {
        "title":             _str(block, "title"),
        "soundcloud":        _str(block, "soundcloud"),
        "soundcloud-embed":  _str(block, "soundcloud-embed"),
        "lyrics-author":     _str(block, "lyrics-author"),
        "lyrics-author-url": _str(block, "lyrics-author-url"),
        "music-author":      _str(block, "music-author"),
        "music-author-url":  _str(block, "music-author-url"),
        "music-date":        _str(block, "music-date"),
        "song-id":           _str(block, "song-id"),
        "album-id":          _str(block, "album-id"),
    }

# keep old name as alias for any future callers
parse_variant_block = parse_block


def _extract_block(text: str, var_name: str) -> str | None:
    """Return the inner content of '#let var_name = (...)' or None."""
    m = re.search(rf'#let {re.escape(var_name)}\s*=\s*\(', text)
    if not m:
        return None
    start = m.end()
    depth = 1
    i = start
    while i < len(text) and depth > 0:
        if   text[i] == '(': depth += 1
        elif text[i] == ')': depth -= 1
        i += 1
    return text[start:i - 1]


def parse_song_dir(song_dir: Path) -> dict:
    """Parse a song folder: song.typ config + per-language lyrics."""
    song_typ = song_dir / "song.typ"
    if not song_typ.exists():
        return {}

    config_text = song_typ.read_text(encoding="utf-8")

    # Shared fields from `about` block (new format)
    about_meta    = {}
    default_lang  = None
    about_block   = _extract_block(config_text, "about")
    if about_block:
        about_meta   = parse_block(about_block)
        default_lang = _str(about_block, "default_language")

    # Language entries from `languages` (new) or `variants` (old)
    container = _extract_block(config_text, "languages") or \
                _extract_block(config_text, "variants") or ""

    variants = {}
    for m in re.finditer(r'^\s{2}(\w+):\s*\((.*?)\n\s{2}\),', container, re.MULTILINE | re.DOTALL):
        lang      = m.group(1)
        lang_meta = parse_block(m.group(2))
        # Language keys override about keys; None values don't clobber
        meta = {k: (lang_meta[k] if lang_meta.get(k) is not None else about_meta.get(k))
                for k in set(about_meta) | set(lang_meta)}
        # Inject derived fields
        meta["lang"]     = lang
        meta["language"] = lang
        meta["default"]  = (lang == default_lang) if default_lang else \
                           _bool(m.group(2), "default_language") or _bool(m.group(2), "default")
        meta["lyrics"]   = extract_lyrics(song_dir / f"{lang}.typ") if (song_dir / f"{lang}.typ").exists() else ""
        variants[lang]   = meta

    return variants


def load_albums() -> list[dict]:
    """Return album metadata list from albums/*/album.typ, sorted by folder name."""
    result = []
    if not ALBUMS_DIR.exists():
        return result
    for folder in sorted(ALBUMS_DIR.iterdir()):
        if not folder.is_dir():
            continue
        album_typ = folder / "album.typ"
        if not album_typ.exists():
            continue
        text  = album_typ.read_text(encoding="utf-8")
        block = _extract_block(text, "album")
        if not block:
            continue
        result.append({
            "id":     _str(block, "id"),
            "album":  _str(block, "album"),
            "year":   _str(block, "album-year"),
            "cover":  _str(block, "cover-image"),
            "folder": folder.name,
        })
    return result


def load_songs() -> list[tuple[str, dict]]:
    """Return list of (folder_name, variants_dict) sorted by folder name."""
    result = []
    for d in sorted(SONGS_DIR.iterdir()):
        if d.is_dir():
            variants = parse_song_dir(d)
            if variants:
                result.append((d.name, variants))
    return result


# ── SoundCloud embed pages ────────────────────────────────────────────────────

SC_DIR = ROOT / "pages"

def write_sc_embed(folder: str, lang: str, embed_url: str) -> Path:
    """Write pages/folder/lang.html containing just the SoundCloud player iframe."""
    out_dir  = SC_DIR / folder
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{lang}.html"
    out_file.write_text(
        "<!DOCTYPE html>\n"
        "<html><head><meta charset=\"UTF-8\">"
        "<style>*{margin:0;padding:0}body{background:#0d0d0d}</style></head>\n"
        "<body>"
        f'<iframe width="100%" height="166" scrolling="no" frameborder="no" allow="autoplay"'
        f' src="{embed_url}"></iframe>'
        "</body></html>\n",
        encoding="utf-8",
    )
    return out_file


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
        f' data-tooltip="Sheet music PDF ({lang})">chords {lang}</a>'
    )

    # Subtext for non-default variants: find the default title
    original_html = ""
    if not is_default:
        default_meta  = next((m for m in variants.values() if m.get("default")),
                             next(iter(variants.values())))
        default_title = default_meta.get("title") or folder
        original_html = f' <span class="song-original">original: {default_title}</span>'

    # Actions area: chords badge + SoundCloud play button
    sc      = meta.get("soundcloud")
    actions = pdf_badge
    if sc:
        uid      = re.sub(r"[^a-z0-9]", "_", f"{folder}_{lang}".lower())
        actions += (
            f'<a class="icon-btn play-btn"'
            f' href="{sc}"'
            f' target="_blank" rel="noopener"'
            f' data-tooltip="Listen on SoundCloud">'
            f"{_svg_play_btn(uid)}</a>"
        )

    # SoundCloud embed widget (only when explicit embed URL is provided)
    sc_embed_url = meta.get("soundcloud-embed")
    sc_embed = ""
    if sc_embed_url:
        write_sc_embed(folder, lang, sc_embed_url)
        sc_page  = f"pages/{quote(folder)}/{lang}.html"
        sc_embed = (
            f'<iframe class="sc-embed" src="{sc_page}"'
            f' width="100%" height="166" scrolling="no" frameborder="no"'
            f' loading="lazy"></iframe>'
        )

    # Lyrics panel
    lyr          = meta.get("lyrics", "")
    lyrics_block = ""
    if sc_embed or lyr:
        escaped      = lyr.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") if lyr else ""
        cred         = _credits_html(meta)
        pre_block    = f"<pre>{escaped}</pre>" if lyr else ""
        lyrics_block = f'\n        <div class="lyrics">{sc_embed}{cred}{pre_block}</div>'

    data_default  = "true" if is_default else "false"
    data_album_id = meta.get("album-id") or ""
    return (
        f'      <li data-lang="{lang}" data-default="{data_default}" data-album-id="{data_album_id}">\n'
        f'        <details class="song-details">\n'
        f'          <summary class="song-row">\n'
        f'            <span class="song-title">{song_name}{original_html}</span>\n'
        f'            <div class="song-actions">{actions}</div>\n'
        f"          </summary>"
        f"{lyrics_block}\n"
        f"        </details>\n"
        f"      </li>"
    )


def _albums_block_html(albums: list[dict]) -> str:
    """Render the albums filter row HTML (replaces <!-- albums:start/end --> markers)."""
    btns = ['        <button class="lang-filter-btn active" data-album="all">all</button>']
    for a in albums:
        label = a["album"] + (" · " + a["year"] if a["year"] else "")
        btns.append(
            f'        <button class="lang-filter-btn" data-album="{a["id"]}">{label}</button>'
        )
    inner = "\n".join(btns)
    return (
        f'    <div class="albums-heading-row">\n'
        f'      <h2>albums</h2>\n'
        f'      <div class="album-filter" id="album-filter">\n'
        f'{inner}\n'
        f'      </div>\n'
        f'    </div>'
    )


def _album_cards_html(albums: list[dict]) -> str:
    """Render horizontal album card strip for the album-cards section."""
    cards = []
    for a in albums:
        cover = a.get("cover")
        if cover:
            img = (
                f'<img src="albums/{quote(a["folder"])}/{cover}"'
                f' class="album-card-cover" alt="{a["album"]}">'
            )
        else:
            img = '<div class="album-card-cover album-card-cover--placeholder"></div>'
        name = a["album"] or ""
        year = a["year"] or ""
        cards.append(
            f'      <button class="album-card" data-album="{a["id"]}">\n'
            f'        {img}\n'
            f'        <div class="album-card-name">{name}</div>\n'
            f'        <div class="album-card-year">{year}</div>\n'
            f'      </button>'
        )
    inner = "\n".join(cards)
    return f'    <div class="album-strip">\n{inner}\n    </div>'


def update_html(songs: list[tuple[str, dict]], albums: list[dict] | None = None) -> bool:
    text  = INDEX_HTML.read_text(encoding="utf-8")

    # Update song items
    items = [
        render_html_variant(folder, lang, meta, variants)
        for folder, variants in songs
        for lang, meta in variants.items()
    ]
    inner     = "\n".join(items)
    new_songs = f"      <!-- songs:start -->\n{inner}\n      <!-- songs:end -->"
    updated = re.sub(
        r"      <!-- songs:start -->.*?      <!-- songs:end -->",
        new_songs,
        text,
        flags=re.DOTALL,
    )

    # Update albums filter block and album cards
    if albums is not None:
        albums_inner = _albums_block_html(albums)
        new_albums   = f"    <!-- albums:start -->\n{albums_inner}\n    <!-- albums:end -->"
        updated = re.sub(
            r"    <!-- albums:start -->.*?    <!-- albums:end -->",
            new_albums,
            updated,
            flags=re.DOTALL,
        )

        cards_inner = _album_cards_html(albums)
        new_cards   = f"    <!-- album-cards:start -->\n{cards_inner}\n    <!-- album-cards:end -->"
        updated = re.sub(
            r"    <!-- album-cards:start -->.*?    <!-- album-cards:end -->",
            new_cards,
            updated,
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
    songs  = load_songs()
    albums = load_albums()
    if not songs:
        print("No songs found.", file=sys.stderr)
        sys.exit(1)

    changed = []
    if update_html(songs, albums):
        changed.append("index.html")
    if update_readme(songs):
        changed.append("README.md")

    if changed:
        print(f"Updated: {', '.join(changed)}")
    else:
        print("Already up to date.")


if __name__ == "__main__":
    main()
