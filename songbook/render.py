"""Render one song variant as a standalone HTML page (web view + print layout)."""

from __future__ import annotations

import json
import re
from html import escape
from urllib.parse import quote

from . import chordpro, diagram, i18n
from .catalog import Album, SongEntry, Variant
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
    parsed = [Chord.parse(w) for w in written]
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


# ── Page ──────────────────────────────────────────────────────────────────────

def _link(text: str, url: str | None) -> str:
    t = escape(text)
    return f'<a href="{escape(url)}" target="_blank" rel="noopener">{t}</a>' if url else t


def _credits_html(entry: SongEntry, song: chordpro.Song, labels: dict) -> str:
    lines = []
    lyricist = song.get("lyricist")
    if lyricist:
        parts = [_link(lyricist, song.get("lyricist_url"))]
        if song.get("lyrics_date"):
            parts.append(escape(song.get("lyrics_date")))
        for src in song.get_all("lyrics_source"):
            label, _, url = src.partition("|")
            parts.append(_link(label.strip(), url.strip() or None))
        lines.append(f'<div>{labels["lyrics"]}: {" · ".join(parts)}</div>')
    composer = song.get("composer")
    if composer:
        parts = [_link(composer, entry.data.get("music-author-url"))]
        parts.append(escape(entry.display_date))
        lines.append(f'<div>{labels["music"]}: {" · ".join(parts)}</div>')
    return "".join(lines)


def _lang_nav(entry: SongEntry, current: str) -> str:
    if len(entry.variants) < 2:
        return ""
    items = []
    for lang in entry.variants:
        if lang == current:
            items.append(f'<span class="on">{lang}</span>')
        else:
            items.append(f'<a href="{lang}.html">{lang}</a>')
    return f'<span class="langs">{" · ".join(items)}</span>'


def render_page(entry: SongEntry, variant: Variant, album: Album | None, settings: dict) -> tuple[str, list[str]]:
    song = variant.song
    lang = variant.lang
    labels = {key: texts[lang] for key, texts in i18n.strings().items()}
    names, keys, diagrams, warnings = chord_tables(song)
    written = song.chords_in_order()
    capo = song.capo
    up = "../../"
    folder_q = quote(entry.folder)

    title = song.get("title")
    author = album.author(lang) if album else song.get("composer", "")
    album_link = (
        f'<a class="album" href="{up}index.html?album={quote(album.id)}">'
        f'<span class="back">← </span>{escape(album.year)} · {escape(album.title(lang))}</a>'
        if album else ""
    )
    cover = entry.data.get("cover-image")
    cover_html = f'<img class="cover" src="{up}songs/{folder_q}/{escape(cover)}" alt="">' if cover else ""

    embed = entry.data.get("soundcloud-embed")
    player = (
        f'<div class="player"><iframe src="{escape(embed)}" width="100%" height="120" scrolling="no"'
        f' frameborder="no" allow="autoplay" loading="lazy" title="SoundCloud"></iframe></div>'
        if embed else ""
    )

    if capo:
        capo_ctl = (
            f'<div class="ctl"><span class="lbl">{labels["capo"]}</span>'
            f'<div class="seg" role="group">'
            f'<button type="button" data-mode="shape" class="on">{labels["capo_fret"].format(capo=capo)}</button>'
            f'<button type="button" data-mode="sound">{labels["no_capo"]}</button>'
            f'</div></div>'
        )
        print_capo = labels["capo_fret"].format(capo=capo)
        print_meta = f'{labels["capo"]}: {print_capo} · {labels["key"]}: {keys["shape"][0]}'
    else:
        capo_ctl = ""
        print_meta = f'{labels["key"]}: {keys["shape"][0]}'

    key_ctl = (
        f'<div class="ctl"><span class="lbl">{labels["key"]}</span>'
        f'<div class="seg seg--key">'
        f'<button type="button" data-step="-1" aria-label="{labels["key_down"]}">−</button>'
        f'<output id="key-name">{keys["shape"][0]}</output>'
        f'<button type="button" data-step="1" aria-label="{labels["key_up"]}">+</button>'
        f'</div><output id="key-shift" class="shift"></output>'
        f'<button type="button" class="reset" id="key-reset" hidden>{labels["reset"]}</button></div>'
    )
    pdf_href = f"{up}pdf/{folder_q}/{lang}.pdf"

    cards = []
    for i, w in enumerate(written):
        svg = diagrams.get(w, '<span class="dg-none">?</span>')
        cards.append(
            f'<button type="button" class="dg-card" data-card="{i}">'
            f'<span class="dg-name">{escape(w)}</span><span class="dg-img">{svg}</span></button>'
        )

    data = {"capo": capo, "names": names, "keys": keys, "diagrams": diagrams}
    data_json = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    html = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} — {escape(author)}</title>
<link rel="icon" type="image/png" href="{up}favicon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS_URL}">
<link rel="stylesheet" href="{up}assets/song.css">
</head>
<body>
<div class="page">
  <nav class="top"><a href="{up}index.html">← {labels["all_songs"]}</a>{_lang_nav(entry, lang)}</nav>
  <header class="head">
    {cover_html}
    <div class="head-text">
      {album_link}
      <h1>{escape(title)}</h1>
      <div class="credits">{_credits_html(entry, song, labels)}</div>
    </div>
  </header>
  {player}
  <div class="toolbar">
    {capo_ctl}
    {key_ctl}
    <a class="pdf" href="{pdf_href}" target="_blank" rel="noopener">PDF</a>
  </div>
  <div class="print-meta">{print_meta}</div>
  <main class="layout">
    <article class="sheet">
{sheet_html(song, labels)}
    </article>
    <aside class="chords">
      <h2>{labels["chords"]}</h2>
      <div class="dg-grid">{"".join(cards)}</div>
    </aside>
  </main>
</div>
<div id="pop" class="pop" hidden></div>
<script id="song-data" type="application/json">{data_json}</script>
<script src="{up}assets/song.js"></script>
</body>
</html>
"""
    return html, warnings
