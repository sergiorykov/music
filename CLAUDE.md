# Session Start

At the beginning of every new conversation, print this block immediately:

```
Available commands:
  publish <song>   build a song's HTML page + PDF  (or run publish.py for interactive picker)
  new song         create a new song: song.json, <lang>.cho, cover image slot
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
songs/<Song>/song.json     — data shared by all languages (song-id, album-id, default-language, cover, SoundCloud, music date)
songs/<Song>/<lang>.cho    — lyrics + chords in ChordPro, one file per language
songs/<Song>/cover.png     — cover art
albums/<Album>/album.json  — album metadata (per-language name/author overrides)
settings.json              — global settings and UI labels per language
songbook/                  — build pipeline (Python package)
  chordpro.py  parser (strict ChordPro 6 subset, errors with file:line)
  chords.py    chord/key model, transposition, sharps/flats by key
  voicings.py  guitar fingerings from data/chords-db (+ song {define}s)
  diagram.py   SVG chord diagrams
  render.py    song page HTML (capo modes, transposition, chord panel)
  site.py      generated blocks of index.html and README.md
  catalog.py   loading + validation of songs, albums, settings
assets/song.css, song.js   — song page styles (web + print) and interactions
data/chords-db/            — vendored chords-db guitar fingerings (MIT)
build.py                   — build entry point; publish.py — interactive picker
tests/                     — unit tests (python -m unittest discover tests)
web/ pdf/ pages/           — build outputs, git-ignored, generated in CI
```

## ChordPro conventions

- Chords are written as **shapes** played with the capo (`{capo: 3}` + `[Am]`); the page offers a "no capo" mode that shows sounding chords (Cm) automatically
- `{key}` and `{title}` are required; `{capo}` must match across languages of a song
- Position hints like `G(III)` pick a specific fingering (G barre at 3rd fret)
- Custom metadata uses `{meta: lyricist_url ...}`, `{meta: lyrics_date ...}`, `{meta: lyrics_source label | url}`
- Unknown directives fail the build; `x_*` directives are allowed extensions
- Only Latin letters in chord names — a Cyrillic С fails the build with a hint

## GitHub Pages & CI

- Site lives at `https://sergiorykov.github.io/music/`
- `index.html` at repo root is hand-written except the blocks between `<!-- songs:start/end -->`, `<!-- albums:start/end -->`, `<!-- album-cards:start/end -->` which `build.py` regenerates (same for README.md)
- `.github/workflows/pages.yml` — on PRs: tests + build + check that index.html/README.md are committed up to date; on push to `main`: the same, then deploy (HTML + PDF are built in CI, not committed)

When adding a new song:
1. Create `songs/<Title>/song.json` and `songs/<Title>/<lang>.cho`, add `cover.png`
2. Run `python build.py` — it validates sources and regenerates index.html / README.md
3. Commit sources + index.html + README.md; CI builds pages and PDFs

## Committing

Before every commit, run `git status` and review **both** what you changed and what the user may have changed manually (new files, edited assets, etc.). Stage everything that belongs to the commit — never leave user changes untracked.

If it is unclear what the user changed or why, **ask before committing** rather than guessing or silently skipping their files.

You may commit changes atomically and `git push` at any time without asking. Note that a push to `main` deploys the site to GitHub Pages.

## Design Principles

Follow **SOLID** when writing or refactoring code in this project:

- **S** — each file/module has one responsibility (parsing, chord theory, fingerings, rendering, site generation are separate modules)
- **O** — adding a new song or album must not require editing existing files (a song or album is a new folder with data files)
- **L** — not applicable (no inheritance)
- **I** — keep interfaces narrow; song data should not know how pages render it
- **D** — depend on abstractions (album-id string), not file paths

Concrete rules that follow from this:
- `song.json` / `.cho` only declare data; they reference an album by `album-id`, never by path
- When adding a new album: add `albums/<Album>/album.json`, nothing else changes
- All music logic (transposition, spelling, fingerings) lives in Python at build time; `assets/song.js` only swaps precomputed values

## Scripts

- All scripts are written in **Python** (not PowerShell or Bash)
- Console output must be **visually polished**: use ANSI colours, bold/dim text, clear structure — similar to Claude Code's UI style
- Interactive selectors use arrow-key navigation: `msvcrt` on Windows, `tty`/`termios` on Unix — single unified `pick_song()`, no separate fallback function
- All code, comments, variable names, and docstrings are in **English** — this applies to `.py`, `.html`, `.yml`, and all other source files
- Print the full shell command before running it (e.g. the full `python build.py ...` invocation)
