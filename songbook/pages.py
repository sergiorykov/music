"""Site pages per UI language: home, album pages and song pages, plus the root redirect.

URL scheme (see docs/adr/0001-url-scheme.md):
  /<ui>/                                 home
  /<ui>/albums/<album-slug>/             album page
  /<ui>/songs/<year>-<month>-<song-slug>/  song page
  /pdf/<year>-<month>-<en slug>-<lyrics>.pdf  printable sheet (built from /print/)
Slugs and titles come from the metadata language equal to the UI language.
"""

from __future__ import annotations

import json
import re
from html import escape

from . import i18n, icons
from .catalog import Album, SongEntry, load_settings, ui_languages
from .render import chord_controls, credits_html, html_head, lyrics_block, plain_lyrics


# ── Paths ─────────────────────────────────────────────────────────────────────

def song_path(entry: SongEntry, ui: str) -> str:
    return f"{ui}/songs/{entry.url_slug(ui)}/"


def album_path(album: Album, ui: str) -> str:
    return f"{ui}/albums/{album.slug(ui)}/"


def pdf_path(entry: SongEntry, lyrics: str) -> str:
    """Self-describing file name, also when saved: pdf/<year>-<month>-<en slug>-<lyrics>.pdf."""
    return f"pdf/{entry.folder}-{lyrics}.pdf"


def print_path(entry: SongEntry, lyrics: str) -> str:
    return f"print/{entry.folder}/{lyrics}.html"


# ── Shared parts ──────────────────────────────────────────────────────────────

def ui_switch(current: str, targets: dict[str, str]) -> str:
    """Links to the same page in every UI language; the choice is remembered by the root redirect."""
    t = i18n.Translator(current)
    items = []
    for lang in ui_languages():
        if lang == current:
            items.append(f'<span class="on" aria-current="true">{lang}</span>')
        else:
            items.append(f'<a href="{escape(targets[lang])}" data-ui-lang="{lang}" hreflang="{lang}">{lang}</a>')
    return f'<nav class="uilangs" aria-label="{t("ui_language")}">{" · ".join(items)}</nav>'


def footer(ui: str) -> str:
    t = i18n.Translator(ui)
    stack = [
        ("https://claude.ai/code", icons.CLAUDE_CODE + " Claude Code"),
        ("https://www.chordpro.org", "ChordPro"),
        ("https://www.python.org", "Python"),
        ("https://playwright.dev", "Playwright"),
        ("https://github.com/tombatossals/chords-db", "chords-db"),
    ]
    tools = '<span class="footer-sep">·</span>'.join(
        f'<a href="{url}" target="_blank" rel="noopener" class="footer-tool">{label}</a>' for url, label in stack
    )
    return (
        '<footer>\n'
        '  <div><a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener">CC BY 4.0</a></div>\n'
        f'  <div class="footer-made">{t("made_with")} {tools}</div>\n'
        '</footer>'
    )


def song_item(entry: SongEntry, ui: str, root: str) -> str:
    """One row of a song list (home and album pages)."""
    t = i18n.Translator(ui)
    title = escape(entry.title(ui))
    original = ""
    if ui not in entry.song_languages:
        original_title = entry.title(entry.original.lang) if entry.original.lang in ui_languages() \
            else entry.original.song.get("title")
        if original_title != entry.title(ui):
            original = f' <span class="song-original">{t("original_title", title=original_title)}</span>'

    actions = (
        f'<a class="icon-btn lang-btn" href="{root}{song_path(entry, ui)}"'
        f' data-tooltip="{t("song_page")}">{t("chords")}</a>'
        f'<a class="icon-btn lang-btn" href="{root}{pdf_path(entry, entry.original.lang)}" target="_blank"'
        f' rel="noopener" data-tooltip="{t("pdf_hint")}">pdf</a>'
    )
    sc = entry.data.get("soundcloud")
    if sc:
        actions += (
            f'<a class="icon-btn play-btn" href="{escape(sc)}" target="_blank" rel="noopener"'
            f' data-tooltip="{t("listen")}">{icons.play_button(re.sub(r"[^a-z0-9]", "_", entry.id))}</a>'
        )
    embed = entry.data.get("soundcloud-embed")
    player = (
        f'<iframe class="sc-embed" src="{escape(embed)}" width="100%" height="166" scrolling="no"'
        f' frameborder="no" loading="lazy" title="SoundCloud"></iframe>'
        if embed else ""
    )
    lyrics = escape(plain_lyrics(entry.lyrics_for(ui).song))
    return (
        f'      <li data-sung="{" ".join(entry.song_languages)}" data-album-id="{entry.album_id or ""}">\n'
        f'        <details class="song-details">\n'
        f'          <summary class="song-row">\n'
        f'            <span class="song-title">{title}{original}</span>\n'
        f'            <div class="song-actions">{actions}</div>\n'
        f'          </summary>\n'
        f'        <div class="lyrics">{player}<div class="lyrics-credits">{credits_html(entry, ui)}</div>'
        f'<pre>{lyrics}</pre></div>\n'
        f'        </details>\n'
        f'      </li>'
    )


def _sorted(entries: list[SongEntry]) -> list[SongEntry]:
    return sorted(entries, key=lambda e: e.date, reverse=True)


# ── Home ──────────────────────────────────────────────────────────────────────

def home_page(ui: str, entries: list[SongEntry], albums: list[Album]) -> str:
    t = i18n.Translator(ui)
    settings = load_settings()
    root = "../"
    author = settings["author"][ui]
    links = settings["links"]

    album_chips = "".join(
        f'<button class="lang-filter-btn" data-album="{a.id}">{escape(a.title(ui))} · {escape(a.year)}</button>'
        for a in albums
    )
    album_cards = "".join(
        f'<a class="album-card" href="{root}{album_path(a, ui)}">'
        f'<img src="{root}albums/{escape(a.folder)}/{escape(a.data.get("cover-image", "cover.png"))}"'
        f' class="album-card-cover" alt="{escape(a.title(ui))}">'
        f'<div class="album-card-name">{escape(a.title(ui))}</div>'
        f'<div class="album-card-year">{escape(a.year)}</div></a>'
        for a in albums
    )
    sung = sorted({lang for e in entries for lang in e.song_languages})
    sung_chips = "".join(f'<button class="lang-filter-btn" data-sung="{lang}">{lang}</button>' for lang in sung)
    items = "\n".join(song_item(e, ui, root) for e in _sorted(entries))

    return (
        html_head(f"{author} — {i18n.Translator(ui).raw('songs')}", root, ["home.css"], ui)
        + f'''<body>
  <div class="container">
    <header>
      <div class="author">
        <div class="author-left">
          <img src="{root}{settings["author-photo"]}" alt="{escape(author)}" />
          <span class="author-name">{escape(author)}</span>
        </div>
        <nav class="social">
          <a href="{links["github"]}" target="_blank" rel="noopener" aria-label="GitHub">{icons.GITHUB}</a>
          <a href="{links["soundcloud"]}" target="_blank" rel="noopener" aria-label="SoundCloud"><img src="{root}images/soundcloud_logo.png" width="22" height="22" alt="SoundCloud" class="sc-logo" /></a>
          <a href="{links["instagram"]}" target="_blank" rel="noopener" aria-label="Instagram">{icons.INSTAGRAM}</a>
        </nav>
      </div>
      <div class="tagline-row"><p>{t("tagline")}</p>{ui_switch(ui, {l: f"{root}{l}/" for l in ui_languages()})}</div>
    </header>

    <div class="songs-heading-row">
      <h1>{t("songs")}</h1>
      <div class="lang-filter" id="sung-filter" title="{t("sung_in_hint")}">
        <span class="filter-label">{t("sung_in")}:</span>
        <button class="lang-filter-btn active" data-sung="all">{t("all")}</button>{sung_chips}
      </div>
    </div>

    <div class="albums-heading-row">
      <h2>{t("albums")}</h2>
      <div class="album-filter" id="album-filter">
        <button class="lang-filter-btn active" data-album="all">{t("all")}</button>{album_chips}
      </div>
    </div>
    <div class="album-strip">{album_cards}</div>

    <ul class="songs" id="song-list">
{items}
    </ul>
    {footer(ui)}
  </div>
  <script src="{root}assets/home.js"></script>
</body>
</html>
'''
    )


# ── Album page ────────────────────────────────────────────────────────────────

def album_page(ui: str, album: Album, entries: list[SongEntry]) -> str:
    t = i18n.Translator(ui)
    root = "../../../"
    songs = [e for e in entries if e.album_id == album.id]
    items = "\n".join(song_item(e, ui, root) for e in _sorted(songs))
    targets = {lang: f"{root}{album_path(album, lang)}" for lang in ui_languages()}
    cover = album.data.get("cover-image", "cover.png")
    return (
        html_head(f"{album.title(ui)} — {album.author(ui)}", root, ["home.css"], ui)
        + f'''<body>
  <div class="container">
    <nav class="top-nav"><a href="{root}{ui}/">← {t("all_songs")}</a>{ui_switch(ui, targets)}</nav>
    <header class="album-head">
      <img class="album-cover" src="{root}albums/{escape(album.folder)}/{escape(cover)}" alt="">
      <div>
        <div class="album-year">{escape(album.year)}</div>
        <h1 class="album-title">{escape(album.title(ui))}</h1>
        <div class="album-author">{escape(album.author(ui))}</div>
      </div>
    </header>
    <ul class="songs" id="song-list">
{items}
    </ul>
    {footer(ui)}
  </div>
  <script src="{root}assets/home.js"></script>
</body>
</html>
'''
    )


# ── Song page ─────────────────────────────────────────────────────────────────

def song_page(ui: str, entry: SongEntry, album: Album | None) -> tuple[str, list[str]]:
    t = i18n.Translator(ui)
    root = "../../../"
    title = entry.title(ui)
    author = album.author(ui) if album else entry.meta(ui).get("composer", "")
    default = entry.lyrics_for(ui)
    targets = {lang: f"{root}{song_path(entry, lang)}" for lang in ui_languages()}

    album_link = (
        f'<a class="album" href="{root}{album_path(album, ui)}"><span class="back">← </span>'
        f'{escape(album.year)} · {escape(album.title(ui))}</a>'
        if album else ""
    )
    cover = entry.data.get("cover-image")
    cover_html = f'<img class="cover" src="{root}songs/{escape(entry.folder)}/{escape(cover)}" alt="">' if cover else ""
    embed = entry.data.get("soundcloud-embed")
    player = (
        f'<div class="player"><iframe src="{escape(embed)}" width="100%" height="120" scrolling="no"'
        f' frameborder="no" allow="autoplay" loading="lazy" title="SoundCloud"></iframe></div>'
        if embed else ""
    )

    lyrics_switch = ""
    if len(entry.variants) > 1:
        buttons = "".join(
            f'<button type="button" data-lyrics="{v.lang}"{" class=on" if v is default else ""}>'
            f'{v.lang} <small>{t("original") if v.is_original else t("translation")}</small></button>'
            for v in entry.variants.values()
        )
        lyrics_switch = f'<div class="ctl"><span class="lbl">{t("text")}</span><div class="seg" role="group">{buttons}</div></div>'

    blocks, warnings = [], []
    for v in entry.variants.values():
        html, w = lyrics_block(v, ui, f"{root}{pdf_path(entry, v.lang)}", hidden=v is not default)
        blocks.append(html)
        warnings += w

    html = (
        html_head(f"{title} — {author}", root, ["song.css"], ui)
        + f'''<body class="mode-lyrics">
<div class="page">
  <nav class="top"><a href="{root}{ui}/">← {t("all_songs")}</a>{ui_switch(ui, targets)}</nav>
  <header class="head">
    {cover_html}
    <div class="head-text">
      {album_link}
      <h1>{escape(title)}</h1>
      <div class="credits">{credits_html(entry, ui)}</div>
    </div>
  </header>
  {player}
  <div class="toolbar">
    {lyrics_switch}
    <button type="button" class="toggle" id="chords-toggle" aria-pressed="false">{t("with_chords")}</button>
    <a class="pdf" href="{root}{pdf_path(entry, default.lang)}" target="_blank" rel="noopener" title="{t("pdf_hint")}">PDF</a>
  </div>
  <div class="toolbar toolbar--chords">{chord_controls(default.song, ui)}</div>
  <main>
{"".join(blocks)}
  </main>
</div>
<div id="pop" class="pop" hidden></div>
<script src="{root}assets/song.js"></script>
</body>
</html>
'''
    )
    return html, warnings


# ── Root redirect ─────────────────────────────────────────────────────────────

def root_redirect() -> str:
    """index.html at the site root: send the visitor to their UI language."""
    settings = load_settings()
    langs = ui_languages()
    default = settings["default-ui-language"]
    t = i18n.Translator(default)
    links = " · ".join(f'<a href="{lang}/" hreflang="{lang}">{lang}</a>' for lang in langs)
    return f'''<!DOCTYPE html>
<html lang="{default}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(settings["author"][default])} — {t("songs")}</title>
<link rel="icon" type="image/png" href="favicon.png">
<noscript><meta http-equiv="refresh" content="0; url={default}/"></noscript>
<script>
  // Generated by build.py. Picks the UI language: saved choice, then browser languages, then default.
  (function () {{
    var langs = {json.dumps(langs)}, pick = "{default}";
    try {{
      var saved = localStorage.getItem("songbook.ui");
      if (langs.indexOf(saved) >= 0) {{ location.replace(saved + "/" + location.search); return; }}
    }} catch (e) {{}}
    var prefs = navigator.languages || [navigator.language || ""];
    for (var i = 0; i < prefs.length; i++) {{
      var code = String(prefs[i]).slice(0, 2).toLowerCase();
      if (langs.indexOf(code) >= 0) {{ pick = code; break; }}
    }}
    location.replace(pick + "/" + location.search);
  }})();
</script>
<style>body{{background:#0d0d0d;color:#e8e8e8;font:16px Georgia,serif;display:grid;place-items:center;min-height:100vh;margin:0}}a{{color:#c8a96e}}</style>
</head>
<body><p>{t("choose_language")}: {links}</p></body>
</html>
'''
