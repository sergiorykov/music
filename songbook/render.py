"""Song rendering: chord tables, chord-over-lyrics sheet, lyrics blocks and the print page."""

from __future__ import annotations

import functools
import hashlib
import json
import re
from html import escape
from urllib.parse import quote

from . import chordpro, diagram, i18n
from .catalog import ROOT, Album, SongEntry, Variant, load_settings, ui_languages
from .paths import original_ui, page_url, song_path
from .chords import Chord
from .voicings import lookup

MODES = ("shape", "sound")   # shape: as written, played with capo; sound: concert pitch, no capo
SEMITONES = range(12)

ASSETS = ROOT / "assets"
FONTS_URL = (
    "https://fonts.googleapis.com/css2?family=PT+Serif:ital,wght@0,400;0,700;1,400"
    "&family=JetBrains+Mono:wght@700&display=swap"
)


class RenderError(Exception):
    pass


# ── Chord state tables ────────────────────────────────────────────────────────

def chord_tables(song: chordpro.Song) -> tuple[dict, dict, dict, list[str]]:
    """Precompute chord names, keys and diagrams for every mode x transposition.

    Returns (names, keys, diagrams, warnings):
      names[mode][t]  -> list of chord names, indexed like song.chords_in_order()
      keys[mode][t]   -> key name
      diagrams[name]  -> inline SVG
    """
    written = song.chords_in_order()
    if not written:                                  # lyrics only (e.g. a lyrics translation)
        return {m: [[] for _ in SEMITONES] for m in MODES}, {m: ["" for _ in SEMITONES] for m in MODES}, {}, []
    parsed = [Chord.parse(w, song.german) for w in written]
    names: dict = {m: [] for m in MODES}
    keys: dict = {m: [] for m in MODES}
    diagrams: dict[str, str] = {}
    warnings: list[str] = []

    for mode in MODES:
        for t in SEMITONES:
            shift = t + (song.capo if mode == "sound" else 0)
            key = song.key.transpose(shift)
            keys[mode].append(key.name())
            row = []
            for w, chord in zip(written, parsed):
                name = w if shift % 12 == 0 else chord.transpose(shift).name(key.flats)
                row.append(name)
                if name not in diagrams:
                    v = lookup(chord, song.defines.get(w), shift)
                    if v is not None:
                        diagrams[name] = diagram.render(v)
                    elif mode == "shape" and t == 0:
                        warnings.append(f"no fingering for '{w}' — add a {{define: {w} ...}}")
            names[mode].append(row)
    return names, keys, diagrams, warnings


# ── Lyrics + chords ───────────────────────────────────────────────────────────

_SPACE = object()


def _words(line: chordpro.Line) -> list:
    """Group segments into words so a line never wraps inside a word."""
    words: list = []
    cur: list[tuple[str | None, str]] = []

    def flush() -> None:
        nonlocal cur
        if cur:
            words.append(cur)
            cur = []

    for seg in line.segments:
        chord = seg.chord
        pieces = re.findall(r"\S+|\s+", seg.text)
        if not pieces and chord:
            cur.append((chord, ""))
            continue
        for piece in pieces:
            if piece.isspace():
                if chord:
                    cur.append((chord, ""))
                    chord = None
                flush()
                words.append(_SPACE)
            else:
                cur.append((chord, piece))
                chord = None
    flush()

    # Keep chord-only words (e.g. a closing "[C]") on the same row as the preceding word.
    merged: list = []
    for word in words:
        chord_only = word is not _SPACE and not any(text for _, text in word)
        if (chord_only and len(merged) >= 2 and merged[-1] is _SPACE
                and any(text for _, text in merged[-2])):
            merged.pop()
            merged[-1] = merged[-1] + [(None, " ")] + word
        else:
            merged.append(word)
    return merged


def _cell(chord: str | None, text: str, index: dict[str, int]) -> str:
    """One chord-over-text cell; chordless cells keep an empty chord row for alignment."""
    ly = escape(text) if text else "&#8203;"
    ch = f'<b class="ch" data-i="{index[chord]}">{escape(chord)}</b>' if chord else '<b class="ch ch--none"></b>'
    return f'<span class="c">{ch}<span class="ly">{ly}</span></span>'


def _line_html(line: chordpro.Line, index: dict[str, int]) -> str:
    if not line.has_chords:
        text = "".join(s.text for s in line.segments)
        return f'<div class="ln">{escape(text)}</div>'
    chords_only = not "".join(s.text for s in line.segments).strip()
    out = []
    for word in _words(line):
        if word is _SPACE:
            out.append(" ")
            continue
        cells = "".join(_cell(chord, text, index) for chord, text in word)
        out.append(f'<span class="w">{cells}</span>')
    cls = "ln ln--ch ln--only" if chords_only else "ln ln--ch"
    return f'<div class="{cls}">{"".join(out).strip()}</div>'


def _section_html(sec: chordpro.Section, index: dict[str, int], labels: dict, chords: bool = True) -> str:
    items = list(sec.items)
    while items and isinstance(items[-1], chordpro.Blank):
        items.pop()
    body = []
    for item in items:
        if isinstance(item, chordpro.Line):
            if chords:
                body.append(_line_html(item, index))
            elif text := "".join(s.text for s in item.segments).strip():
                body.append(f'<div class="ln">{escape(text)}</div>')
        elif isinstance(item, chordpro.Comment):
            cls = "cmt cmt--i" if item.italic else "cmt"
            body.append(f'<div class="{cls}">{escape(item.text)}</div>')
        elif isinstance(item, chordpro.Blank):
            body.append('<div class="gap"></div>')
    if not chords and not any('class="ln"' in b or 'class="cmt' in b for b in body):
        return ""  # e.g. an instrumental intro: chords only
    label = sec.label or (labels.get(sec.kind) if sec.kind in ("chorus", "bridge") else None)
    head = f'<div class="sec-label">{escape(label)}</div>' if label else ""
    return f'<section class="sec sec--{sec.kind}">{head}{"".join(body)}</section>'


def sheet_html(song: chordpro.Song, labels: dict, chords: bool = True) -> str:
    """Sections of a song; `chords=False` gives the lyrics only (song lists)."""
    index = {name: i for i, name in enumerate(song.chords_in_order())}
    out = []
    for block in song.body:
        if isinstance(block, chordpro.Section):
            if html := _section_html(block, index, labels, chords):
                out.append(html)
        elif isinstance(block, chordpro.ChorusRef):
            label = block.label or labels["chorus"]
            out.append(f'<section class="sec sec--ref"><div class="sec-label">{escape(label)}</div></section>')
        elif isinstance(block, chordpro.PageBreak) and chords:
            out.append('<div class="page-break"></div>')
    return "\n".join(out)


# ── Shared page parts ─────────────────────────────────────────────────────────

@functools.cache
def _asset_version(name: str) -> str:
    return hashlib.sha1((ASSETS / name).read_bytes()).hexdigest()[:10]


def asset(up: str, name: str) -> str:
    """URL of a file in assets/ with a content hash, so browsers never mix new pages with stale CSS/JS."""
    return f"{up}assets/{name}?v={_asset_version(name)}"


def html_head(title: str, up: str, css: list[str], lang: str, extra: str = "") -> str:
    """`extra`: more head tags (SEO metadata from songbook.seo)."""
    links = "".join(f'<link rel="stylesheet" href="{asset(up, c)}">' for c in css)
    return (
        f'<!DOCTYPE html>\n<html lang="{lang}">\n<head>\n<meta charset="UTF-8">\n'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<title>{escape(title)}</title>\n{extra}'
        f'<link rel="icon" type="image/png" href="{up}favicon.png">\n'
        f'<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        f'<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        f'<link rel="stylesheet" href="{FONTS_URL}">\n{links}\n</head>\n'
    )


def link(text: str, url: str | None) -> str:
    t = escape(text)
    return f'<a href="{escape(url)}" target="_blank" rel="noopener">{t}</a>' if url else t


def credits_html(entry: SongEntry, ui: str) -> str:
    """Lyricist and composer names in the metadata language; links and dates from the sources."""
    t = i18n.Translator(ui)
    meta = entry.meta(ui)
    original = entry.original.song
    lines = []
    lyricist = meta.get("lyricist") or original.get("lyricist")
    if lyricist:
        parts = [link(lyricist, original.get("lyricist_url"))]
        if original.get("lyrics_date"):
            parts.append(escape(original.get("lyrics_date")))
        for src in entry.lyrics_sources:
            parts.append(link(src["label"][ui], src["url"]))
        lines.append(f'<div>{t("lyrics")}: {" · ".join(parts)}</div>')
    composer = meta.get("composer") or original.get("composer")
    if composer:
        parts = [link(composer, entry.data.get("music-author-url")), escape(entry.display_date)]
        lines.append(f'<div>{t("music")}: {" · ".join(parts)}</div>')
    return "".join(lines)


def credits_plain(entry: SongEntry, ui: str) -> str:
    """Lyricist and composer names and the date, without links (web songbook)."""
    t = i18n.Translator(ui)
    meta = entry.meta(ui)
    original = entry.original.song
    parts = []
    lyricist = meta.get("lyricist") or original.get("lyricist")
    composer = meta.get("composer") or original.get("composer")
    if lyricist:
        parts.append(f'{t("lyrics")}: {escape(lyricist)}')
    if composer:
        parts.append(f'{t("music")}: {escape(composer)}')
    parts.append(escape(entry.display_date))
    return " · ".join(parts)


def web_song_sheet(entry: SongEntry, ui: str, up: str) -> tuple[str, list[str]]:
    """One song of the web songbook: header (cover, title, credits, date, capo / key),
    chord diagrams and the original lyrics with chords — the PDF sheet, on screen."""
    t = i18n.Translator(ui)
    song = entry.original.song
    block, warnings = lyrics_block(entry.original, ui, hidden=False)
    cover = entry.cover_src(up)
    cover_html = f'<img class="cover" src="{escape(cover)}" alt="">' if cover else ""
    original = song.get("title")
    title = entry.title(ui)
    sub = f'<div class="subtitle">{escape(original)}</div>' if original and original != title else ""
    capo = f'{t("capo")}: <b>{t("capo_fret", capo=song.capo)}</b> · ' if song.capo else ""
    key = f'{t("key")}: {escape(song.key.name())}' if song.get("key") else ""
    html = (
        f'<header class="head">{cover_html}<div class="head-text"><h1>{escape(title)}</h1>{sub}'
        f'<div class="credits">{credits_plain(entry, ui)}</div></div></header>\n'
        f'<div class="print-meta">{capo}{key}</div>\n{block}'
    )
    return html, warnings


def chord_controls(song: chordpro.Song, ui: str) -> str:
    """Capo mode and transposition controls (chord mode only)."""
    t = i18n.Translator(ui)
    out = []
    if song.capo:
        out.append(
            f'<div class="ctl"><span class="lbl">{t("capo")}</span>'
            f'<div class="seg" role="group">'
            f'<button type="button" data-mode="shape" class="on">{t("capo_fret", capo=song.capo)}</button>'
            f'<button type="button" data-mode="sound">{t("no_capo")}</button>'
            f'</div></div>'
        )
    out.append(
        f'<div class="ctl"><span class="lbl">{t("key")}</span>'
        f'<div class="seg seg--key">'
        f'<button type="button" data-step="-1" aria-label="{t("key_down")}">−</button>'
        f'<output class="key-name">{escape(song.key.name())}</output>'
        f'<button type="button" data-step="1" aria-label="{t("key_up")}">+</button>'
        f'</div><output class="key-shift shift"></output>'
        f'<button type="button" class="reset key-reset" hidden>{t("reset")}</button></div>'
    )
    return "".join(out)


def lyrics_block(variant: Variant, ui: str, hidden: bool, note: str = "") -> tuple[str, list[str]]:
    """Sheet + chord panel + precomputed chord data for one lyrics file."""
    t = i18n.Translator(ui)
    labels = {key: texts[ui] for key, texts in i18n.strings().items()}
    song = variant.song
    names, keys, diagrams, warnings = chord_tables(song)
    cards = []
    for i, w in enumerate(song.chords_in_order()):
        svg = diagrams.get(w, '<span class="dg-none">?</span>')
        cards.append(
            f'<button type="button" class="dg-card" data-card="{i}">'
            f'<span class="dg-name">{escape(w)}</span><span class="dg-img">{svg}</span></button>'
        )
    data = {"capo": song.capo, "names": names, "keys": keys, "diagrams": diagrams}
    data_json = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = (
        f'<div class="lyrics-block" data-lyrics="{variant.lang}"'
        f' data-original="{1 if variant.is_original else 0}"{" hidden" if hidden else ""}>\n{note}'
        f'<div class="layout">\n<article class="sheet">\n{sheet_html(song, labels)}\n</article>\n'
        f'<aside class="chords"><h2>{t("chords")}</h2><div class="dg-grid">{"".join(cards)}</div></aside>\n'
        f'</div>\n<script type="application/json" class="lyrics-data">{data_json}</script>\n</div>'
    )
    return html, warnings


def translation_note(entry: SongEntry, variant: Variant, ui: str) -> str:
    """Note above a lyrics translation (automatic or by the author); none for the original lyrics."""
    if variant.is_original:
        return ""
    t = i18n.Translator(ui)
    key = "author_translation_note" if variant.by_author else "auto_translation_note"
    return f'<div class="auto-note">{t(key, langs="/".join(entry.song_languages))}</div>\n'


# ── Print page (source of the PDF) ────────────────────────────────────────────

def links_html(entry: SongEntry, ui: str) -> str:
    """Printed links: the SoundCloud track and the song page in a UI language (full URLs, readable on paper)."""
    t = i18n.Translator(ui)
    parts = []
    sc = entry.data.get("soundcloud")
    if sc:
        parts.append(f'SoundCloud: <a href="{escape(sc)}">{escape(sc.split("://", 1)[-1])}</a>')
    url = page_url(song_path(entry, ui))
    parts.append(f'{t("song_link")}: <a href="{escape(url)}">{escape(url.split("://", 1)[-1])}</a>')
    return f'<div class="print-links">{"<br>".join(parts)}</div>'


def _print_sheet(entry: SongEntry, variant: Variant, album: Album | None, ui: str, title: str,
                 subtitle: str = "", note: str = "") -> tuple[str, list[str]]:
    """Header (cover, album, title, credits, links, capo/key) + sheet of one lyrics file."""
    t = i18n.Translator(ui)
    song = variant.song
    up = "../../"
    block, warnings = lyrics_block(variant, ui, hidden=False, note=note)
    album_line = f'<div class="album">{escape(album.year)} · {escape(album.title(ui))}</div>' if album else ""
    cover = entry.cover_src(up)
    cover_html = f'<img class="cover" src="{escape(cover)}" alt="">' if cover else ""
    sub = f'<div class="subtitle">{escape(subtitle)}</div>' if subtitle else ""
    capo = f'{t("capo")}: <b>{t("capo_fret", capo=song.capo)}</b> · ' if song.capo else ""
    key = f'{t("key")}: {escape(song.key.name())}' if song.get("key") else ""
    html = (
        f'<header class="head">{cover_html}<div class="head-text">{album_line}'
        f'<h1>{escape(title)}</h1>{sub}<div class="credits">{credits_html(entry, ui)}</div>'
        f'{links_html(entry, ui)}</div></header>\n'
        f'<div class="print-meta">{capo}{key}</div>\n{block}'
    )
    return html, warnings


def _sheets_document(title: str, ui: str, body_class: str, songs: list[str], front: str = "") -> str:
    """A4 landscape sheets of two A5 halves (assets/songbook.js lays the songs out).

    `songs`: `<section class="sb-song">` blocks, measured and placed by the script;
    `front`: fixed sheets before them (the songbook's title and contents).
    """
    return (
        html_head(title, "../../", ["song.css", "songbook.css"], ui)
        + f'''<body class="{body_class} print-page songbook" data-layout="pending">
<div class="sb-sheets">{front}</div>
<div class="sb-source">
{"".join(songs)}
</div>
<script src="{asset("../../", "songbook.js")}"></script>
</body>
</html>
'''
    )


def _song_section(anchor: str, sheet: str) -> str:
    return f'<section class="sb-song" id="{anchor}">\n{sheet}\n</section>'


def chords_print_page(entry: SongEntry, album: Album | None) -> tuple[str, list[str]]:
    """Original lyrics with chords and fingerings: the song's sheet exactly as in the songbook."""
    ui = original_ui(entry)
    title = entry.title(ui)
    sheet, warnings = _print_sheet(entry, entry.original, album, ui, title)
    return _sheets_document(title, ui, "mode-chords single", [_song_section(f"song-{entry.folder}", sheet)]), warnings


def lyrics_print_page(entry: SongEntry, album: Album | None, ui: str) -> str:
    """Lyrics only in a UI language: the automatic translation, or the original when it is sung in it."""
    t = i18n.Translator(ui)
    variant = entry.lyrics_for(ui)
    title = entry.title(ui)
    note = translation_note(entry, variant, ui)
    sheet, _ = _print_sheet(entry, variant, album, ui, title, note=note)
    return _sheets_document(title, ui, "mode-lyrics single", [_song_section(f"song-{entry.folder}", sheet)])


def songbook_page(ui: str, entries: list[SongEntry], albums: dict[str, Album]) -> str:
    """All songs in one printable book: A4 landscape, two A5 pages per sheet.

    Sheet 1: title (left) and contents (right). Then every song's original lyrics with
    chords; assets/songbook.js measures each song and lays it out on one half or both
    halves of one sheet (never across sheets), numbers the pages and fills the contents.
    """
    t = i18n.Translator(ui)
    settings = load_settings()
    author = settings["author"][ui]
    ordered = sorted(entries, key=lambda e: e.date, reverse=True)
    years = sorted({e.date[:4] for e in ordered})
    span = years[0] if len(years) == 1 else f"{years[0]}–{years[-1]}"

    toc, songs = [], []
    for e in ordered:
        title = e.title(ui)
        original = e.original.song.get("title")
        subtitle = original if original != title else ""
        album = albums.get(e.album_id) if e.album_id else None
        anchor = f"song-{e.folder}"
        extra = f' <span class="toc-sub">{escape(subtitle)}</span>' if subtitle else ""
        toc.append(
            f'<li data-song="{anchor}"><a href="#{anchor}">{escape(title)}</a>{extra}'
            f'<span class="toc-page"></span></li>'
        )
        sheet, _ = _print_sheet(e, e.original, album, ui, title, subtitle)
        songs.append(_song_section(anchor, sheet))

    front = f'''
  <section class="sb-sheet">
    <div class="half sb-title">
      <img class="sb-photo" src="../../{settings["author-photo"]}" alt="">
      <div class="sb-author">{escape(author)}</div>
      <h1>{t("songbook")}</h1>
      <div class="sb-meta">{escape(span)} · {t("songbook_hint")}</div>
    </div>
    <div class="half">
      <h2 class="sb-toc-title">{t("contents")}</h2>
      <ol class="sb-toc">{"".join(toc)}</ol>
    </div>
  </section>
'''
    return _sheets_document(f"{author} — {t.raw('songbook')}", ui, "mode-chords", songs, front)
