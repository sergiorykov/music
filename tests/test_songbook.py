"""Unit tests for the songbook pipeline. Run: python -m unittest discover tests"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from songbook import chordpro, i18n  # noqa: E402
from songbook.chords import Chord, ChordError, Key  # noqa: E402
from songbook.render import chord_tables  # noqa: E402
from songbook.voicings import lookup  # noqa: E402


def parse_text(text: str) -> chordpro.Song:
    with tempfile.NamedTemporaryFile("w", suffix=".cho", delete=False, encoding="utf-8") as f:
        f.write(text)
    return chordpro.parse(Path(f.name))


class ChordTests(unittest.TestCase):
    def test_parse_and_name(self):
        for name in ["Am", "C", "E7", "F#m7", "Bbmaj7", "C/G", "Am/C", "Dsus4", "G(III)"]:
            self.assertEqual(Chord.parse(name).name(flats="b" in name), name)

    def test_cyrillic_is_rejected_with_hint(self):
        with self.assertRaises(ChordError) as ctx:
            Chord.parse("С")          # Cyrillic
        self.assertIn("Cyrillic", str(ctx.exception))

    def test_transpose_spelling_follows_key(self):
        key = Key.parse("Am").transpose(3)        # capo 3 -> Cm, a flat key
        self.assertEqual(key.name(), "Cm")
        self.assertEqual(Chord.parse("F").transpose(3).name(key.flats), "Ab")
        self.assertEqual(Chord.parse("E7").transpose(3).name(key.flats), "G7")
        sharp = Key.parse("Am").transpose(2)      # Bm, a sharp key
        self.assertEqual(Chord.parse("Em").transpose(2).name(sharp.flats), "F#m")

    def test_position_hint_moves_with_transposition(self):
        self.assertEqual(Chord.parse("G(III)").transpose(4).name(False), "B(VII)")


class VoicingTests(unittest.TestCase):
    def test_open_chord_from_db(self):
        v = lookup(Chord.parse("Am"), None, 0)
        self.assertEqual((v.base_fret, v.frets), (1, (-1, 0, 2, 2, 1, 0)))

    def test_position_hint_picks_barre(self):
        v = lookup(Chord.parse("G(III)"), None, 0)
        self.assertEqual((v.base_fret, v.frets), (3, (1, 3, 3, 2, 1, 1)))
        self.assertEqual(lookup(Chord.parse("G(III)"), None, 2).base_fret, 5)


class ChordProTests(unittest.TestCase):
    SONG = "{title: T}\n{key: Am}\n{capo: 3}\n{soc}\n[Am]Так [C]бывает\n{eoc}\n{chorus}\n"

    def test_parse_structure(self):
        song = parse_text(self.SONG)
        self.assertEqual(song.capo, 3)
        self.assertEqual(song.chords_in_order(), ["Am", "C"])
        self.assertIsInstance(song.body[0], chordpro.Section)
        self.assertEqual(song.body[0].kind, "chorus")
        self.assertIsInstance(song.body[1], chordpro.ChorusRef)

    def test_errors_carry_line_numbers(self):
        with self.assertRaises(chordpro.ChordProError) as ctx:
            parse_text("{title: T}\n{key: Am}\n[С]текст\n{bogus}\n")
        msg = str(ctx.exception)
        self.assertIn(":3: unknown chord", msg)
        self.assertIn(":4: unsupported directive {bogus}", msg)

    def test_missing_key_is_an_error(self):
        with self.assertRaises(chordpro.ChordProError):
            parse_text("{title: T}\n[Am]x\n")

    def test_tables_sound_mode_applies_capo(self):
        names, keys, diagrams, warnings = chord_tables(parse_text(self.SONG))
        self.assertEqual(names["shape"][0], ["Am", "C"])
        self.assertEqual(names["sound"][0], ["Cm", "Eb"])
        self.assertEqual(keys["sound"][0], "Cm")
        self.assertIn("Eb", diagrams)
        self.assertEqual(warnings, [])


class I18nTests(unittest.TestCase):
    def test_every_key_has_every_ui_language(self):
        i18n.validate()

    def test_format_and_escape(self):
        t = i18n.Translator("pt")
        self.assertEqual(t.raw("capo_fret", capo=3), "3ª casa")
        self.assertEqual(i18n.Translator("en")("song_page"), "Lyrics &amp; chords")


if __name__ == "__main__":
    unittest.main()
