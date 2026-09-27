"""Unit tests for the songbook pipeline. Run: python -m unittest discover tests"""

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from songbook import catalog, chordpro, i18n, pages, seo  # noqa: E402
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

    def test_german_notation_h_is_b_natural(self):
        h7 = Chord.parse("H7", german=True)
        self.assertEqual((h7.root, h7.suffix), (11, "7"))
        self.assertEqual(h7.name(False), "H7")                       # kept as written
        self.assertEqual(Chord.parse("B", german=True).root, 10)      # German B = B flat
        key = Key.parse("Em", german=True).transpose(2)                # capo 2 -> F#m
        self.assertEqual(h7.transpose(2).name(key.flats), "C#7")
        self.assertEqual(Chord.parse("Am/H", german=True).transpose(2).name(key.flats), "Hm/C#")
        with self.assertRaises(ChordError):
            Chord.parse("H7")                                          # H needs German notation

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

    def test_song_with_h_is_german(self):
        song = parse_text("{title: T}\n{key: Em}\n[Em]a [H7]b [B]c\n")
        self.assertTrue(song.german)
        names, keys, _, _ = chord_tables(song)
        self.assertEqual(names["shape"][1], ["Fm", "C7", "H"])       # +1: B flat -> H in German
        self.assertFalse(parse_text("{title: T}\n{key: Em}\n[Em]a [B7]b\n").german)
        self.assertTrue(parse_text("{title: T}\n{key: Am}\n[Am]a [Am/H]b\n").german)   # H only in the bass

    def test_key_is_optional_in_lyrics_only_files(self):
        song = parse_text("{title: T}\nlyrics only\n")      # the catalog requires {key} in the original
        self.assertIsNone(song.get("key"))
        self.assertEqual(chord_tables(song)[2], {})

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
        self.assertEqual(t.raw("capo_fret", capo=3), "3.º traste")
        self.assertEqual(i18n.Translator("en")("pdf_hint"), "Printable PDF")


class CatalogTests(unittest.TestCase):
    def test_real_catalog_loads_and_slugs_are_unique(self):
        albums = catalog.load_albums()
        entries = [catalog.load_song(f, albums) for f in catalog.song_folders()]
        catalog.check_song_slugs(entries)
        beregi = next(e for e in entries if e.id == "beregi-sebya")
        self.assertEqual(beregi.url_slug("en"), "2024-03-take-care-of-yourself")
        self.assertEqual(beregi.song_languages, ["ru"])
        self.assertTrue(beregi.original.is_original)
        self.assertEqual(beregi.lyrics_for("en").lang, "en")   # translation exists
        self.assertEqual(beregi.lyrics_for("pt").lang, "pt")   # automatic translation
        self.assertEqual([v.lang for v in beregi.translations], ["en", "pt"])
        self.assertEqual(beregi.cover_src("../../"), "../../songs/2024-03-take-care-of-yourself/cover.png")
        beregi.data["cover-image"] = "https://i1.sndcdn.com/a.jpg"
        self.assertEqual(beregi.cover_src("../../"), "https://i1.sndcdn.com/a.jpg")


def make_song(tmp: Path, cho: dict[str, str], **extra) -> Path:
    """A minimal song folder 2020-01-x with the given lyrics files."""
    import json
    folder = tmp / "2020-01-x"
    folder.mkdir()
    meta = {lang: {"title": "X", "slug": "x"} for lang in catalog.ui_languages()}
    data = {"id": "x", "date": "2020-01-01", "song-languages": ["ru"], "original-lyrics": "ru",
            "metadata": meta, **extra}
    (folder / "song.json").write_text(json.dumps(data), encoding="utf-8")
    for lang, text in cho.items():
        (folder / f"{lang}.cho").write_text(text, encoding="utf-8")
    return folder


class LanguageModelTests(unittest.TestCase):
    ORIGINAL = "{title: X}\n{key: Am}\n[Am]слова\n"

    def test_translation_must_be_lyrics_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = make_song(Path(tmp), {"ru": self.ORIGINAL, "en": "{title: X}\n[Am]words\n"})
            with self.assertRaisesRegex(catalog.CatalogError, "lyrics only"):
                catalog.load_song(folder, {})

    def test_original_needs_key_and_a_song_language(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = make_song(Path(tmp), {"ru": "{title: X}\nслова\n"})
            with self.assertRaisesRegex(catalog.CatalogError, "need"):
                catalog.load_song(folder, {})
        with tempfile.TemporaryDirectory() as tmp:
            folder = make_song(Path(tmp), {"ru": self.ORIGINAL}, **{"song-languages": ["en"]})
            with self.assertRaisesRegex(catalog.CatalogError, "song-languages"):
                catalog.load_song(folder, {})

    def test_language_versions_link_back(self):
        a = catalog.SongEntry("a", {"id": "a", "language-versions": ["b"]}, {})
        b = catalog.SongEntry("b", {"id": "b"}, {})
        with self.assertRaisesRegex(catalog.CatalogError, "link back"):
            catalog.check_language_versions([a, b])
        b.data["language-versions"] = ["a"]
        catalog.check_language_versions([a, b])
        with self.assertRaisesRegex(catalog.CatalogError, "unknown song"):
            catalog.check_language_versions([a])


class PagesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.albums = catalog.load_albums()
        cls.entries = [catalog.load_song(f, cls.albums) for f in catalog.song_folders()]
        cls.beregi = next(e for e in cls.entries if e.id == "beregi-sebya")

    def test_seo_head_links_every_ui_language_and_describes_the_song(self):
        album = self.albums[self.beregi.album_id]
        pt, _ = pages.song_page("pt", self.beregi, album)
        self.assertIn('<link rel="canonical" href="https://sergiorykov.github.io/music/pt/songs/', pt)
        for lang in ("ru", "en", "pt", "x-default"):
            self.assertIn(f'<link rel="alternate" hreflang="{lang}"', pt)
        ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', pt).group(1))
        song = ld["@graph"][0]
        self.assertEqual(song["@type"], "MusicComposition")
        self.assertEqual(song["lyricist"]["name"], "Tanya Pelikhovskaya")
        home = pages.home_page("ru", self.entries, list(self.albums.values()))
        self.assertIn("<title>Сергей Рыков — инди-музыка</title>", home)
        self.assertIn('"@type":"Person"', home)
        self.assertNotIn("google-site-verification", home)   # empty in settings.json until set up

    def test_sitemap_and_llms_txt_list_every_song(self):
        xml = seo.sitemap(self.entries, list(self.albums.values()))
        self.assertEqual(xml.count("<url>"), 3 * (1 + len(self.albums) + len(self.entries)))
        txt = seo.llms_txt(self.entries, self.albums)
        self.assertTrue(txt.startswith("# Sergio Rykov"))
        for e in self.entries:
            self.assertIn(e.title("en"), txt)

    def test_author_translation_is_marked_as_the_authors(self):
        popolam = next(e for e in self.entries if e.id == "popolam")
        self.assertTrue(popolam.variants["en"].by_author)
        self.assertFalse(popolam.variants["pt"].by_author)
        en, _ = pages.song_page("en", popolam, self.albums[popolam.album_id])
        self.assertIn("own translation. The song is sung in: ru", en)
        self.assertIn("translation</small>", en)

    def test_song_page_defaults_to_ui_language_lyrics(self):
        album = self.albums[self.beregi.album_id]
        en, _ = pages.song_page("en", self.beregi, album)
        self.assertIn('data-lyrics="en" data-original="0">', en)
        self.assertIn('data-lyrics="ru" data-original="1" hidden>', en)
        self.assertIn('href="../../../pdf/sergio-rykov-beregi-sebya-chords-ru.pdf"', en)   # original + chords
        self.assertIn('href="../../../pdf/sergio-rykov-beregi-sebya-lyrics-en.pdf"', en)   # UI language, lyrics only
        self.assertIn(">PDF chords RU</a>", en)
        pt, _ = pages.song_page("pt", self.beregi, album)
        self.assertIn('data-lyrics="pt" data-original="0">', pt)
        self.assertIn('class="auto-note"', pt)                      # translations say they are automatic
        self.assertIn('id="player-toggle" aria-pressed="true"', pt)  # SoundCloud player on by default
        self.assertIn('<div class="player" id="player"><iframe src="https://w.soundcloud.com/player/', pt)  # loads with the page
        self.assertNotIn('loading="lazy"', pt)
        other = self.entries[0] if self.entries[0] is not self.beregi else self.entries[1]
        linked, _ = pages.song_page("ru", self.beregi, album, [other])
        self.assertIn(f'href="../../../{pages.song_path(other, "ru")}"', linked)
        self.assertIn('href="../../../pt/albums/o-silencio/"', pt)
        self.assertIn('class="mode-lyrics"', pt)

    def test_home_filters_by_song_language(self):
        home = pages.home_page("ru", self.entries, list(self.albums.values()))
        self.assertIn('data-sung="ru"', home)
        self.assertIn("пою на", home)
        self.assertIn("https://github.com/sergiorykov/music", home)
        self.assertNotIn("Typst", home)
        en = pages.home_page("en", self.entries, list(self.albums.values()))
        self.assertNotIn(">PDF chords RU</a>", en)   # lists: lyrics, chords and SoundCloud only
        self.assertIn('original <span class="lang-tag">RU</span>', en)   # song language as a tag, not a Cyrillic title
        self.assertNotIn("original: ", en)
        self.assertIn('/#chords" target="_blank"', en)   # song pages open in a new tab
        self.assertIn('/#lyrics" target="_blank"', en)


    def test_print_pages_carry_links(self):
        from songbook.render import chords_print_page, lyrics_print_page
        album = self.albums[self.beregi.album_id]
        chords, _ = chords_print_page(self.beregi, album)
        self.assertIn('href="https://soundcloud.com/sergiorykov/beregi-sebya"', chords)
        self.assertIn('href="https://sergiorykov.github.io/music/ru/songs/2024-03-beregi-sebya/"', chords)
        lyrics = lyrics_print_page(self.beregi, album, "pt")
        self.assertIn('class="mode-lyrics print-page"', lyrics)
        self.assertIn('class="auto-note"', lyrics)
        self.assertIn("/music/pt/songs/2024-03-cuida-de-ti/", lyrics)

    def test_songbook_has_contents_and_every_song(self):
        from songbook.render import songbook_page
        html = songbook_page("en", self.entries, self.albums)
        for e in self.entries:
            self.assertIn(f'href="#song-{e.folder}"', html)
            self.assertIn(f'id="song-{e.folder}"', html)
        self.assertIn("Songbook", html)
        home = pages.home_page("pt", self.entries, list(self.albums.values()))
        self.assertIn('href="../pdf/sergio-rykov-songs-pt.pdf" download', home)

    def test_root_redirect_lists_ui_languages(self):
        html = pages.root_redirect()
        self.assertIn('["ru", "en", "pt"]', html)


if __name__ == "__main__":
    unittest.main()
