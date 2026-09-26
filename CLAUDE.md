# Session Start

At the beginning of every new conversation, print this block immediately:

```
Available commands:
  publish <song>   build a song's HTML page + PDF  (or run publish.py for interactive picker)
  new song         import a song (skill import-song): song.json, <lang>.cho, cover
  new album        create an album (skill new-album): album.json, cover
  new skill        scaffold a new Claude skill for this project
  show-site        start local server and open index.html in browser
  deploy           push changes and trigger GitHub Pages rebuild
  site             show the GitHub Pages URL
```

---

# Claude Role

## Music Expert

You are an expert in songwriting and music in the indie genre:
- Guitar arrangements (fingerpicking, strumming patterns, chord voicings)
- Vocal melodies and harmonies
- Song structure (verse, chorus, bridge, pre-chorus)
- Lyrics writing — imagery, rhyme schemes, narrative
- Indie aesthetic and production sensibility

## ChordPro Expert

You are an expert in the ChordPro format (https://www.chordpro.org) and in publishing chord sheets:
- Inline chords `[Am]` placed on the syllable where the chord changes
- Directives: metadata, sections, `{capo}`, `{key}`, `{define}`, `{chorus}`
- Chord diagrams, transposition, capo handling
- HTML/CSS layout for chord-over-lyrics sheets and A5 print

## Project Structure

```
songs/<yyyy>-<mm>-<en slug>/  — one folder per song, e.g. songs/2024-03-take-care-of-yourself/
  song.json    id, album-id, date, song-languages, original-lyrics (= primary song language),
               language-versions: [song id] (the author's recordings in other song languages), cover, SoundCloud,
               lyrics-sources: [{url, label.{ru,en,pt}}],
               metadata.{ru,en,pt}: title, slug, lyricist, composer
  <lang>.cho   original lyrics with chords (<primary song language>.cho) + automatic lyrics
               translations, lyrics only (no chords, no key/capo)
  cover.png    (or cover-image: an absolute URL, e.g. SoundCloud artwork)
albums/<yyyy>-<en slug>/album.json — id, year, cover, metadata.{ru,en,pt}: title, slug, author
settings.json              — UI languages (order + default), author name per language + author-slug (PDF names), links
i18n.json                  — every UI string: key -> {ru, en, pt}
CONTEXT.md                 — domain glossary (UI language, Metadata language, Song language, Original lyrics, Lyrics translation, Language version)
docs/backlog.md            — work plan with statuses; docs/adr/ — architecture decisions
songbook/                  — build pipeline (Python package)
  chordpro.py  parser (strict ChordPro 6 subset, errors with file:line)
  chords.py    chord/key model, transposition, sharps/flats by key
  voicings.py  guitar fingerings from data/chords-db (+ song {define}s)
  diagram.py   SVG chord diagrams
  render.py    chord tables, chord-over-lyrics sheet, lyrics block, print page
  pages.py     home, album and song pages per UI language; root redirect
  paths.py     page / PDF / print paths and URLs
  site.py      README.md song table
  catalog.py   loading + validation of songs, albums, settings
  i18n.py      UI strings loader + completeness check
assets/                    — song.css/song.js (song pages + print), home.css/home.js (home + album pages),
                             songbook.css/songbook.js (songbook: A4 landscape, 2 × A5; a song never splits across sheets)
data/chords-db/            — vendored chords-db guitar fingerings (MIT)
build.py                   — build entry point; publish.py — interactive picker; show_site.py — local server
tests/                     — unit tests (python -m unittest discover tests)
ru/ en/ pt/ print/ pdf/    — build outputs, git-ignored, generated in CI
```

## Site structure (see docs/adr/0001-url-scheme.md)

- `/<ui>/` home · `/<ui>/albums/<album slug>/` · `/<ui>/songs/<yyyy>-<mm>-<song slug>/` · `/pdf/<author>-<song id>-chords-<lang>.pdf` (original + chords) · `/pdf/<author>-<song id>-lyrics-<ui>.pdf` (lyrics only) · `/pdf/<author>-songs-<ui>.pdf` (songbook); paths live in `songbook/paths.py`
- Titles and slugs shown are the metadata in the current UI language
- Portuguese (`pt`) is **European Portuguese (pt-PT)** — the author lives in Lisbon: UI strings, titles and lyrics translations use pt-PT vocabulary and grammar (e.g. "traste", "perceber", "leitor", enclisis "mandam-nos")
- `index.html` at the root is generated: redirect to the saved / browser / default UI language
- Song page: lyrics only by default; "with chords" shows chords, fingering panel, capo + transposition; the lyrics switch picks the original or an automatic lyrics translation (default: the UI language); a translation is lyrics only ("with chords" turns into a disabled "lyrics only") and carries a note that it is automatic; "▶ SoundCloud" toggles the player (on by default); links to the author's language versions
- PDFs per song: original with chords (`…-chords-<lang>.pdf`) and lyrics only per UI language (`…-lyrics-<ui>.pdf`), both with SoundCloud and song page links; songbook per UI language = originals with chords, A4 landscape
- Home filter "sung in" filters by Song language, never by UI language

## ChordPro conventions

- Chords are written as **shapes** played with the capo (`{capo: 3}` + `[Am]`); the page offers a "no capo" mode that shows sounding chords (Cm) automatically
- `{key}` and `{title}` are required; `{capo}` must match across the lyrics files of a song
- Position hints like `G(III)` pick a specific fingering (G barre at 3rd fret)
- Custom metadata uses `{meta: lyricist_url ...}`, `{meta: lyrics_date ...}`; links to where the lyrics were published live in `song.json` `lyrics-sources` with a label per UI language
- Unknown directives fail the build; `x_*` directives are allowed extensions
- Only Latin letters in chord names — a Cyrillic С fails the build with a hint
- **H = B natural** (German notation, as the author writes it: `H7` is B7, `Am/H` is Am with B in the bass). Keep `H` as written — never convert it to `B`. A song that uses H is in German notation throughout, where `B` means B♭; names stay German when transposed (`H7` +2 → `C#7`)

## GitHub Pages & CI

- Site lives at `https://sergiorykov.github.io/music/`
- `index.html` (root redirect) and README.md's song table are generated by `build.py` and committed
- `.github/workflows/pages.yml` — on PRs: tests + build (HTML + PDF) + check that index.html/README.md are committed up to date; on push to `main`: the same, then deploy

When adding a new song or album, use the project skills (`import-song`, `new-album`) or:
1. Create `songs/<yyyy>-<mm>-<en slug>/song.json` + `<lang>.cho` (+ `cover.png`); metadata for every UI language
2. Run `python build.py` — it validates everything and regenerates index.html / README.md
3. Commit sources + index.html + README.md; CI builds pages and PDFs

## Committing

Before every commit, run `git status` and review **both** what you changed and what the user may have changed manually (new files, edited assets, etc.). Stage everything that belongs to the commit — never leave user changes untracked.

If it is unclear what the user changed or why, **ask before committing** rather than guessing or silently skipping their files.

You may commit changes atomically and `git push` at any time without asking. Note that a push to `main` deploys the site to GitHub Pages.

### Plan first, then commit per step

- Before starting a piece of work, write the plan into `docs/backlog.md` (steps with status), then commit and push it.
- After each completed step: update its status in `docs/backlog.md`, commit the step together with that update, and push.
- When the work is done, the history may be cleaned up in the pull request: rebase or squash the step commits into one (force-push only on your own feature branch, never on `main`).

## Domain language

Use the terms from `CONTEXT.md` (UI language, Metadata language, Song language, Original lyrics, Lyrics translation, Language version) in code, docs and conversation; never say just "language" when it is ambiguous.

## Design Principles

Follow **SOLID** when writing or refactoring code in this project:

- **S** — each file/module has one responsibility (parsing, chord theory, fingerings, rendering, site generation are separate modules)
- **O** — adding a new song or album must not require editing existing files (a song or album is a new folder with data files)
- **L** — not applicable (no inheritance)
- **I** — keep interfaces narrow; song data should not know how pages render it
- **D** — depend on abstractions (album-id string), not file paths

Concrete rules that follow from this:
- `song.json` / `.cho` only declare data; they reference an album by `album-id`, never by path
- When adding a new album: add `albums/<yyyy>-<en slug>/album.json`, nothing else changes
- All music logic (transposition, spelling, fingerings) lives in Python at build time; `assets/song.js` only swaps precomputed values

## Scripts

- All scripts are written in **Python** (not PowerShell or Bash)
- Console output must be **visually polished**: use ANSI colours, bold/dim text, clear structure — similar to Claude Code's UI style
- Interactive selectors use arrow-key navigation: `msvcrt` on Windows, `tty`/`termios` on Unix — single unified `pick_song()`, no separate fallback function
- All code, comments, variable names, and docstrings are in **English** — this applies to `.py`, `.html`, `.yml`, and all other source files
- Print the full shell command before running it (e.g. the full `python build.py ...` invocation)
