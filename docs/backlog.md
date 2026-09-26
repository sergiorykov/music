# Backlog

Work plan. Update status as steps land; each step is committed and pushed (see CLAUDE.md → Committing).
Terms (UI language, Metadata language, Song language) are defined in [CONTEXT.md](../CONTEXT.md).

Status: `[ ]` todo · `[~]` in progress · `[x]` done

## Next

- [ ] **Plan the work with `/grill-with-docs`** — interview over all items below: design tree, glossary in CONTEXT.md, ADRs for hard-to-reverse choices (URL scheme, localization format). Output: agreed plan and order of work.

## Localization

- [ ] **UI language switch `/ru` `/en` `/pt`** — all UI strings in one JSON at repo root: key → `{ru, en, pt}`. Auto-translate existing ru strings to en + pt (reviewed later by the author). Replaces the labels in `settings.json`.
- [ ] **Song metadata in every metadata language** — title + slug in ru, en, pt; the UI shows the ones for the current UI language. Auto-translate for current songs.
- [ ] **Album metadata in every metadata language** — title + slug in ru, en, pt. Auto-translate for current albums (Кукла Маша, Тишина).
- [ ] **Song languages + home filter** — each song lists the song languages it is sung in (ru; mixed ru+en; separate versions; more may come). The home page filter is "the language I sing in": label it so visitors don't confuse it with the UI language. Song import must capture it.

## Pages

- [ ] **Album pages** — `/<ui-lang>/albums/<album-slug>`, e.g. `/pt/albums/<pt slug of Тишина>`.
- [ ] **Song pages** — `/<ui-lang>/songs/<year>-<month>-<song-slug>`.
  - SoundCloud widget + lyrics with authors, as now; default view is lyrics only.
  - UI language switch en / pt / ru.
  - Localized "with chords" toggle → chord mode: chords above lines, fingering panel on the right, capo info + transposition before the song.

## Site fixes

- [ ] **GitHub link** → `https://github.com/sergiorykov/music` (currently `/songs`).
- [ ] **Footer tech list** — Typst already replaced by ChordPro (PR #2); list the actual stack (ChordPro, Python, Playwright, chords-db?) — confirm which to show.

## Skills (after localization)

- [ ] **Skill: import a song** — song.json with metadata in all metadata languages + slugs, song languages, `.cho` per version, cover, validation via `build.py`.
- [ ] **Skill: create an album** — album.json with titles + slugs in ru / en / pt, cover, song list.
