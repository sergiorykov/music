# URL scheme: UI language first, dated song slugs

Public URLs are `/<ui>/` (home), `/<ui>/albums/<album-slug>/` and `/<ui>/songs/<year>-<month>-<song-slug>/`, where `<ui>` is the UI language and every slug comes from the metadata in that language (so `/pt/albums/o-silencio/`, `/ru/albums/tishina/`). Songs carry `<year>-<month>-` so that two songs may share a title slug and URLs sort chronologically; song folders use the same pattern with the en slug (`songs/2024-03-take-care-of-yourself/`), which the build enforces. The site root only redirects to a UI language (saved choice, then browser languages, then en). Once shared, these URLs are hard to change, so slugs should be treated as permanent.

## Considered Options

- One page per song with a client-side language switch: simpler build, but no language-specific URLs to share or index.
- `/songs/<slug>/?lang=pt`: keeps one slug per song, but slugs could not be localized.
