// Album metadata for "Тишина / The Silence"

#let album = (
  id:               "the-silence",
  default_language: "ru",
  author:      "Сергей Рыков",
  album:       "Тишина",
  album-year:  "2026",
  cover-image: "cover.png",  
  songs: (
    "beregi-sebya",
  ),
  
  // Per-language overrides for album and author display names
  lang: (
    ru: (
      author: "Рыков Сергей",
      album:  "Тишина",
    ),
    en: (
      author: "Sergio Rykov",
      album:  "The Silence",
    ),
  ),
)
