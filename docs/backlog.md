# Backlog

Work plan. Update status as steps land; each step is committed and pushed (see CLAUDE.md → Committing).
Terms (UI language, Metadata language, Song language, Lyrics translation) are defined in [CONTEXT.md](../CONTEXT.md).

Status: `[ ]` todo · `[~]` in progress · `[x]` done

## Now: song page tweaks

- [x] **Glossary: Lyrics translation** — «Take Care of Yourself» is a translation; the Song language of «Береги себя» is ru only. Record the term in CONTEXT.md.
- [x] **Song page: back to album** — link "Year · Album title" above the song title. Until album pages exist it opens the home page filtered to that album (`index.html?album=<id>`); later it points to the album page.
- [x] **Song page: lyrics switch in the toolbar** — folded into "Song pages" below (the page is rebuilt for UI languages anyway).

## Autonomous run (2026-09-26) — execution order

1. [x] `i18n.json`: all UI strings, key → {ru, en, pt}; auto-translate en + pt; completeness test.
2. [x] Metadata model: song.json / album.json get title + slug (+ credits) per metadata language, song languages, original lyrics, ISO date; auto-translate current songs and albums; validation.
3. [x] Song pages `/<ui>/songs/<yyyy>-<mm>-<slug>/`: lyrics switch (original / translations) in the toolbar, default = UI language; "with chords" toggle (default off); chord mode = chords, fingering panel, capo + transposition; UI language switch; back to album page. Print pages for PDF.
4. [x] Album pages `/<ui>/albums/<slug>/`.
5. [x] Home pages `/<ui>/` + root redirect by browser language; "sung in" filter; GitHub link → /music; footer stack.
6. [x] README, CI, CLAUDE.md, show_site/publish updated.
7. [x] Skills: import a song, create an album.

## Now: links, PDF naming, list buttons, songbook (2026-09-26)

1. [x] **Localized lyrics sources** — move lyrics source links from `.cho` `{meta: lyrics_source}` to `song.json` `lyrics-sources: [{url, label: {ru, en, pt}}]`; credits show the label in the UI language.
2. [x] **Meaningful PDF names** — `pdf/<author>-<song id>-<lyrics>.pdf`, e.g. `sergio-rykov-beregi-sebya-ru.pdf` (was `pdf/<song-id>/<lyrics>.pdf`); songbook `pdf/sergio-rykov-songs-<ui>.pdf`. Author slug in settings.json.
3. [x] **PDF button names its lyrics language** — `PDF EN` / `PDF RU` on the song page (follows the lyrics switch) and in lists.
4. [x] **List buttons: lyrics · chords · PDF XX** — on home and album pages: open the song page in lyrics mode, in chord mode (`#chords`), and the PDF of the lyrics shown for this UI language.
5. [x] **Footer stack** — drop Python and Playwright (Claude Code, ChordPro, chords-db remain).
6. [x] **Songbook PDF** — one PDF with all songs (sung lyrics + chords + fingerings), title page, contents with links, page numbers, per UI language: `pdf/sergio-rykov-songs-<ui>.pdf`; "⬇ Songbook PDF" button on the home page.

## Now: import «Листья оливы» (2026-09-26)

1. [x] **Cover by URL** — `cover-image` may be an absolute URL (SoundCloud artwork); song pages, print pages and PDF use it as is.
2. [x] **Song files** — `songs/2024-01-olive-leaves/`: song.json (ru/en/pt metadata, sung in ru, SoundCloud embed from the track permalink, cover from SoundCloud), `ru.cho` (`G (III)` → `G(III)`, key Em, capo 2, `{define: Am/H}`).
2a. [x] **German notation** — keep `H` as written (H = B natural, B = B♭ in such songs); the chord model, transposition and naming support it; rule added to CLAUDE.md and the import-song skill.
3. [x] **Build, tests, preview**; regenerate index.html / README.md.

## Now: import-song skill reads SoundCloud (2026-09-26)

1. [x] **Skill: SoundCloud as a source** — given a track URL, the skill pulls title, description (credits, date, capo, lyrics with chords), artwork (cover) and builds the widget URL itself; network fallbacks documented.

## Now: language versions, auto-translations, PDFs, landscape songbook (2026-09-26)

Decisions (author, 2026-09-26): a song sung in [ru, en] is one song with a primary song language (its file name and default); a song recorded in two languages is two songs (two folders, two SoundCloud links) cross-linked as author's language versions; every lyrics translation is an automatic translation, lyrics only; all current songs: original ru, en/pt auto-translated; songbook = A4 landscape, two A5 pages per sheet.

1. [x] **Model + glossary** — CONTEXT.md: Language version, Lyrics translation = automatic; song.json `language-versions: [song id]` (validated, reciprocal); original lyrics file = primary song language (must be in song-languages); lyrics translations carry no chords (build error otherwise); `{key}` required only in the original.
2. [x] **Auto-translations** — lyrics-only en/pt for every song (Береги себя: strip chords from en, add pt; Кукла Маша and Листья оливы: en + pt).
2b. [x] **Portuguese = pt-PT** (author lives in Lisbon) — rewrite pt lyrics translations, UI strings and pt titles in European Portuguese; rule in CLAUDE.md and skills.
3. [x] **Song page** — lyrics switch: original (`ru`, or `ru/en`) with chords | translations with a disabled "lyrics only" button and a clear "automatic translation, for meaning" note; "▶ SoundCloud" toggle after "with chords" shows the widget before the lyrics (on by default); link to the author's language version.
4. [x] **PDFs** — per song: chords PDF of the original (`…-chords-<lang>.pdf`) and lyrics-only PDF per UI language (`…-lyrics-<ui>.pdf`); both carry links to SoundCloud and to the song page in that language; song page shows "PDF chords RU" + "PDF lyrics <UI>".
5. [x] **Songbook** — originals with chords + SoundCloud and song links; A4 landscape, two A5 pages per sheet; a song takes one or two halves of one sheet, never split across sheets (right half may stay empty), font shrinks if longer than two halves.
5b. [x] **Album folders** — `albums/<year>-<en slug>/` (e.g. `albums/2026-the-silence`), enforced by the build.
6. [x] **Docs, skills, tests.**

## Now: song page header and PDF polish (2026-09-26)

1. [x] **PDF: capo in bold** and a thin divider between the header and the capo/key line.
2. [x] **SoundCloud widget shows on load** — the player iframe loads eagerly (no lazy loading).
3. [x] **PDF buttons in the header** — a right-hand column next to the title, stacked, equal width; no longer wrapping the toolbar.
4. [x] **SoundCloud button pushed to the right** of the toolbar.

## Now: import «Луч на стене» (2026-09-26)

1. [x] **Song files** — `songs/2024-03-sunbeam-on-the-wall/`: `ru.cho` (spoken intro poem, verses A = CHORDS_1 and B = CHORDS_2 patterns, chorus «живо», interludes, outro), `song.json` (ru/en/pt metadata, SoundCloud, cover from SoundCloud).
2. [x] **Automatic translations** — `en.cho`, `pt.cho` (pt-PT), lyrics only.
3. [x] **Build, tests, preview.**

## Now: singable translations rule, three-column songbook sheets (2026-09-26)

1. [x] **Rule: singable lyrics translations** — keep the style and imagery, follow the rhythm line by line (syllable count and stresses) so the translation fits the melody; meaning first when they conflict. In CLAUDE.md and the import-song skill.
2. [x] **Songbook: three columns** — a song too long for two halves gets its sheet split into three columns; scale down only if three columns are not enough.

## Now: CI warnings (2026-09-26)

1. [x] **Node 24 actions** — checkout v7, setup-python v7, configure-pages v6, upload-pages-artifact v5 (uses upload-artifact v7), deploy-pages v5 (all `node24`, checked in their action.yml).
2. [x] **Pin the runner** — `ubuntu-24.04` instead of `ubuntu-latest`, so the switch to Ubuntu 26 (from 2026-10-19) is a deliberate upgrade (Playwright system deps), not a surprise.

## Now: original-language tags in song lists (2026-09-26)

1. [x] **«original RU» tags** — in the home and album song lists replace «original: <title in the song language>» with «original» + one tag per song language (`RU`, or `RU` `EN`): readable for visitors who don't read Cyrillic.

## Now: list buttons open song pages in a new tab (2026-09-26)

1. [x] **lyrics / chords in a new tab** — like PDF and SoundCloud, so the list stays open.

## Now: SoundCloud widget loads with the song page (2026-09-26)

1. [x] **Widget in the page, not behind the button** — iframe in the initial HTML, visible, standard 166 px height; embeds use the track-id form (`api.soundcloud.com/tracks/<id>`) the widget itself redirects to; the SoundCloud button only hides / shows it; import skill stores the track-id form.

## Now: album link, list lyrics, 13 new songs (2026-09-27)

1. [x] **Album link under «← all songs»** — song page top nav: `← <year> · <album title>` in the UI language, same style, right under the all-songs link.
2. [x] **List lyrics like the song page** — home and album pages: the expanded song shows lyrics styled as on the song page (sections, chorus, comments), with the automatic-translation note; credits stay as they are.
3. [x] **Albums by year; author translations** — songs from 2024 on → «Тишина», older → «Кукла Маша» (incl. «Листья оливы», «Луч на стене»); a lyrics translation made by the author (Пополам → «Never to last») is marked as the author's, not automatic.
4. [x] **Import 13 songs** from SoundCloud / the author's text: Пополам, Я и ты, Дай мне силу, Песня Мисси, Юности цвет, Прости меня, Горы-тропы, Доверяй, Радости свет, Заповедь поэта, Солнышко, Вестник небес, Отпуск (no SoundCloud yet). Chords listed per line are placed inside the line by best guess — the author fixes them by hand.
5. [x] **Import «Солнце внутри», «Гордость»** — no SoundCloud yet, album «Тишина»; «Шаг веры» waits for its date; «Отпуск» is already in step 4.
6. [x] **Import «Шаг веры»** (05.12.2025, «Тишина», no SoundCloud yet).
7. [x] **SEO** — localized titles («Сергей Рыков — инди-музыка»), meta description, canonical + hreflang alternates, Open Graph, JSON-LD (Person, MusicAlbum, MusicComposition), `sitemap.xml`.
8. [x] **AEO** — author bio in every UI language (settings.json), `llms.txt` for AI agents; `robots.txt` allowing search and AI crawlers, generated at the site root (works as is on a custom domain; on github.io the author copies it to the `sergiorykov.github.io` repo).
9. [x] **Bio: Lisbon; SEO setup guide** — author bio says he lives in Lisbon; `docs/seo-setup.md`: Google Search Console, Bing Webmaster Tools, Wikidata, copying robots.txt / llms.txt to the domain root; settings.json `verification` (search console meta tags) and `links.wikidata` (JSON-LD sameAs).
10. [x] **Cache-busting for assets** — CSS/JS links carry `?v=<content hash>`, so browsers never pair new pages with stale styles.
11. [x] **robots.txt, llms.txt, sitemap.xml committed** — generated by build.py and committed at the repo root like index.html; CI checks they are up to date.
12. [x] **Skills: every regenerated file named explicitly** — import-song / new-album list what `build.py` regenerates and what to commit: index.html, README.md, sitemap.xml, llms.txt, robots.txt.
13. [x] **Song lists without the PDF button** — lyrics, chords and the SoundCloud button only.
14. [x] **SoundCloud button variants** — demo page; the author picked D: grey outline circle, 26 px, SoundCloud orange on hover.
15. [x] **Song PDFs in the songbook layout** — chords and lyrics PDFs: A4 landscape, exactly as the song's sheet in the songbook.

## Now: web songbook (2026-09-27)

For a tablet: chords and lyrics of a song on one screen.

1. [x] **Page `/<ui>/songbook/`** — left: collapsible menu, songs grouped by album (album: `year · title`, collapsible; song: `yyyy-mm · title`); right: the selected song across the full width in landscape like the PDF sheet — header (cover, title, lyricist / composer names, date, capo / key, no links), chord diagrams, lyrics with chords in 2 columns, 3 if long, smaller if still too long; one column on narrow screens. The menu hides to free the width; `#song` in the URL; ← → keys for the previous / next song.
2. [x] **Home: «Songbook» button** under «Songbook PDF»; sitemap + SEO head for the new page.
3. [x] **Home: songbook buttons in one row** above the songs heading and its filter: «Songbook» then «Songbook PDF».

## Now: about page (2026-09-27)

1. [x] **Page `/<ui>/about/`** — photo (webp, resized), the author bio from settings.json, a SoundCloud link; the photo and the name on the home page link to it; sitemap + SEO head (Person). Photo: the one the author sent (600×770 webp).
2. [x] **New photo in the home avatar** — `images/author-avatar.webp` (256 px square crop of the new photo) replaces `author-photo.jpg` everywhere it is used: home, songbook PDF title, Open Graph / JSON-LD.

## Now: light / dark theme (2026-09-27)

1. [ ] **Theme switch on every page** — a ☀ / ☾ button next to the UI language switch; light palette for home, album, about, song and web songbook pages (screen only — print and PDFs keep their own palette); the choice is saved in localStorage; with no saved choice the system setting (prefers-color-scheme) decides; applied in `<head>` before paint, so no flash.

## Next

- [ ] **Plan the work with `/grill-with-docs`** — interview over all items below: design tree, glossary in CONTEXT.md, ADRs for hard-to-reverse choices (URL scheme, localization format). Output: agreed plan and order of work.

## Localization

- [x] **UI language switch `/ru` `/en` `/pt`** — all UI strings in one JSON at repo root: key → `{ru, en, pt}`. Auto-translate existing ru strings to en + pt (reviewed later by the author). Replaces the labels in `settings.json`.
- [x] **Song metadata in every metadata language** — title + slug in ru, en, pt; the UI shows the ones for the current UI language. Auto-translate for current songs.
- [x] **Album metadata in every metadata language** — title + slug in ru, en, pt. Auto-translate for current albums (Кукла Маша, Тишина).
- [x] **Song languages + home filter** — each song lists the song languages it is sung in (ru; mixed ru+en; separate versions; more may come). Lyrics translations (e.g. «Take Care of Yourself») are not song languages and must not appear under a song-language filter. The home page filter is "the language I sing in": label it so visitors don't confuse it with the UI language. Song import must capture it.

## Pages

- [x] **Album pages** — `/<ui-lang>/albums/<album-slug>`, e.g. `/pt/albums/<pt slug of Тишина>`.
- [x] **Song pages** — `/<ui-lang>/songs/<year>-<month>-<song-slug>`.
  - SoundCloud widget + lyrics with authors, as now; default view is lyrics only.
  - UI language switch en / pt / ru.
  - Localized "with chords" toggle → chord mode: chords above lines, fingering panel on the right, capo info + transposition before the song.

## Site fixes

- [x] **GitHub link** → `https://github.com/sergiorykov/music` (currently `/songs`).
- [x] **Footer tech list** — Typst already replaced by ChordPro (PR #2); list the actual stack (ChordPro, Python, Playwright, chords-db?) — confirm which to show.

## Skills (after localization)

- [x] **Skill: import a song** — song.json with metadata in all metadata languages + slugs, song languages, `.cho` per version, cover, validation via `build.py`.
- [x] **Skill: create an album** — album.json with titles + slugs in ru / en / pt, cover, song list.
