"""Site paths and URLs: pages, PDFs and the print pages PDFs are made from.

  /<ui>/songs/<year>-<month>-<slug>/          song page
  /<ui>/albums/<slug>/                        album page
  /<ui>/songbook/                             web songbook (songs with chords, one per screen)
  /pdf/<author>-<song id>-chords-<lang>.pdf   original lyrics with chords (primary song language)
  /pdf/<author>-<song id>-lyrics-<ui>.pdf     lyrics only, in a UI language (translation or original)
  /pdf/<author>-songs-<ui>.pdf                songbook
"""

from __future__ import annotations

from .catalog import Album, SongEntry, load_settings, ui_languages


def site_url() -> str:
    return load_settings()["site-url"].rstrip("/")


def page_url(path: str) -> str:
    return f"{site_url()}/{path}"


def _author() -> str:
    return load_settings()["author-slug"]


def song_path(entry: SongEntry, ui: str) -> str:
    return f"{ui}/songs/{entry.url_slug(ui)}/"


def album_path(album: Album, ui: str) -> str:
    return f"{ui}/albums/{album.slug(ui)}/"


def songbook_web_path(ui: str) -> str:
    """Web songbook: every song with chords, one per screen (for a tablet)."""
    return f"{ui}/songbook/"


def chords_pdf_path(entry: SongEntry) -> str:
    return f"pdf/{_author()}-{entry.id}-chords-{entry.original.lang}.pdf"


def lyrics_pdf_path(entry: SongEntry, ui: str) -> str:
    return f"pdf/{_author()}-{entry.id}-lyrics-{ui}.pdf"


def chords_print_path(entry: SongEntry) -> str:
    return f"print/{entry.folder}/chords.html"


def lyrics_print_path(entry: SongEntry, ui: str) -> str:
    return f"print/{entry.folder}/lyrics-{ui}.html"


def songbook_pdf_path(ui: str) -> str:
    return f"pdf/{_author()}-songs-{ui}.pdf"


def songbook_print_path(ui: str) -> str:
    return f"print/songbook/{ui}.html"


def original_ui(entry: SongEntry) -> str:
    """UI language that fits the original lyrics (for its labels and links)."""
    langs = ui_languages()
    for lang in entry.song_languages:
        if lang in langs:
            return lang
    return load_settings()["default-ui-language"]
