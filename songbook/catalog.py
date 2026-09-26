"""Song, album and settings metadata: discovery, loading and validation.

Layout:
  settings.json                  UI languages, author, links
  i18n.json                      UI strings (see songbook/i18n.py)
  albums/<Album>/album.json      album metadata, per metadata language
  songs/<song>/song.json         song metadata, per metadata language
  songs/<song>/<lang>.cho        lyrics + chords in ChordPro: the original lyrics
                                 and any lyrics translations, one file each
  <song> = <year>-<month>-<en slug>, e.g. 2024-03-take-care-of-yourself

Terms follow CONTEXT.md: UI language, Metadata language, Song language, Lyrics translation.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from . import chordpro

ROOT = Path(__file__).resolve().parent.parent
SONGS_DIR = ROOT / "songs"
ALBUMS_DIR = ROOT / "albums"
SETTINGS_PATH = ROOT / "settings.json"

FOLDER_LANGUAGE = "en"   # songs/<year>-<month>-<slug in this metadata language>/
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


class CatalogError(Exception):
    pass


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise CatalogError(f"{path}: invalid JSON: {e}") from None


@lru_cache(maxsize=1)
def load_settings() -> dict:
    return _read_json(SETTINGS_PATH)


def ui_languages() -> list[str]:
    return load_settings()["ui-languages"]


def _check_metadata(path: Path, data: dict, fields: tuple[str, ...]) -> None:
    """Every UI language needs every field; slugs must be URL-safe."""
    meta = data.get("metadata", {})
    for lang in ui_languages():
        entry = meta.get(lang)
        if not entry:
            raise CatalogError(f"{path}: metadata.{lang} is missing")
        for f in fields:
            if not entry.get(f):
                raise CatalogError(f"{path}: metadata.{lang}.{f} is missing")
        if not SLUG_RE.match(entry["slug"]):
            raise CatalogError(f"{path}: metadata.{lang}.slug '{entry['slug']}' must be lowercase a-z, 0-9 and dashes")


@dataclass
class Album:
    folder: str
    data: dict

    @property
    def id(self) -> str:
        return self.data["id"]

    @property
    def year(self) -> str:
        return self.data["year"]

    def meta(self, lang: str) -> dict:
        return self.data["metadata"][lang]

    def title(self, lang: str) -> str:
        return self.meta(lang)["title"]

    def slug(self, lang: str) -> str:
        return self.meta(lang)["slug"]

    def author(self, lang: str) -> str:
        return self.meta(lang)["author"]


@dataclass
class Variant:
    """One lyrics file of a song: the original lyrics or a lyrics translation."""
    lang: str
    song: chordpro.Song
    is_original: bool


@dataclass
class SongEntry:
    folder: str
    data: dict                      # song.json
    variants: dict[str, Variant]    # lyrics lang -> Variant, original first

    @property
    def id(self) -> str:
        return self.data["id"]

    @property
    def album_id(self) -> str | None:
        return self.data.get("album-id")

    @property
    def date(self) -> str:
        return self.data["date"]

    @property
    def display_date(self) -> str:
        year, month, day = self.date.split("-")
        return f"{day}.{month}.{year}"

    @property
    def song_languages(self) -> list[str]:
        return self.data["song-languages"]

    @property
    def original(self) -> Variant:
        return self.variants[self.data["original-lyrics"]]

    def meta(self, lang: str) -> dict:
        return self.data["metadata"][lang]

    def title(self, lang: str) -> str:
        return self.meta(lang)["title"]

    def url_slug(self, lang: str) -> str:
        """<year>-<month>-<slug>, the song's path segment for a UI language."""
        year, month, _ = self.date.split("-")
        return f"{year}-{month}-{self.meta(lang)['slug']}"

    def lyrics_for(self, ui_lang: str) -> Variant:
        """Lyrics shown by default: the translation into the UI language, else the original."""
        v = self.variants.get(ui_lang)
        return v if v is not None else self.original


def load_albums() -> dict[str, Album]:
    albums: dict[str, Album] = {}
    for folder in sorted(p for p in ALBUMS_DIR.iterdir() if p.is_dir()):
        path = folder / "album.json"
        if not path.exists():
            continue
        album = Album(folder.name, _read_json(path))
        _check_metadata(path, album.data, ("title", "slug", "author"))
        if not album.data.get("year"):
            raise CatalogError(f"{path}: year is missing")
        albums[album.id] = album
    _check_unique_slugs("album", {a.id: a.data for a in albums.values()})
    return albums


def load_song(folder: Path, albums: dict[str, Album]) -> SongEntry:
    path = folder / "song.json"
    data = _read_json(path)
    for key in ("id", "date", "song-languages", "original-lyrics"):
        if not data.get(key):
            raise CatalogError(f"{path}: '{key}' is missing")
    if not DATE_RE.match(data["date"]):
        raise CatalogError(f"{path}: date '{data['date']}' must be YYYY-MM-DD")
    _check_metadata(path, data, ("title", "slug"))
    if data.get("album-id") and data["album-id"] not in albums:
        raise CatalogError(f"{path}: unknown album-id '{data['album-id']}'")

    year, month, _ = data["date"].split("-")
    expected = f"{year}-{month}-{data['metadata'][FOLDER_LANGUAGE]['slug']}"
    if folder.name != expected:
        raise CatalogError(f"{folder}: folder must be named '{expected}' (<year>-<month>-<{FOLDER_LANGUAGE} slug>)")

    langs = sorted(p.stem for p in folder.glob("*.cho"))
    original = data["original-lyrics"]
    if original not in langs:
        raise CatalogError(f"{path}: original-lyrics '{original}' has no {original}.cho")

    ordered = [original] + [lang for lang in langs if lang != original]
    variants = {
        lang: Variant(lang, chordpro.parse(folder / f"{lang}.cho"), lang == original)
        for lang in ordered
    }
    capos = {lang: v.song.capo for lang, v in variants.items()}
    if len(set(capos.values())) > 1:
        raise CatalogError(f"{folder}: {{capo}} differs between lyrics files: {capos}")

    return SongEntry(folder.name, data, variants)


def _check_unique_slugs(kind: str, items: dict[str, dict]) -> None:
    for lang in ui_languages():
        seen: dict[str, str] = {}
        for item_id, data in items.items():
            slug = data["metadata"][lang]["slug"]
            if slug in seen:
                raise CatalogError(f"{kind} slug '{slug}' ({lang}) is used by both '{seen[slug]}' and '{item_id}'")
            seen[slug] = item_id


def check_song_slugs(entries: list[SongEntry]) -> None:
    """Song URLs are <year>-<month>-<slug>; they must be unique per UI language."""
    for lang in ui_languages():
        seen: dict[str, str] = {}
        for e in entries:
            url = e.url_slug(lang)
            if url in seen:
                raise CatalogError(f"song URL '{lang}/songs/{url}' is used by both '{seen[url]}' and '{e.folder}'")
            seen[url] = e.folder


def song_folders() -> list[Path]:
    return sorted(p for p in SONGS_DIR.iterdir() if (p / "song.json").exists())
