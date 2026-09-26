---
name: new-album
description: Create a new album in this songbook — album.json with title, slug and author in every UI language, year and cover. Use when the user wants to add or create an album.
---

# Create an album

Read `CONTEXT.md` first; album titles and slugs are **Metadata language** data, one per UI language in `settings.json` (`ru`, `en`, `pt`).

## 1. Gather facts (ask only for what you cannot find)

- Title (in the author's language), year, cover image (square PNG)
- Which existing songs belong to it (their `song.json` gets `"album-id"`)

Plan first: add the steps to `docs/backlog.md`, commit and push (CLAUDE.md → Committing).

## 2. Files

`albums/<year>-<en slug>/album.json` + `cover.png` (e.g. `albums/2026-the-silence/`; the build rejects any other folder name):
```json
{
  "id": "the-silence",
  "year": "2026",
  "cover-image": "cover.png",
  "metadata": {
    "ru": { "title": "Тишина",      "slug": "tishina",     "author": "Сергей Рыков" },
    "en": { "title": "The Silence", "slug": "the-silence", "author": "Sergio Rykov" },
    "pt": { "title": "O Silêncio",  "slug": "o-silencio",  "author": "Sergio Rykov" }
  }
}
```
- `id`: ASCII, stable, referenced by songs as `album-id`; never change it after publishing
- Translate titles automatically (Portuguese = pt-PT) and report them as machine-translated
- Slugs: lowercase `a-z0-9-`, transliterate Cyrillic, unique per language; they become `/<ui>/albums/<slug>/` URLs, so treat them as permanent (docs/adr/0001-url-scheme.md)
- Nothing else changes: songs reference the album by `album-id`; the album page lists them by date

## 3. Validate, preview, commit

```
python build.py
python -m unittest discover tests
python show_site.py     # /ru/albums/<slug>/, /en/…, /pt/…
```
Commit `albums/<year>-<en slug>/` (+ any `song.json` updated with `album-id`) with `index.html`, `README.md` and the backlog status; push.
