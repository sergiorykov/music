// Global settings shared across all songs

#let author-photo = "images/author-photo.jpg"  // square author photo

#import "albums/Тишина/album.typ": album as _a
#let author     = _a.author
#let album      = _a.album
#let album-year = _a.album-year

// Fonts and colours
#let main-font = "Segoe UI"
#let chord-color = blue.darken(30%)  // chord highlight colour
#let text-color = black
#let bg-color = white

// Sizes
#let cover-size = 2.5cm        // song cover image (square)
#let author-icon-size = 0.8cm  // author avatar in header

// Per-language overrides — any key here shadows the global default in template.typ
// Supported keys: lyrics-label, music-label, author, album
#let lang-settings = (
  ru: (
    lyrics-label: "Стихи",
    music-label:  "Музыка",
  ),
  en: (
    lyrics-label: "Lyrics",
    music-label:  "Music",
    author:       _a.lang.at("en").at("author"),
    album:        _a.lang.at("en").at("album"),
  ),
)
