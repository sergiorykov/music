// Global settings shared across all songs

#let author = "Sergio Rykov"
#let author-photo = "images/author-photo.jpg"  // square author photo
#let album = "Тишина"
#let album-year = "2026"

// Fonts and colours
#let main-font = "Segoe UI"
#let chord-color = blue.darken(30%)  // chord highlight colour
#let text-color = black
#let bg-color = white

// Sizes
#let cover-size = 2.5cm        // song cover image (square)
#let author-icon-size = 0.8cm  // author avatar in header

// Per-language overrides — any key here shadows the global default in template.typ
// Supported keys: lyrics-label, music-label, author (default music author name)
#let lang-settings = (
  ru: (
    lyrics-label: "Стихи",
    music-label:  "Музыка",
    author:       "Сергей Рыков",
  ),
  en: (
    lyrics-label: "Lyrics",
    music-label:  "Music",
    album:        "The Silence",
  ),
)
