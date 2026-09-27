# Songbook

Indie songs published as chord sheets and lyrics for listeners and guitarists, navigable in several languages.

## Languages

**UI language**:
The language the site speaks to the visitor in: labels, buttons, navigation. Chosen by the visitor.
_Avoid_: site language, locale, interface language

**Metadata language**:
The language of the names that describe a Song or an Album (title, slug) so a visitor can recognise and navigate them. Shown in the visitor's UI language.
_Avoid_: translation, title language

**Song language**:
A language a Song is sung in. A Song is sung in one language or in a mix of languages; for a mix, one of them is the **primary song language**.
_Avoid_: lyrics language, language (unqualified)

**Original lyrics**:
The lyrics exactly as sung, with chords, in the Song's song language(s); named after the primary song language.
_Avoid_: source text

**Lyrics translation**:
A translation of the original lyrics into another language so listeners can understand the meaning; it keeps the style and, where possible, the rhythm of the original so it could be sung to the melody. Automatic by default; the author's own translation is marked as such (`author-translations` in song.json). Lyrics only: not performed by the author, no chords, adds no Song language.
_Avoid_: version, English song, human translation

**Language version**:
A separate Song that is the author's own recording of another Song in a different song language (its own folder, lyrics and SoundCloud track). Language versions link to each other.
_Avoid_: translation, variant, cover
