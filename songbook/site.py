"""README.md: regenerate the song table between <!-- songs:start --> and <!-- songs:end -->."""

from __future__ import annotations

import re

from .catalog import ROOT, SongEntry
from .pages import pdf_path, song_path

README_MD = ROOT / "README.md"
PAGES_BASE = "https://sergiorykov.github.io/music"
README_UI = "en"


def _md_link(text: str, url: str | None) -> str:
    return f"[{text}]({url})" if url else text


def _readme_row(entry: SongEntry) -> str:
    br = "<br>"
    meta = entry.meta(README_UI)
    original = entry.original.song
    sheets = br.join(
        f"[{v.lang.upper()}{'' if v.is_original else ' (translation)'}]"
        f"({PAGES_BASE}/{pdf_path(entry, v.lang)})"
        for v in entry.variants.values()
    )
    sc = entry.data.get("soundcloud")
    authors = []
    if meta.get("lyricist"):
        authors.append(f"Lyrics: {_md_link(meta['lyricist'], original.get('lyricist_url'))}")
    if meta.get("composer"):
        authors.append(
            f"Music: {_md_link(meta['composer'], entry.data.get('music-author-url'))} · {entry.display_date}"
        )
    title = f"[{meta['title']}]({PAGES_BASE}/{song_path(entry, README_UI)})"
    if entry.original.lang != README_UI:
        title += f"<br>{entry.title(entry.original.lang)}"
    return (
        f"| {title} | {', '.join(entry.song_languages)} | {sheets} | "
        f"{_md_link('Listen', sc) if sc else '—'} | {br.join(authors) or '—'} |"
    )


def update_readme(entries: list[SongEntry]) -> bool:
    text = README_MD.read_text(encoding="utf-8")
    table = (
        "| Song | Sung in | PDF | SoundCloud | Authors |\n"
        "|------|---------|-----|------------|---------|\n"
        + "\n".join(_readme_row(e) for e in sorted(entries, key=lambda e: e.date, reverse=True))
    )
    block = f"<!-- songs:start -->\n{table}\n<!-- songs:end -->"
    updated = re.sub(r"<!-- songs:start -->.*?<!-- songs:end -->", lambda _: block, text, flags=re.DOTALL)
    if updated == text:
        return False
    README_MD.write_text(updated, encoding="utf-8")
    return True
