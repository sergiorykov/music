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
An automatic translation of the original lyrics into another language so listeners can understand the meaning. Lyrics only: never sung, no chords, adds no Song language.
_Avoid_: version, English song, human translation

**Language version**:
A separate Song that is the author's own recording of another Song in a different song language (its own folder, lyrics and SoundCloud track). Language versions link to each other.
_Avoid_: translation, variant, cover
