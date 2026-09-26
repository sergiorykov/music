"""Guitar voicings (fingerings): lookup in chords-db and song-level {define}s."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path

from .chordpro import Define
from .chords import SUFFIXES, Chord

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "chords-db" / "guitar.json"

_DB_KEYS = ["C", "Csharp", "D", "Eb", "E", "F", "Fsharp", "G", "Ab", "A", "Bb", "B"]
_DB_BASS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "Bb", "B"]


@dataclass(frozen=True)
class Voicing:
    base_fret: int
    frets: tuple[int, ...]            # low E -> high E; -1 muted, 0 open, n relative to base_fret
    fingers: tuple[int, ...] | None
    barres: tuple[int, ...]           # relative frets played as a barre

    @property
    def movable(self) -> bool:
        return 0 not in self.frets

    def shift(self, semitones: int) -> "Voicing":
        return replace(self, base_fret=(self.base_fret - 1 + semitones) % 12 + 1)


@lru_cache(maxsize=1)
def _db() -> dict:
    return json.loads(DB_PATH.read_text(encoding="utf-8"))["chords"]


def _from_db_position(p: dict) -> Voicing:
    return Voicing(
        base_fret=p["baseFret"],
        frets=tuple(p["frets"]),
        fingers=tuple(p["fingers"]) if p.get("fingers") else None,
        barres=tuple(p.get("barres", [])),
    )


def _db_positions(chord: Chord) -> list[dict]:
    suffix = SUFFIXES[chord.suffix]
    if chord.bass is not None:
        if chord.suffix not in ("", "m"):
            return []
        suffix = ("m" if chord.suffix == "m" else "") + "/" + _DB_BASS[chord.bass]
    for entry in _db()[_DB_KEYS[chord.root]]:
        if entry["suffix"] == suffix:
            return entry["positions"]
    return []


def _from_define(d: Define) -> Voicing:
    barres: tuple[int, ...] = ()
    if d.fingers:
        by_finger: dict[tuple[int, int], int] = {}
        for fret, finger in zip(d.frets, d.fingers):
            if fret > 0 and finger > 0:
                by_finger[(finger, fret)] = by_finger.get((finger, fret), 0) + 1
        barres = tuple(sorted({fret for (_, fret), n in by_finger.items() if n > 1}))
    return Voicing(d.base_fret, tuple(d.frets), tuple(d.fingers) if d.fingers else None, barres)


def lookup(written: Chord, define: Define | None, semitones: int) -> Voicing | None:
    """Voicing for `written` transposed by `semitones`, or None when unknown.

    A song-level {define} or a position hint like G(III) pins a specific shape;
    transposition slides that shape along the neck when it has no open strings.
    """
    target = written.transpose(semitones)

    if define is not None:
        v = _from_define(define)
        if semitones % 12 == 0:
            return v
        if v.movable:
            return v.shift(semitones)
        return lookup(replace(target, position=None), None, 0)

    positions = _db_positions(target)
    if written.position is not None:
        for p in positions:
            if p["baseFret"] == target.position:
                return _from_db_position(p)
        for p in _db_positions(written):
            if p["baseFret"] == written.position:
                v = _from_db_position(p)
                if v.movable:
                    return v.shift(semitones)
        return None

    return _from_db_position(positions[0]) if positions else None
