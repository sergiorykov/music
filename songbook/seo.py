"""Search and answer-engine metadata: head tags, JSON-LD, sitemap.xml and llms.txt.

Pages only describe themselves here (title, description, their path in every UI language);
the markup search engines and AI agents read is built in one place.
"""

from __future__ import annotations

import json
from html import escape

from . import i18n
from .catalog import Album, SongEntry, load_settings, ui_languages
from .paths import (album_path, chords_pdf_path, lyrics_pdf_path, page_url, site_url, song_path,
                    songbook_pdf_path, songbook_web_path, about_path)

OG_LOCALES = {"ru": "ru_RU", "en": "en_US", "pt": "pt_PT"}


def author_name(ui: str) -> str:
    return load_settings()["author"][ui]


def author_bio(ui: str) -> str:
    return load_settings()["author-bio"][ui]


def absolute(src: str | None) -> str | None:
    """Absolute URL of an image: site-relative paths get the site URL."""
    if not src:
        return None
    return src if src.startswith(("https://", "http://")) else page_url(src.lstrip("./"))


# ── JSON-LD ───────────────────────────────────────────────────────────────────

def _person_id() -> str:
    return f"{site_url()}/#author"


def person(ui: str) -> dict:
    s = load_settings()
    names = sorted(set(s["author"].values()) - {s["author"][ui]})
    return {
        "@type": "Person",
        "@id": _person_id(),
        "name": s["author"][ui],
        "alternateName": names,
        "description": author_bio(ui),
        "url": page_url(f"{ui}/"),
        "image": absolute(s.get("author-photo")),
        "jobTitle": i18n.Translator(ui).raw("author_role"),
        "homeLocation": {"@type": "Place", "name": s["author-location"][ui]},
        "sameAs": [s["links"][k] for k in ("soundcloud", "instagram", "wikidata") if s["links"].get(k)],
    }


def home_ld(ui: str, entries: list[SongEntry], albums: list[Album]) -> list[dict]:
    return [
        person(ui),
        {
            "@type": "WebSite",
            "name": i18n.Translator(ui).raw("site_title"),
            "url": page_url(f"{ui}/"),
            "inLanguage": ui,
            "author": {"@id": _person_id()},
        },
        {
            "@type": "ItemList",
            "name": i18n.Translator(ui).raw("songs"),
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "url": page_url(song_path(e, ui)), "name": e.title(ui)}
                for i, e in enumerate(entries)
            ],
        },
    ]


def album_ld(ui: str, album: Album, songs: list[SongEntry]) -> list[dict]:
    return [{
        "@type": "MusicAlbum",
        "name": album.title(ui),
        "url": page_url(album_path(album, ui)),
        "datePublished": album.year,
        "byArtist": {"@id": _person_id(), "@type": "Person", "name": album.author(ui)},
        "image": absolute(f"albums/{album.folder}/{album.data.get('cover-image', 'cover.png')}"),
        "numTracks": len(songs),
        "track": [{"@type": "MusicRecording", "name": e.title(ui), "url": page_url(song_path(e, ui))} for e in songs],
    }]


def song_ld(ui: str, entry: SongEntry, album: Album | None) -> list[dict]:
    meta = entry.meta(ui)
    ld = {
        "@type": "MusicComposition",
        "name": entry.title(ui),
        "alternateName": sorted({entry.title(lang) for lang in ui_languages()} - {entry.title(ui)}),
        "url": page_url(song_path(entry, ui)),
        "datePublished": entry.date,
        "inLanguage": entry.song_languages,
        "composer": {"@type": "Person", "name": meta["composer"]},
        "lyricist": {"@type": "Person", "name": meta["lyricist"]},
        "image": absolute(entry.cover_src("")),
        "lyrics": {"@type": "CreativeWork", "inLanguage": entry.original.lang,
                   "url": page_url(chords_pdf_path(entry))},
        "workTranslation": [
            {"@type": "CreativeWork", "inLanguage": v.lang, "url": page_url(lyrics_pdf_path(entry, v.lang))}
            for v in entry.translations
        ],
    }
    if album:
        ld["isPartOf"] = {"@type": "MusicAlbum", "name": album.title(ui), "url": page_url(album_path(album, ui))}
    sc = entry.data.get("soundcloud")
    if sc:
        ld["recordedAs"] = {"@type": "MusicRecording", "name": entry.title(ui), "url": sc,
                            "byArtist": {"@id": _person_id()}}
    return [ld]


# ── Head tags ─────────────────────────────────────────────────────────────────

def head(ui: str, paths: dict[str, str], description: str, ld: list[dict],
         image: str | None = None, og_type: str = "website") -> str:
    """Description, canonical + hreflang alternates, Open Graph and JSON-LD for one page.

    `paths`: the page's path in every UI language (site-relative, e.g. "en/songs/…/").
    """
    s = load_settings()
    url = page_url(paths[ui])
    tags = [
        f'<meta name="description" content="{escape(description)}">',
        f'<meta name="author" content="{escape(author_name(ui))}">',
        f'<link rel="canonical" href="{escape(url)}">',
    ]
    tags += [f'<link rel="alternate" hreflang="{lang}" href="{escape(page_url(p))}">' for lang, p in paths.items()]
    tags.append(f'<link rel="alternate" hreflang="x-default" href="{escape(page_url(paths[s["default-ui-language"]]))}">')
    og = {
        "og:type": og_type, "og:site_name": i18n.Translator(ui).raw("site_title"), "og:url": url,
        "og:description": description, "og:locale": OG_LOCALES.get(ui, ui),
        "og:image": absolute(image or s.get("author-photo")),
    }
    tags += [f'<meta property="{k}" content="{escape(v)}">' for k, v in og.items() if v]
    tags.append('<meta name="twitter:card" content="summary">')
    # Search console ownership checks (settings.json "verification"; empty = not set up yet)
    names = {"google": "google-site-verification", "bing": "msvalidate.01"}
    tags += [f'<meta name="{names[k]}" content="{escape(v)}">'
             for k, v in s.get("verification", {}).items() if v and k in names]
    if ld:
        graph = {"@context": "https://schema.org", "@graph": ld}
        data = json.dumps(graph, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        tags.append(f'<script type="application/ld+json">{data}</script>')
    return "\n".join(tags) + "\n"


def og_title(title: str) -> str:
    return f'<meta property="og:title" content="{escape(title)}">\n'


# ── Descriptions ──────────────────────────────────────────────────────────────

def song_description(ui: str, entry: SongEntry) -> str:
    t = i18n.Translator(ui)
    first = next((ln for ln in _lines(entry.lyrics_for(ui)) if ln), "").rstrip(" ,.;:!?-—…")
    return t.raw("seo_song").format(title=entry.title(ui), author=entry.meta(ui)["composer"],
                                    langs="/".join(entry.song_languages), first=first)


def album_description(ui: str, album: Album, count: int) -> str:
    return i18n.Translator(ui).raw("seo_album").format(title=album.title(ui), year=album.year,
                                                      author=album.author(ui), count=count)


def _lines(variant) -> list[str]:
    from .chordpro import Line, Section
    out = []
    for block in variant.song.body:
        if isinstance(block, Section):
            for item in block.items:
                if isinstance(item, Line):
                    out.append("".join(s.text for s in item.segments).strip())
    return out


# ── robots.txt, sitemap.xml, llms.txt ─────────────────────────────────────────────────────

AI_CRAWLERS = [
    "GPTBot", "OAI-SearchBot", "ChatGPT-User",                  # OpenAI
    "ClaudeBot", "Claude-SearchBot", "Claude-User",              # Anthropic
    "PerplexityBot", "Perplexity-User",                          # Perplexity
    "Google-Extended", "Applebot-Extended",                      # Gemini / Apple Intelligence
    "CCBot", "meta-externalagent",                               # Common Crawl, Meta AI
]


def robots_txt() -> str:
    """Everyone may crawl everything; AI crawlers are named so their allowance is explicit.

    Crawlers read robots.txt only at the domain root: on a custom domain this file is it;
    on sergiorykov.github.io/music/ it has to be copied to the sergiorykov.github.io repository.
    """
    agents = "\n".join(f"User-agent: {a}" for a in AI_CRAWLERS)
    return (
        "User-agent: *\nAllow: /\n\n"
        f"# AI crawlers and agents: training, AI search and user-requested fetches\n{agents}\nAllow: /\n\n"
        f"Sitemap: {site_url()}/sitemap.xml\n"
        f"# For AI agents: {site_url()}/llms.txt\n"
    )


def sitemap(entries: list[SongEntry], albums: list[Album]) -> str:
    groups: list[tuple[dict[str, str], str | None]] = [({lang: f"{lang}/" for lang in ui_languages()}, None)]
    groups.append(({lang: songbook_web_path(lang) for lang in ui_languages()}, None))
    groups.append(({lang: about_path(lang) for lang in ui_languages()}, None))
    groups += [({lang: album_path(a, lang) for lang in ui_languages()}, None) for a in albums]
    groups += [({lang: song_path(e, lang) for lang in ui_languages()}, e.date) for e in entries]
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for paths, date in groups:
        alts = "".join(f'<xhtml:link rel="alternate" hreflang="{lang}" href="{escape(page_url(p))}"/>'
                       for lang, p in paths.items())
        for p in paths.values():
            lastmod = f"<lastmod>{date}</lastmod>" if date else ""
            out.append(f"  <url><loc>{escape(page_url(p))}</loc>{lastmod}{alts}</url>")
    out.append("</urlset>")
    return "\n".join(out) + "\n"


def llms_txt(entries: list[SongEntry], albums: dict[str, Album]) -> str:
    """llms.txt (https://llmstxt.org): who the author is and where everything is, for AI agents."""
    s = load_settings()
    en, ru = "en", "ru"
    lines = [
        f"# {s['author'][en]} ({s['author'][ru]}) — {i18n.Translator(en).raw('site_title').split('— ')[-1]}",
        "",
        f"> {author_bio(en)}",
        "",
        author_bio(ru),
        "",
        f"Site: {site_url()}/ — UI languages: {', '.join(ui_languages())}. "
        "Every song page has the original lyrics (with guitar chords, capo and transposition) "
        "and lyrics translations; PDFs with chords and lyrics; a songbook PDF per UI language; "
        f"a web songbook with every song and its chords, one per screen: {page_url(songbook_web_path('en'))}",
        "",
        "## Links",
        "",
        f"- [SoundCloud]({s['links']['soundcloud']}): recordings",
        f"- [Instagram]({s['links']['instagram']})",
        f"- [Source (GitHub)]({s['links']['github']}): ChordPro sources of every song",
        "",
        "## Albums",
        "",
    ]
    for a in albums.values():
        n = sum(1 for e in entries if e.album_id == a.id)
        lines.append(f"- [{a.title(en)} / {a.title(ru)}]({page_url(album_path(a, en))}) ({a.year}): {n} songs")
    lines += ["", "## Songs", ""]
    for e in entries:
        album = albums.get(e.album_id) if e.album_id else None
        m = e.meta(en)
        parts = [e.display_date, f"sung in {'/'.join(e.song_languages)}",
                 f"lyrics: {m['lyricist']}", f"music: {m['composer']}"]
        if album:
            parts.append(f"album: {album.title(en)}")
        if e.data.get("soundcloud"):
            parts.append(f"[listen]({e.data['soundcloud']})")
        parts.append(f"[chords PDF]({page_url(chords_pdf_path(e))})")
        lines.append(f"- [{e.title(en)} / {e.title(ru)}]({page_url(song_path(e, en))}): " + "; ".join(parts))
    songbooks = ", ".join(f"[{lang}]({page_url(songbook_pdf_path(lang))})" for lang in ui_languages())
    lines += ["", "## Optional", "",
              f"- Songbook PDFs: {songbooks}",
              f"- [Sitemap]({site_url()}/sitemap.xml)", ""]
    return "\n".join(lines)
