# Backlog

Work plan. Update status as steps land; each step is committed and pushed (see CLAUDE.md → Committing).
Terms (UI language, Metadata language, Song language, Lyrics translation) are defined in [CONTEXT.md](../CONTEXT.md).

Status: `[ ]` todo · `[~]` in progress · `[x]` done

## Now: song page tweaks

- [x] **Glossary: Lyrics translation** — «Take Care of Yourself» is a translation; the Song language of «Береги себя» is ru only. Record the term in CONTEXT.md.
- [x] **Song page: back to album** — link "Year · Album title" above the song title. Until album pages exist it opens the home page filtered to that album (`index.html?album=<id>`); later it points to the album page.
- [~] **Song page: lyrics switch in the toolbar** — folded into "Song pages" below (the page is rebuilt for UI languages anyway).

## Autonomous run (2026-09-26) — execution order

1. [x] `i18n.json`: all UI strings, key → {ru, en, pt}; auto-translate en + pt; completeness test.
2. [x] Metadata model: song.json / album.json get title + slug (+ credits) per metadata language, song languages, original lyrics, ISO date; auto-translate current songs and albums; validation.
3. [x] Song pages `/<ui>/songs/<yyyy>-<mm>-<slug>/`: lyrics switch (original / translations) in the toolbar, default = UI language; "with chords" toggle (default off); chord mode = chords, fingering panel, capo + transposition; UI language switch; back to album page. Print pages for PDF.
4. [x] Album pages `/<ui>/albums/<slug>/`.
5. [x] Home pages `/<ui>/` + root redirect by browser language; "sung in" filter; GitHub link → /music; footer stack.
6. [ ] README, CI, CLAUDE.md, show_site/publish updated.
7. [ ] Skills: import a song, create an album.

## Next

- [ ] **Plan the work with `/grill-with-docs`** — interview over all items below: design tree, glossary in CONTEXT.md, ADRs for hard-to-reverse choices (URL scheme, localization format). Output: agreed plan and order of work.

## Localization

- [ ] **UI language switch `/ru` `/en` `/pt`** — all UI strings in one JSON at repo root: key → `{ru, en, pt}`. Auto-translate existing ru strings to en + pt (reviewed later by the author). Replaces the labels in `settings.json`.
- [ ] **Song metadata in every metadata language** — title + slug in ru, en, pt; the UI shows the ones for the current UI language. Auto-translate for current songs.
- [ ] **Album metadata in every metadata language** — title + slug in ru, en, pt. Auto-translate for current albums (Кукла Маша, Тишина).
- [ ] **Song languages + home filter** — each song lists the song languages it is sung in (ru; mixed ru+en; separate versions; more may come). Lyrics translations (e.g. «Take Care of Yourself») are not song languages and must not appear under a song-language filter. The home page filter is "the language I sing in": label it so visitors don't confuse it with the UI language. Song import must capture it.

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
