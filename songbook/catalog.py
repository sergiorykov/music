"""Song, album and settings metadata: discovery, loading and validation.

Layout:
  settings.json                   global settings and UI labels per language
  albums/<Album>/album.json       album metadata
  songs/<Song>/song.json          data shared by all languages of a song
  songs/<Song>/<lang>.cho         lyrics + chords in ChordPro, one file per language
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from . import chordpro

ROOT = Path(__file__).resolve().parent.parent
SONGS_DIR = ROOT / "songs"
ALBUMS_DIR = ROOT / "albums"
SETTINGS_PATH = ROOT / "settings.json"


class CatalogError(Exception):
    pass


@dataclass
class Album:
    folder: str
    data: dict

    @property
    def id(self) -> str:
        return self.data["id"]

    def name(self, lang: str) -> str:
        return self.data.get("languages", {}).get(lang, {}).get("album", self.data["album"])

    def author(self, lang: str) -> str:
        return self.data.get("languages", {}).get(lang, {}).get("author", self.data["author"])

    @property
    def year(self) -> str:
        return self.data.get("album-year", "")


@dataclass
class Variant:
    """One language version of a song."""
    lang: str
    song: chordpro.Song


@dataclass
class SongEntry:
    folder: str
    data: dict                      # song.json
    variants: dict[str, Variant]    # lang -> Variant, default language first

    @property
    def default_language(self) -> str:
        return self.data["default-language"]

    @property
    def album_id(self) -> str | None:
        return self.data.get("album-id")


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise CatalogError(f"{path}: invalid JSON: {e}") from None


def load_settings() -> dict:
    return _read_json(SETTINGS_PATH)


def load_albums() -> dict[str, Album]:
    albums: dict[str, Album] = {}
    for folder in sorted(p for p in ALBUMS_DIR.iterdir() if p.is_dir()):
        path = folder / "album.json"
        if path.exists():
            album = Album(folder.name, _read_json(path))
            albums[album.id] = album
    return albums


def load_song(folder: Path, albums: dict[str, Album]) -> SongEntry:
    data = _read_json(folder / "song.json")
    langs = sorted(p.stem for p in folder.glob("*.cho"))
    if not langs:
        raise CatalogError(f"{folder}: no <lang>.cho files")

    default = data.get("default-language")
    if default not in langs:
        raise CatalogError(f"{folder}/song.json: default-language '{default}' has no {default}.cho")
    if data.get("album-id") and data["album-id"] not in albums:
        raise CatalogError(f"{folder}/song.json: unknown album-id '{data['album-id']}'")

    ordered = [default] + [lang for lang in langs if lang != default]
    variants = {lang: Variant(lang, chordpro.parse(folder / f"{lang}.cho")) for lang in ordered}

    capos = {lang: v.song.capo for lang, v in variants.items()}
    if len(set(capos.values())) > 1:
        raise CatalogError(f"{folder}: {{capo}} differs between languages: {capos}")

    return SongEntry(folder.name, data, variants)


def song_folders() -> list[Path]:
    """Song folders migrated to ChordPro (those with a song.json)."""
    return sorted(p for p in SONGS_DIR.iterdir() if (p / "song.json").exists())
