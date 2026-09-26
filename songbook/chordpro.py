"""Parser for a strict subset of the ChordPro 6 format (https://www.chordpro.org).

Supported:
  metadata     {title} {subtitle} {artist} {composer} {lyricist} {album} {year}
               {key} {capo} {tempo} {time} {duration} {copyright} {meta: name value}
  sections     {start_of_verse|chorus|bridge[: label]} ... {end_of_...}, short forms
  chorus ref   {chorus[: label]}
  comments     {comment} {comment_italic} {highlight}, lines starting with '#'
  chords       [Am] inline, {define: NAME base-fret N frets ... [fingers ...]}
  page breaks  {new_page} {column_break} (print only)
  extensions   {x_*} directives are accepted and ignored, per the spec

Anything else is a parse error: sources must stay portable ChordPro.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .chords import Chord, ChordError, Key, uses_german

META_DIRECTIVES = {
    "title": "title", "t": "title", "subtitle": "subtitle", "st": "subtitle",
    "artist": "artist", "composer": "composer", "lyricist": "lyricist",
    "album": "album", "year": "year", "key": "key", "capo": "capo",
    "tempo": "tempo", "time": "time", "duration": "duration", "copyright": "copyright",
}
SECTION_DIRECTIVES = {
    "start_of_verse": ("start", "verse"), "sov": ("start", "verse"),
    "end_of_verse": ("end", "verse"), "eov": ("end", "verse"),
    "start_of_chorus": ("start", "chorus"), "soc": ("start", "chorus"),
    "end_of_chorus": ("end", "chorus"), "eoc": ("end", "chorus"),
    "start_of_bridge": ("start", "bridge"), "sob": ("start", "bridge"),
    "end_of_bridge": ("end", "bridge"), "eob": ("end", "bridge"),
}
COMMENT_DIRECTIVES = {
    "comment": "comment", "c": "comment", "highlight": "comment",
    "comment_italic": "comment_italic", "ci": "comment_italic",
}
BREAK_DIRECTIVES = {"new_page", "np", "column_break", "colb"}

_DIRECTIVE_RE = re.compile(r"^\{\s*([a-z_][a-z0-9_]*)\s*(?::\s*(.*?))?\s*\}$", re.IGNORECASE)
_CHORD_RE = re.compile(r"\[([^\]]*)\]")


class ChordProError(Exception):
    pass


@dataclass
class Segment:
    chord: str | None   # chord name as written, None for leading lyrics
    text: str


@dataclass
class Line:
    segments: list[Segment]

    @property
    def has_chords(self) -> bool:
        return any(s.chord for s in self.segments)


@dataclass
class Comment:
    text: str
    italic: bool = False


@dataclass
class Blank:
    pass


@dataclass
class PageBreak:
    pass


@dataclass
class Section:
    kind: str                     # verse | chorus | bridge | none
    label: str | None = None
    items: list = field(default_factory=list)   # Line | Comment | Blank


@dataclass
class ChorusRef:
    label: str | None = None


@dataclass
class Define:
    name: str
    base_fret: int
    frets: list[int]          # -1 muted, 0 open, n = fret relative to base_fret
    fingers: list[int] | None


@dataclass
class Song:
    path: Path
    german: bool = False            # chords written in German notation (H = B natural)
    meta: dict[str, list[str]] = field(default_factory=dict)
    body: list = field(default_factory=list)         # Section | ChorusRef | PageBreak
    defines: dict[str, Define] = field(default_factory=dict)

    def get(self, name: str, default: str | None = None) -> str | None:
        values = self.meta.get(name)
        return values[0] if values else default

    def get_all(self, name: str) -> list[str]:
        return self.meta.get(name, [])

    @property
    def key(self) -> Key:
        return Key.parse(self.get("key"), self.german)

    @property
    def capo(self) -> int:
        return int(self.get("capo", "0"))

    def chords_in_order(self) -> list[str]:
        """Unique chord names in order of first appearance."""
        seen: dict[str, None] = {}
        for block in self.body:
            if isinstance(block, Section):
                for item in block.items:
                    if isinstance(item, Line):
                        for seg in item.segments:
                            if seg.chord:
                                seen.setdefault(seg.chord)
        return list(seen)


def _parse_label(value: str | None) -> str | None:
    if not value:
        return None
    m = re.match(r'^label\s*=\s*"(.*)"$', value)
    return m[1] if m else value


def _parse_define(value: str) -> Define:
    tokens = value.split()
    if not tokens:
        raise ChordProError("empty {define}")
    name, rest = tokens[0], tokens[1:]
    base_fret, frets, fingers = 1, None, None
    i = 0
    while i < len(rest):
        word = rest[i]
        if word == "base-fret":
            base_fret = int(rest[i + 1])
            i += 2
        elif word in ("frets", "fingers"):
            vals = rest[i + 1:i + 7]
            if len(vals) != 6:
                raise ChordProError(f"{{define: {name}}}: '{word}' needs 6 values")
            if word == "frets":
                frets = [-1 if v.lower() in ("x", "n", "-1") else int(v) for v in vals]
            else:
                fingers = [0 if v.lower() in ("x", "n", "-", "0") else int(v) for v in vals]
            i += 7
        else:
            raise ChordProError(f"{{define: {name}}}: unexpected '{word}'")
    if frets is None:
        raise ChordProError(f"{{define: {name}}}: 'frets' is required")
    return Define(name, base_fret, frets, fingers)


def _parse_line(text: str) -> Line:
    segments: list[Segment] = []
    pos = 0
    chord: str | None = None
    for m in _CHORD_RE.finditer(text):
        lyric = text[pos:m.start()]
        if lyric or chord is not None:
            segments.append(Segment(chord, lyric))
        chord = m[1].strip()
        pos = m.end()
    tail = text[pos:]
    if tail or chord is not None:
        segments.append(Segment(chord, tail))
    return Line(segments)


def parse(path: Path) -> Song:
    song = Song(path=path)
    errors: list[str] = []
    current: Section | None = None

    def section() -> Section:
        nonlocal current
        if current is None:
            current = Section("none")
            song.body.append(current)
        return current

    def err(lineno: int, msg: str) -> None:
        errors.append(f"{path}:{lineno}: {msg}")

    chord_refs: list[tuple[int, str]] = []    # validated once the notation is known

    lines = path.read_text(encoding="utf-8").splitlines()
    for lineno, raw in enumerate(lines, 1):
        line = raw.rstrip()
        if line.startswith("#"):
            continue

        m = _DIRECTIVE_RE.match(line.strip())
        if m:
            name, value = m[1].lower(), m[2]
            if name in META_DIRECTIVES:
                song.meta.setdefault(META_DIRECTIVES[name], []).append(value or "")
            elif name == "meta":
                parts = (value or "").split(None, 1)
                if len(parts) != 2:
                    err(lineno, "{meta} needs a name and a value")
                else:
                    song.meta.setdefault(parts[0], []).append(parts[1])
            elif name in SECTION_DIRECTIVES:
                action, kind = SECTION_DIRECTIVES[name]
                if action == "start":
                    if current is not None and current.kind != "none":
                        err(lineno, f"{{{name}}} inside unfinished {current.kind}")
                    current = Section(kind, _parse_label(value))
                    song.body.append(current)
                else:
                    if current is None or current.kind != kind:
                        err(lineno, f"{{{name}}} without matching start")
                    current = None
            elif name == "chorus":
                current = None
                song.body.append(ChorusRef(_parse_label(value)))
            elif name in COMMENT_DIRECTIVES:
                section().items.append(Comment(value or "", COMMENT_DIRECTIVES[name] == "comment_italic"))
            elif name == "define":
                try:
                    d = _parse_define(value or "")
                    chord_refs.append((lineno, d.name))
                    song.defines[d.name] = d
                except (ChordProError, ChordError, ValueError) as e:
                    err(lineno, str(e))
            elif name in BREAK_DIRECTIVES:
                current = None
                song.body.append(PageBreak())
            elif name.startswith("x_"):
                pass
            else:
                err(lineno, f"unsupported directive {{{name}}}")
            continue

        if not line.strip():
            if current is not None and current.kind == "none":
                current = None              # blank line ends an implicit block
            elif current is not None and current.items:
                current.items.append(Blank())
            continue

        parsed = _parse_line(line)
        for seg in parsed.segments:
            if seg.chord is None:
                continue
            if not seg.chord:
                err(lineno, "empty chord []")
                continue
            chord_refs.append((lineno, seg.chord))
        section().items.append(parsed)

    if current is not None and current.kind != "none":
        err(len(lines), f"unterminated {current.kind} section")

    song.german = uses_german([name for _, name in chord_refs])
    for lineno, name in chord_refs:
        try:
            Chord.parse(name, song.german)
        except ChordError as e:
            err(lineno, str(e))

    for required in ("title", "key"):
        if not song.get(required):
            err(1, f"missing required {{{required}}}")
    if song.get("key"):
        try:
            song.key
        except ChordError as e:
            err(1, str(e))
    if song.get("capo") and not song.get("capo").isdigit():
        err(1, f"invalid {{capo: {song.get('capo')}}}")

    if errors:
        raise ChordProError("\n".join(errors))
    return song
