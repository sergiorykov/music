"""Song rendering: chord tables, chord-over-lyrics sheet, lyrics blocks and the print page."""

from __future__ import annotations

import json
import re
from html import escape
from urllib.parse import quote

from . import chordpro, diagram, i18n
from .catalog import Album, SongEntry, Variant, load_settings, ui_languages
from .chords import Chord
from .voicings import lookup

MODES = ("shape", "sound")   # shape: as written, played with capo; sound: concert pitch, no capo
SEMITONES = range(12)

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


def _section_html(sec: chordpro.Section, index: dict[str, int], labels: dict) -> str:
    items = list(sec.items)
    while items and isinstance(items[-1], chordpro.Blank):
        items.pop()
    body = []
    for item in items:
        if isinstance(item, chordpro.Line):
            body.append(_line_html(item, index))
        elif isinstance(item, chordpro.Comment):
            cls = "cmt cmt--i" if item.italic else "cmt"
            body.append(f'<div class="{cls}">{escape(item.text)}</div>')
        elif isinstance(item, chordpro.Blank):
            body.append('<div class="gap"></div>')
    label = sec.label or (labels.get(sec.kind) if sec.kind in ("chorus", "bridge") else None)
    head = f'<div class="sec-label">{escape(label)}</div>' if label else ""
    return f'<section class="sec sec--{sec.kind}">{head}{"".join(body)}</section>'


def sheet_html(song: chordpro.Song, labels: dict) -> str:
    index = {name: i for i, name in enumerate(song.chords_in_order())}
    out = []
    for block in song.body:
        if isinstance(block, chordpro.Section):
            out.append(_section_html(block, index, labels))
        elif isinstance(block, chordpro.ChorusRef):
            label = block.label or labels["chorus"]
            out.append(f'<section class="sec sec--ref"><div class="sec-label">{escape(label)}</div></section>')
        elif isinstance(block, chordpro.PageBreak):
            out.append('<div class="page-break"></div>')
    return "\n".join(out)


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


# ── Shared page parts ─────────────────────────────────────────────────────────

def html_head(title: str, up: str, css: list[str], lang: str) -> str:
    links = "".join(f'<link rel="stylesheet" href="{up}assets/{c}">' for c in css)
    return (
        f'<!DOCTYPE html>\n<html lang="{lang}">\n<head>\n<meta charset="UTF-8">\n'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<title>{escape(title)}</title>\n'
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


def lyrics_block(variant: Variant, ui: str, pdf_href: str, hidden: bool) -> tuple[str, list[str]]:
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
        f'<div class="lyrics-block" data-lyrics="{variant.lang}" data-pdf="{escape(pdf_href)}"'
        f'{" hidden" if hidden else ""}>\n'
        f'<div class="layout">\n<article class="sheet">\n{sheet_html(song, labels)}\n</article>\n'
        f'<aside class="chords"><h2>{t("chords")}</h2><div class="dg-grid">{"".join(cards)}</div></aside>\n'
        f'</div>\n<script type="application/json" class="lyrics-data">{data_json}</script>\n</div>'
    )
    return html, warnings


# ── Print page (source of the PDF) ────────────────────────────────────────────

def print_ui_language(entry: SongEntry, variant: Variant) -> str:
    """Labels of a printed sheet follow its lyrics when that is a UI language."""
    langs = ui_languages()
    if variant.lang in langs:
        return variant.lang
    return entry.original.lang if entry.original.lang in langs else langs[0]


def _print_sheet(entry: SongEntry, variant: Variant, album: Album | None, ui: str, title: str,
                 subtitle: str = "") -> tuple[str, list[str]]:
    """Header (cover, album, title, credits, capo/key) + chords-on sheet of one lyrics file."""
    t = i18n.Translator(ui)
    song = variant.song
    up = "../../"
    block, warnings = lyrics_block(variant, ui, "", hidden=False)
    album_line = f'<div class="album">{escape(album.year)} · {escape(album.title(ui))}</div>' if album else ""
    cover = entry.cover_src(up)
    cover_html = f'<img class="cover" src="{escape(cover)}" alt="">' if cover else ""
    sub = f'<div class="subtitle">{escape(subtitle)}</div>' if subtitle else ""
    capo = f'{t("capo")}: {t("capo_fret", capo=song.capo)} · ' if song.capo else ""
    html = (
        f'<header class="head">{cover_html}<div class="head-text">{album_line}'
        f'<h1>{escape(title)}</h1>{sub}<div class="credits">{credits_html(entry, ui)}</div></div></header>\n'
        f'<div class="print-meta">{capo}{t("key")}: {escape(song.key.name())}</div>\n{block}'
    )
    return html, warnings


def print_page(entry: SongEntry, variant: Variant, album: Album | None) -> tuple[str, list[str]]:
    """Chords-on sheet for one lyrics file, laid out for A5 print."""
    ui = print_ui_language(entry, variant)
    title = variant.song.get("title")
    sheet, warnings = _print_sheet(entry, variant, album, ui, title)
    html = (
        html_head(title, "../../", ["song.css"], ui)
        + f'<body class="mode-chords print-page">\n<div class="page">\n{sheet}\n</div>\n</body>\n</html>\n'
    )
    return html, warnings


def songbook_page(ui: str, entries: list[SongEntry], albums: dict[str, Album]) -> str:
    """All songs in one printable book: title page, contents, then each song's sung lyrics with chords."""
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
            f'<li><a href="#{anchor}">{escape(title)}</a>{extra}'
            f'<span class="toc-year">{escape(e.date[:4])}</span></li>'
        )
        sheet, _ = _print_sheet(e, e.original, album, ui, title, subtitle)
        songs.append(f'<section class="sb-song" id="{anchor}">\n{sheet}\n</section>')

    return (
        html_head(f"{author} — {t.raw('songbook')}", "../../", ["song.css"], ui)
        + f'''<body class="mode-chords print-page songbook">
<div class="page">
<section class="sb-title">
  <img class="sb-photo" src="../../{settings["author-photo"]}" alt="">
  <div class="sb-author">{escape(author)}</div>
  <h1>{t("songbook")}</h1>
  <div class="sb-meta">{escape(span)} · {t("songbook_hint")}</div>
  <h2 class="sb-toc-title">{t("contents")}</h2>
  <ol class="sb-toc">{"".join(toc)}</ol>
</section>
{"".join(songs)}
</div>
</body>
</html>
'''
    )
