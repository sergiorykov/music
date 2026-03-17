// Per-language configuration for "Береги себя".
// Keys in `about` are shared; each entry in `languages` overrides individual keys.
// Usage in lang files: #show: song-template.with(..variant("ru"))

#let about = (
  song-id:          "beregi-sebya",
  album-id:         "the-silence",
  default_language: "ru",
  cover-image:      "/songs/Береги себя/cover.png",
  capo:             "4",
  soundcloud:       "https://soundcloud.com/sergiorykov/beregi-sebya",
  soundcloud-embed: "https://w.soundcloud.com/player/?url=https%3A//api.soundcloud.com/tracks/soundcloud%253Atracks%253A1781981829&color=%23ff5500&auto_play=false&hide_related=false&show_comments=true&show_user=true&show_reposts=false&show_teaser=true",
  music-author-url: "https://soundcloud.com/sergiorykov/",
  music-date:       "22.03.2024",
)

#let languages = (
  ru: (
    title:            "Береги себя",
    music-author:     "Сергей Рыков",
    lyrics-author:    "Таня Пелиховская",
    lyrics-author-url: "https://www.chitalnya.ru/users/Einsamer2/info.php",
    lyrics-date:      none,
    lyrics-sources: (
      ("текст fb", "https://www.facebook.com/story.php/?story_fbid=317692863917323&id=100070298352633&paipv=0&eav=AfZ-taNTFgh0iZEcLmdUgs-NpnB_-6hxpCRCUIM1Phy_2jGI49Kuq2VZfME3qsrILAw&_rdr"),
      ("текст tg", "https://t.me/klub_ratnikov/3006"),
    ),
  ),
  en: (
    title:            "Take Care of Yourself",
    music-author:     "Sergey Rykov",
    lyrics-author:    "Tanya Pelikhovskaya",
    lyrics-author-url: "https://www.chitalnya.ru/users/Einsamer2/info.php",
    lyrics-date:      none,
    lyrics-sources:   (),
  ),
)

// Merge about + language overrides; inject language code from key name
#let variant(lang) = {
  let result = about
  result.insert("language", lang)
  for (k, v) in languages.at(lang) { result.insert(k, v) }
  result
}
