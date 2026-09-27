"""Chord names: parsing, transposition and key-aware enharmonic spelling.

A chord name has the form  ROOT [SUFFIX] [/BASS] [(POSITION)]
  ROOT      A-G (or A-H in German notation) with optional # or b
  SUFFIX    one of SUFFIXES (empty = major)
  BASS      optional slash bass note
  POSITION  optional Roman numeral fret hint, e.g. G(III) = G barre at 3rd fret

German notation (common in Russian songbooks): H = B natural, B = B flat.
A song is in German notation when any of its chords uses H; names keep that notation
when transposed (e.g. H7 -> C#7, Am/H -> Bm/C#, B -> H).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

NOTE_PC = {
    "C": 0, "B#": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "Fb": 4,
    "F": 5, "E#": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9,
    "A#": 10, "Bb": 10, "B": 11, "Cb": 11,
}
SHARP_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
FLAT_NAMES  = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

NOTE_PC_GERMAN = {**NOTE_PC, "B": 10, "H": 11, "H#": 0, "Hb": 10}
SHARP_NAMES_GERMAN = SHARP_NAMES[:11] + ["H"]
FLAT_NAMES_GERMAN = FLAT_NAMES[:10] + ["B", "H"]

# Pitch classes of keys conventionally written with flats.
FLAT_MAJOR_KEYS = {1, 3, 5, 8, 10}          # Db Eb F Ab Bb
FLAT_MINOR_KEYS = {0, 2, 3, 5, 7, 10}       # Cm Dm Ebm Fm Gm Bbm

# Chord suffix as written -> suffix name in chords-db.
SUFFIXES = {
    "": "major", "m": "minor", "7": "7", "m7": "m7", "maj7": "maj7",
    "6": "6", "m6": "m6", "9": "9", "m9": "m9", "maj9": "maj9", "69": "69",
    "11": "11", "m11": "m11", "13": "13", "add9": "add9", "madd9": "madd9",
    "sus2": "sus2", "sus4": "sus4", "7sus4": "7sus4", "dim": "dim", "dim7": "dim7",
    "aug": "aug", "aug7": "aug7", "m7b5": "m7b5", "mmaj7": "mmaj7",
    "7b5": "7b5", "7b9": "7b9", "7#9": "7#9",
}

_ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]

_SUFFIX_RE = "|".join(sorted((re.escape(s) for s in SUFFIXES if s), key=len, reverse=True))
_CHORD_RE = re.compile(
    rf"^(?P<root>[A-H][#b]?)(?P<suffix>{_SUFFIX_RE})?"
    rf"(?:/(?P<bass>[A-H][#b]?))?(?:\((?P<pos>[IVX]+)\))?$"
)


class ChordError(ValueError):
    pass


def roman(n: int) -> str:
    return _ROMAN[n - 1]


def from_roman(s: str) -> int:
    try:
        return _ROMAN.index(s) + 1
    except ValueError:
        raise ChordError(f"invalid fret position '({s})'") from None


def uses_flats(key_pc: int, minor: bool) -> bool:
    return key_pc in (FLAT_MINOR_KEYS if minor else FLAT_MAJOR_KEYS)


def note_name(pc: int, flats: bool, german: bool = False) -> str:
    if german:
        return (FLAT_NAMES_GERMAN if flats else SHARP_NAMES_GERMAN)[pc % 12]
    return (FLAT_NAMES if flats else SHARP_NAMES)[pc % 12]


def uses_german(names: list[str]) -> bool:
    """A song is in German notation when a chord root or bass is H."""
    return any(re.search(r"^H|/H", n) for n in names)


@dataclass(frozen=True)
class Chord:
    root: int                 # pitch class 0-11
    suffix: str               # key of SUFFIXES
    bass: int | None = None   # pitch class of slash bass
    position: int | None = None  # base fret hint from "(III)"
    german: bool = False      # written in German notation (H = B natural, B = B flat)

    @property
    def minor(self) -> bool:
        return self.suffix.startswith("m") and not self.suffix.startswith("maj")

    @classmethod
    def parse(cls, name: str, german: bool = False) -> "Chord":
        m = _CHORD_RE.match(name)
        if not m:
            hint = ""
            if any(ord(ch) > 127 for ch in name):
                hint = " (contains non-Latin characters, e.g. Cyrillic С instead of Latin C)"
            raise ChordError(f"unknown chord '{name}'{hint}")
        pcs = NOTE_PC_GERMAN if german else NOTE_PC
        if not german and "H" in (m["root"][0], (m["bass"] or " ")[0]):
            raise ChordError(f"'{name}' uses German H; the whole song must then be in German notation")
        bass = m["bass"]
        pos = m["pos"]
        return cls(
            root=pcs[m["root"]],
            suffix=m["suffix"] or "",
            bass=pcs[bass] if bass else None,
            position=from_roman(pos) if pos else None,
            german=german,
        )

    def transpose(self, semitones: int) -> "Chord":
        if semitones % 12 == 0:
            return self
        pos = self.position
        if pos is not None:
            pos = (pos - 1 + semitones) % 12 + 1
        return replace(
            self,
            root=(self.root + semitones) % 12,
            bass=None if self.bass is None else (self.bass + semitones) % 12,
            position=pos,
        )

    def name(self, flats: bool) -> str:
        s = note_name(self.root, flats, self.german) + self.suffix
        if self.bass is not None:
            s += "/" + note_name(self.bass, flats, self.german)
        if self.position is not None:
            s += f"({roman(self.position)})"
        return s


@dataclass(frozen=True)
class Key:
    tonic: int
    minor: bool
    german: bool = False

    @classmethod
    def parse(cls, name: str, german: bool = False) -> "Key":
        m = re.match(r"^([A-H][#b]?)(m?)$", name.strip())
        if not m or (not german and m[1][0] == "H"):
            raise ChordError(f"invalid key '{name}' (expected e.g. Am, C, F#m)")
        return cls((NOTE_PC_GERMAN if german else NOTE_PC)[m[1]], bool(m[2]), german)

    def transpose(self, semitones: int) -> "Key":
        return replace(self, tonic=(self.tonic + semitones) % 12)

    @property
    def flats(self) -> bool:
        return uses_flats(self.tonic, self.minor)

    def name(self) -> str:
        return note_name(self.tonic, self.flats, self.german) + ("m" if self.minor else "")
