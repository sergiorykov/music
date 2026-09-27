"""Site pages per UI language: home, album pages and song pages, plus the root redirect.

URL scheme: songbook/paths.py and docs/adr/0001-url-scheme.md.
Slugs and titles come from the metadata language equal to the UI language.
"""

from __future__ import annotations

import json
from html import escape

from . import i18n, icons, seo
from .catalog import Album, SongEntry, load_settings, ui_languages
from .paths import (album_path, chords_pdf_path, lyrics_pdf_path, original_ui, song_path,
                    songbook_pdf_path, songbook_web_path, about_path)
from .render import asset, chord_controls, credits_html, html_head, web_song_sheet, lyrics_block, sheet_html, translation_note


# ── Shared parts ──────────────────────────────────────────────────────────────

def ui_switch(current: str, targets: dict[str, str]) -> str:
    """Links to the same page in every UI language (the choice is remembered by the root redirect)
    and the light / dark theme switch."""
    t = i18n.Translator(current)
    items = []
    for lang in ui_languages():
        if lang == current:
            items.append(f'<span class="on" aria-current="true">{lang}</span>')
        else:
            items.append(f'<a href="{escape(targets[lang])}" data-ui-lang="{lang}" hreflang="{lang}">{lang}</a>')
    toggle = (f'<button type="button" class="theme-toggle" data-theme-toggle title="{t("theme_toggle")}"'
              f' aria-label="{t("theme_toggle")}"><span class="to-light">☀</span><span class="to-dark">☾</span></button>')
    return f'<nav class="uilangs" aria-label="{t("ui_language")}">{" · ".join(items)}{toggle}</nav>'


def footer(ui: str) -> str:
    t = i18n.Translator(ui)
    stack = [
        ("https://claude.ai/code", icons.CLAUDE_CODE + " Claude Code"),
        ("https://www.chordpro.org", "ChordPro"),
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
    if ui not in entry.song_languages:              # sung in another language: say which, as tags
        tags = "".join(f'<span class="lang-tag">{lang.upper()}</span>' for lang in entry.song_languages)
        original = f' <span class="song-original">{t("original")} {tags}</span>'

    page = f"{root}{song_path(entry, ui)}"
    actions = (
        f'<a class="icon-btn lang-btn" href="{page}#lyrics" target="_blank" rel="noopener"'
        f' data-tooltip="{t("lyrics_hint")}">{t("lyrics_btn")}</a>'
        f'<a class="icon-btn lang-btn" href="{page}#chords" target="_blank" rel="noopener"'
        f' data-tooltip="{t("chords_hint")}">{t("chords")}</a>'
    )
    sc = entry.data.get("soundcloud")
    if sc:
        actions += (
            f'<a class="icon-btn play-btn" href="{escape(sc)}" target="_blank" rel="noopener"'
            f' data-tooltip="{t("listen")}">{icons.play_button()}</a>'
        )
    embed = entry.data.get("soundcloud-embed")
    player = (
        f'<iframe class="sc-embed" src="{escape(embed)}" width="100%" height="166" scrolling="no"'
        f' frameborder="no" loading="lazy" title="SoundCloud"></iframe>'
        if embed else ""
    )
    shown = entry.lyrics_for(ui)
    labels = {key: texts[ui] for key, texts in i18n.strings().items()}
    note = translation_note(entry, shown, ui)
    lyrics = f'{note}<div class="sheet">{sheet_html(shown.song, labels, chords=False)}</div>'
    return (
        f'      <li data-sung="{" ".join(entry.song_languages)}" data-album-id="{entry.album_id or ""}">\n'
        f'        <details class="song-details">\n'
        f'          <summary class="song-row">\n'
        f'            <span class="song-title">{title}{original}</span>\n'
        f'            <div class="song-actions">{actions}</div>\n'
        f'          </summary>\n'
        f'        <div class="lyrics">{player}<div class="lyrics-credits">{credits_html(entry, ui)}</div>'
        f'{lyrics}</div>\n'
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

    album_rows = "".join(
        f'<div class="album-row"><button class="album-item" data-album="{a.id}">'
        f'<img src="{root}albums/{escape(a.folder)}/{escape(a.data.get("cover-image", "cover.png"))}" alt="">'
        f'<span>{escape(a.title(ui))}<small>{escape(a.year)}</small></span></button>'
        f'<a class="album-go" href="{root}{album_path(a, ui)}" title="{escape(a.title(ui))}"'
        f' aria-label="{escape(a.title(ui))}">→</a></div>'
        for a in albums
    )
    sung = sorted({lang for e in entries for lang in e.song_languages})
    sung_chips = "".join(f'<button class="lang-filter-btn" data-sung="{lang}">{lang}</button>' for lang in sung)
    items = "\n".join(song_item(e, ui, root) for e in _sorted(entries))

    return (
        html_head(t.raw("site_title"), root, ["home.css"], ui,
                  seo.og_title(t.raw("site_title"))
                  + seo.head(ui, {l: f"{l}/" for l in ui_languages()}, seo.author_bio(ui),
                             seo.home_ld(ui, _sorted(entries), albums), og_type="profile"))
        + f'''<body class="wide">
  <div class="layout2">
    <aside class="side">
      <a class="side-author" href="{root}{about_path(ui)}" title="{t("about_hint")}">
        <img class="side-photo" src="{root}{settings["author-photo"]}" alt="{escape(author)}">
        <span class="side-name">{escape(author)}</span>
      </a>
      <p class="side-tagline">{t("tagline")}</p>
      <nav class="social">
        <a href="{links["github"]}" target="_blank" rel="noopener" aria-label="GitHub">{icons.GITHUB}</a>
        <a href="{links["soundcloud"]}" target="_blank" rel="noopener" aria-label="SoundCloud"><img src="{root}images/soundcloud_logo.png" width="22" height="22" alt="SoundCloud" class="sc-logo" /></a>
        <a href="{links["instagram"]}" target="_blank" rel="noopener" aria-label="Instagram">{icons.INSTAGRAM}</a>
      </nav>
      <div class="songbook-btns">
        <a class="songbook-btn" href="{root}{songbook_web_path(ui)}" title="{t("songbook_web_hint")}">♪ {t("songbook_web")}</a>
        <a class="songbook-btn" href="{root}{songbook_pdf_path(ui)}" download title="{t("songbook_hint")}">⬇ {t("songbook_btn")}</a>
      </div>
      <div class="side-h" title="{t("sung_in_hint")}">{t("sung_in")}</div>
      <div class="lang-filter" id="sung-filter">
        <button class="lang-filter-btn active" data-sung="all">{t("all")}</button>{sung_chips}
      </div>
      <div class="side-h">{t("albums")}</div>
      <div class="album-list" id="album-filter">
        <button class="album-item album-all active" data-album="all">{t("all_songs")}</button>{album_rows}
      </div>
    </aside>

    <main class="main">
      <div class="main-head"><h1>{t("songs")} <small>· {len(entries)}</small></h1>{ui_switch(ui, {l: f"{root}{l}/" for l in ui_languages()})}</div>
      <ul class="songs" id="song-list">
{items}
      </ul>
      {footer(ui)}
    </main>
  </div>
  <script src="{asset(root, "home.js")}"></script>
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
        html_head(f"{album.title(ui)} — {album.author(ui)}", root, ["home.css"], ui,
                  seo.og_title(f"{album.title(ui)} — {album.author(ui)}")
                  + seo.head(ui, {l: album_path(album, l) for l in ui_languages()},
                             seo.album_description(ui, album, len(songs)),
                             seo.album_ld(ui, album, _sorted(songs)),
                             image=f"albums/{album.folder}/{cover}", og_type="music.album"))
        + f'''<body class="wide">
  <div class="layout2">
    <aside class="side">
      <a class="side-back" href="{root}{ui}/">← {t("all_songs")}</a>
      <img class="album-cover" src="{root}albums/{escape(album.folder)}/{escape(cover)}" alt="">
      <div class="album-year">{escape(album.year)}</div>
      <h1 class="album-title">{escape(album.title(ui))}</h1>
      <div class="album-author">{escape(album.author(ui))}</div>
    </aside>
    <main class="main">
      <div class="main-head"><h2>{t("songs")} <small>· {len(songs)}</small></h2>{ui_switch(ui, targets)}</div>
      <ul class="songs" id="song-list">
{items}
      </ul>
      {footer(ui)}
    </main>
  </div>
  <script src="{asset(root, "home.js")}"></script>
</body>
</html>
'''
    )


# ── Song page ─────────────────────────────────────────────────────────────────

def song_page(ui: str, entry: SongEntry, album: Album | None,
              versions: list[SongEntry] = ()) -> tuple[str, list[str]]:
    """Song page. `versions`: the author's language versions of this song (other songs)."""
    t = i18n.Translator(ui)
    root = "../../../"
    title = entry.title(ui)
    author = album.author(ui) if album else entry.meta(ui).get("composer", "")
    default = entry.lyrics_for(ui)
    targets = {lang: f"{root}{song_path(entry, lang)}" for lang in ui_languages()}
    sung = "/".join(entry.song_languages)

    album_link = (
        f'<a href="{root}{album_path(album, ui)}">{escape(album.year)} · {escape(album.title(ui))}</a>'
        if album else ""
    )
    version_links = "".join(
        f'<div class="version">{t("language_version")} ({"/".join(v.song_languages)}): '
        f'<a href="{root}{song_path(v, ui)}">{escape(v.title(ui))}</a></div>'
        for v in versions
    )
    cover = entry.cover_src(root)
    cover_html = f'<img class="cover" src="{escape(cover)}" alt="">' if cover else ""
    embed = entry.data.get("soundcloud-embed")
    player = (
        f'<div class="player" id="player"><iframe src="{escape(embed)}" width="100%" height="166" scrolling="no"'
        f' frameborder="no" allow="autoplay" title="SoundCloud"></iframe></div>'
        if embed else ""
    )
    player_toggle = (
        f'<button type="button" class="toggle toggle--play on" id="player-toggle" aria-pressed="true"'
        f' aria-controls="player" title="{t("player_hint")}">{icons.SOUNDCLOUD} {t("player")}</button>'
        if embed else ""
    )

    buttons = "".join(
        f'<button type="button" data-lyrics="{v.lang}"{" class=on" if v is default else ""}>'
        f'{sung if v.is_original else v.lang} '
        f'<small>{t("original") if v.is_original else t("author_translation") if v.by_author else t("auto_translation")}</small></button>'
        for v in entry.variants.values()
    )
    lyrics_switch = (
        f'<div class="ctl"><span class="lbl">{t("text")}</span><div class="seg" role="group">{buttons}</div></div>'
        if len(entry.variants) > 1 else ""
    )

    blocks, warnings = [], []
    for v in entry.variants.values():
        html, w = lyrics_block(v, ui, hidden=v is not default, note=translation_note(entry, v, ui))
        blocks.append(html)
        warnings += w

    html = (
        html_head(f"{title} — {author} · {t.raw('song_title_suffix')}", root, ["song.css"], ui,
                  seo.og_title(f"{title} — {author}")
                  + seo.head(ui, {l: song_path(entry, l) for l in ui_languages()},
                             seo.song_description(ui, entry), seo.song_ld(ui, entry, album),
                             image=entry.cover_src(""), og_type="music.song"))
        + f'''<body class="mode-lyrics">
<div class="page">
  <nav class="top"><div class="back-links"><a href="{root}{ui}/">← {t("all_songs")}</a>{album_link}</div>{ui_switch(ui, targets)}</nav>
  <header class="head">
    {cover_html}
    <div class="head-text">
      <h1>{escape(title)}</h1>
      <div class="credits">{credits_html(entry, ui)}{version_links}</div>
    </div>
    <div class="head-pdfs">
      <a class="pdf" href="{root}{chords_pdf_path(entry)}" target="_blank" rel="noopener" title="{t("pdf_hint")}">{t("pdf_chords", langs=sung.upper())}</a>
      <a class="pdf" href="{root}{lyrics_pdf_path(entry, ui)}" target="_blank" rel="noopener" title="{t("pdf_hint")}">{t("pdf_lyrics", lang=ui.upper())}</a>
    </div>
  </header>
  <div class="toolbar">
    {lyrics_switch}
    <button type="button" class="toggle" id="chords-toggle" aria-pressed="false"
      data-label-chords="{t("with_chords")}" data-label-lyrics-only="{t("lyrics_only")}">{t("with_chords")}</button>
    {player_toggle}
  </div>
  <div class="toolbar toolbar--chords">{chord_controls(entry.original.song, ui)}</div>
  {player}
  <main>
{"".join(blocks)}
  </main>
</div>
<div id="pop" class="pop" hidden></div>
<script src="{asset(root, "song.js")}"></script>
</body>
</html>
'''
    )
    return html, warnings


# ── Root redirect ─────────────────────────────────────────────────────────────

# ── About ─────────────────────────────────────────────────────────────────────

def about_page(ui: str) -> str:
    """About the author: photo, bio (settings.json author-bio), SoundCloud."""
    t = i18n.Translator(ui)
    settings = load_settings()
    root = "../../"
    author = settings["author"][ui]
    sc = settings["links"]["soundcloud"]
    title = f"{t.raw('about')} — {author}"
    targets = {lang: f"{root}{about_path(lang)}" for lang in ui_languages()}
    head = seo.og_title(title) + seo.head(ui, {lang: about_path(lang) for lang in ui_languages()},
                                          seo.author_bio(ui), [seo.person(ui)],
                                          image=settings["about-photo"], og_type="profile")
    return (
        html_head(title, root, ["home.css"], ui, head)
        + f'''<body>
  <div class="container">
    <nav class="top-nav"><a href="{root}{ui}/">← {t("all_songs")}</a>{ui_switch(ui, targets)}</nav>
    <article class="about">
      <img class="about-photo" src="{root}{settings["about-photo"]}" alt="{escape(author)}">
      <h1 class="about-name">{escape(author)}</h1>
      <div class="about-place">{escape(settings["author-location"][ui])}</div>
      <p class="about-bio">{escape(seo.author_bio(ui))}</p>
      <a class="songbook-btn about-sc" href="{escape(sc)}" target="_blank" rel="noopener">{icons.SOUNDCLOUD} {t("listen_on_soundcloud")}</a>
    </article>
    {footer(ui)}
  </div>
</body>
</html>
'''
    )


# ── Web songbook ──────────────────────────────────────────────────────────────

def songbook_web_page(ui: str, entries: list[SongEntry], albums: list[Album]) -> tuple[str, list[str]]:
    """Every song with chords, one per screen (for a tablet): album menu on the left,
    the selected song on the right across the full width, like its PDF sheet.
    Layout, navigation and the menu toggle live in assets/songbook-web.js."""
    t = i18n.Translator(ui)
    root = "../../"
    author = load_settings()["author"][ui]
    groups = [(f"{a.year} · {a.title(ui)}", [e for e in entries if e.album_id == a.id]) for a in albums]
    known = {a.id for a in albums}
    groups.append((t.raw("other_songs"), [e for e in entries if e.album_id not in known]))

    nav, songs, warnings = [], [], []
    for label, group in groups:
        if not group:
            continue
        links = "".join(
            f'<li><a href="#{e.id}" data-song="{e.id}"><span class="wsb-date">{e.date[:7]}</span> '
            f'{escape(e.title(ui))}</a></li>'
            for e in _sorted(group)
        )
        nav.append(f'<details class="wsb-album" open><summary>{escape(label)}</summary><ol>{links}</ol></details>')
        for e in _sorted(group):
            sheet, w = web_song_sheet(e, ui, root)
            warnings += w
            songs.append(
                f'<article class="wsb-song" data-song="{e.id}" hidden><div class="wsb-flow">'
                f'<div class="wsb-content">{sheet}</div></div></article>'
            )

    title = f"{t.raw('songbook_web')} — {author}"
    targets = {lang: f"{root}{songbook_web_path(lang)}" for lang in ui_languages()}
    head = seo.og_title(title) + seo.head(
        ui, {lang: songbook_web_path(lang) for lang in ui_languages()}, t.raw("songbook_web_hint"), [])
    html = (
        html_head(title, root, ["song.css", "songbook-web.css"], ui, head)
        + f'''<body class="wsb mode-chords">
<div class="wsb-bar">
  <button type="button" class="wsb-btn" id="wsb-menu" aria-controls="wsb-nav" aria-expanded="true" title="{t("menu")}">☰</button>
  <a class="wsb-home" href="{root}{ui}/">← {t("all_songs")}</a>
  <span class="wsb-title">{t("songbook_web")}</span>
  <button type="button" class="wsb-btn" id="wsb-prev" title="{t("prev_song")}">‹</button>
  <button type="button" class="wsb-btn" id="wsb-next" title="{t("next_song")}">›</button>
  {ui_switch(ui, targets)}
</div>
<div class="wsb-wrap">
  <nav class="wsb-nav" id="wsb-nav">{"".join(nav)}</nav>
  <main class="wsb-main">{"".join(songs)}</main>
</div>
<script src="{asset(root, "songbook-web.js")}"></script>
</body>
</html>
'''
    )
    return html, warnings


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
