---
name: import-song
description: Import a song into this songbook — lyrics with chords (text, chords-over-lyrics, or ChordPro), metadata in every UI language, song languages, album, cover, SoundCloud. Use when the user wants to add, import or publish a new song.
---

# Import a song

Read `CONTEXT.md` first and use its terms: **Song language** (what the song is sung in), **Original lyrics** (as sung, with chords), **Lyrics translation** (automatic, lyrics only), **Language version** (the same song recorded in another song language = a separate song), **Metadata language** / **UI language** (ru, en, pt — see `settings.json`).

## 1. Gather facts (ask only for what you cannot find)

- Lyrics with chords, in any form — these are the **original lyrics**
- **Song languages**: the language(s) it is sung in: one (`["ru"]`) or a mix (`["ru", "en"]`); for a mix pick the **primary song language** (ask) — it names the lyrics file and is `original-lyrics`
- **Language versions**: if the author recorded the song in another language too, that is a separate song (own folder, lyrics, SoundCloud); link both with `"language-versions": ["<other song id>"]` in each song.json
- Date (at least year + month) → `date: YYYY-MM-DD` (use `-01` for an unknown day, and say so)
- Album (`album-id` from `albums/*/album.json`, or none → offer the `new-album` skill); the author's rule: songs from 2024 on → `the-silence`, older → `kukla-masha`
- Capo, key; lyricist, composer (+ links), lyrics sources (links where the lyrics were published; label them in every UI language)
- SoundCloud track URL — everything else it can give, fetch yourself (next section)
- Cover image: from SoundCloud artwork unless the author gives a file

### SoundCloud track URL → facts (do this yourself, never ask the author for it)

1. Fetch oEmbed: `https://soundcloud.com/oembed?format=json&url=<track URL>`
   - Direct `curl` / WebFetch may be blocked by the environment's network policy (soundcloud.com, sndcdn.com). Then use an external fetcher tool if one is available (e.g. Nimble `nimble_extract` with `driver: vx6`, `output_format: plain_text`); report which route worked.
2. From the JSON take:
   - `title` (e.g. "Листья Оливы by Sergio Rykov") → song title; prefer the author's spelling from their message if it differs
   - `description` → the author usually pastes "Слова и музыка: …" (lyricist + composer), the date, `capo +N` and the lyrics with chords — compare with what the author sent and report differences
   - `thumbnail_url` → cover (`…-t500x500.jpg`)
3. Widget: `soundcloud-embed` = `https://w.soundcloud.com/player/?url=https%3A//api.soundcloud.com/tracks/soundcloud%253Atracks%253A<track id>&color=%23ff5500&auto_play=false&hide_related=false&show_comments=true&show_user=true&show_reposts=false&show_teaser=true` — the official embed form with the track id. Get the id from oEmbed's `html`, or render the widget with the permalink (`?url=https%3A//soundcloud.com/<user>/<track>&…`, e.g. Nimble `nimble_extract` with `driver: vx8`): it redirects to the track-id URL — store that one, never the permalink form.
4. Cover: download `thumbnail_url` into the song folder as `cover.jpg` and set `"cover-image": "cover.jpg"`. If the CDN is blocked, set `"cover-image"` to the `thumbnail_url` itself (an absolute URL works) and tell the author the cover is hot-linked.

Plan first: add the import as a step list to `docs/backlog.md`, commit and push (CLAUDE.md → Committing).

## 2. Metadata in every UI language

For each UI language in `settings.json` (`ru`, `en`, `pt`): `title`, `slug`, `lyricist`, `composer`.
- Portuguese is European Portuguese (pt-PT), never Brazilian
- Translate titles and credit names automatically; mark them as machine-translated in your summary so the author can review
- Slugs: lowercase `a-z0-9-`, transliterate Cyrillic (`Береги себя` → `beregi-sebya`), unique per language
- Names in en/pt use the Latin spelling the author uses publicly (`Sergio Rykov`)

## 3. Files

Folder: `songs/<yyyy>-<mm>-<en slug>/` (the build rejects any other name).

`song.json`:
```json
{
  "id": "<en or ru slug, ASCII, stable — used in PDF URLs>",
  "album-id": "the-silence",
  "date": "2024-03-22",
  "song-languages": ["ru"],
  "original-lyrics": "ru",
  "cover-image": "cover.png",
  "soundcloud": "https://soundcloud.com/...",
  "soundcloud-embed": "https://w.soundcloud.com/player/?url=...",
  "music-author-url": "https://soundcloud.com/sergiorykov/",
  "lyrics-sources": [
    { "url": "https://t.me/…", "label": { "ru": "текст tg", "en": "lyrics on Telegram", "pt": "letra no Telegram" } }
  ],
  "metadata": {
    "ru": { "title": "…", "slug": "…", "lyricist": "…", "composer": "…" },
    "en": { "title": "…", "slug": "…", "lyricist": "…", "composer": "…" },
    "pt": { "title": "…", "slug": "…", "lyricist": "…", "composer": "…" }
  }
}
```

`<primary song language>.cho` — the original lyrics with chords, strict ChordPro:
```
{title: Береги себя}
{lyricist: Таня Пелиховская}
{composer: Сергей Рыков}
{key: Am}
{capo: 4}
{meta: lyricist_url https://…}
{meta: lyrics_date 01.07.2016}

{start_of_verse}
[F]Береги себя [Em]только, слы[Am]шишь...
{end_of_verse}

{start_of_chorus}
…
{end_of_chorus}

{chorus}
```

### Automatic lyrics translations

If the author gives their own translation of the lyrics, use it as `<lang>.cho` (lyrics only) and list the language in `"author-translations": ["en"]` in song.json — the site marks it as the author's translation instead of an automatic one. Translate automatically only the remaining UI languages.

For every UI language the song is not sung in, write `<lang>.cho` with an automatic translation of the original lyrics (e.g. a ru song gets `en.cho` and `pt.cho`):
- singable where possible (see CLAUDE.md → Lyrics translations): line by line, the same syllable count (±1) and stresses on the same beats as the original, so it fits the melody; keep the style, imagery and register; rhymes only where natural; meaning wins over form when they conflict
- same sections and line breaks (`{start_of_chorus}` / `{chorus}` as in the original); repeated lines translated identically
- lyrics only: **no chords, no `{key}`, no `{capo}`** — the build rejects chords in a translation
- header: `{title}` in that language, `{lyricist}`, `{composer}` in their Latin spelling
- Portuguese is European Portuguese (pt-PT)
- the site marks these as automatic translations, only to convey the meaning; report them as machine-translated

## 4. Converting chords-over-lyrics text

- Place each chord **before the syllable where it changes**: the column of the chord in a monospaced source points at that syllable; move a chord that lands on a vowel back to the consonant starting its syllable (`о[C]бещает`, `у[E7]ходит`)
- A chord past the end of the line goes after it with a space: `…небес, [C]`
- Chord-only lines (intro/outro): `[Am] [Em] [Em] [Am]`
- Verses without chords in the source stay without chords — do not invent them
- If a later verse repeats the chords of an earlier one, map them by **syllable index**, and say so in the summary
- **H means B natural** — the author writes German notation: `H7` = B7, `Am/H` = Am with a B bass. Keep `H` exactly as written, do not convert it to `B`. In a song that uses H, a plain `B` means B♭ (ask if a `B` chord appears and the intent is unclear)
- Write position hints without a space: `G (III)` → `G(III)`
- Slash chords missing from chords-db (e.g. `Am/H`) need a `{define: Am/H base-fret 1 frets x 2 2 2 1 0 fingers 0 2 3 4 1 0}`
- Chord names are Latin only: check for Cyrillic `С`/`А`/`Е` in chords and Latin letters inside Cyrillic words (`Новыx`) — fix and report them
- Use `{start_of_chorus}` once and `{chorus}` for repeats
- `G(III)`-style position hints select a barre at that fret

## 5. Validate and preview

```
python build.py                  # validates, regenerates index.html, README.md, robots.txt, llms.txt, sitemap.xml
python -m unittest discover tests
python show_site.py              # check /ru/, /en/, /pt/ song pages, chords toggle, PDF link
```
Fix every `✗` and `!` (a `!` means a chord has no fingering: add `{define: …}`).

## 6. Commit

Commit sources + `index.html` + `README.md` + `robots.txt` / `llms.txt` / `sitemap.xml` with the backlog status updated; push. Report: machine-translated fields, chord placements you inferred, facts you assumed (date day, song languages).
