// template.typ
#import "settings.typ": author, author-photo, album, album-year, main-font, chord-color, text-color, cover-size, author-icon-size, lang-settings

// Highlight chords: Latin A-G with modifiers (Cyrillic lyrics don't overlap)
#let chord-show = it => text(weight: "bold", fill: chord-color, font: "Courier New", size: 0.9em, it)

#let song-template(
  title: "",
  cover-image: none,
  capo: none,
  soundcloud: none,
  language: "en",
  default: false,   // used by update_songs.py; ignored here
  // Lyrics credits
  lyrics-author: none,
  lyrics-author-url: none,
  lyrics-date: none,
  lyrics-sources: (),   // array of ("Label", "url") pairs
  // Music credits
  music-author: none,   // if none, resolved from lang-settings or global author
  music-author-url: none,
  music-date: none,
  body,
) = {
  // Resolve per-language overrides from settings
  let ls             = lang-settings.at(language, default: (:))
  let lyrics-label   = ls.at("lyrics-label", default: "Lyrics")
  let music-label    = ls.at("music-label",  default: "Music")
  let eff-music-author = if music-author != none { music-author } else {
    ls.at("author", default: author)
  }
  let eff-album = ls.at("album", default: album)

  set page(
    paper: "a5",
    margin: (x: 1.2cm, y: 1cm),
  )

  set text(font: main-font, size: 11pt, fill: text-color, lang: language)
  set par(leading: 0.55em, spacing: 1em)

  // Apply chord highlighting via show rule (document-wide)
  show regex("\\b[A-G][#b]?m?(maj7|min7|7|dim7|dim|aug|sus4|sus2|add9)?(/[A-G][#b]?)?\\b"): chord-show

  // ── Header ──────────────────────────────────────────────────────
  block(
    width: 100%,
    inset: (bottom: 0.4cm),
    stroke: (bottom: 0.5pt + luma(200)),
  )[
    #grid(
      columns: (auto, 1fr, auto),
      gutter: 0.4cm,
      align: horizon,
      box(width: author-icon-size, height: author-icon-size, radius: 50%, clip: true,
        image(author-photo, width: author-icon-size, height: author-icon-size, fit: "cover")),
      [
        #text(weight: "bold", author) \
        #text(size: 9pt, style: "italic", fill: luma(130))[#eff-album · #album-year]
      ],
      [],
    )
  ]

  v(0.3cm)

  // ── Title + cover + credits ─────────────────────────────────────
  grid(
    columns: (cover-size, 1fr),
    gutter: 0.5cm,
    align: horizon,
    image(cover-image, width: cover-size, height: cover-size, fit: "cover"),
    block(inset: (top: 0pt))[
      #text(size: 17pt, weight: "bold", title)
      #v(0.1cm)
      #set text(size: 8pt, fill: luma(130), style: "italic")
      #if lyrics-author != none [
        #lyrics-label: #if lyrics-author-url != none [
          #link(lyrics-author-url)[#lyrics-author]
        ] else [
          #lyrics-author
        ]#if lyrics-date != none [ · #lyrics-date]#for s in lyrics-sources [ · #link(s.at(1))[#s.at(0)]]
        \
      ]
      #music-label: #if music-author-url != none [
        #link(music-author-url)[#eff-music-author]
      ] else [
        #eff-music-author
      ]#if music-date != none [ · #music-date]
    ],
  )

  v(0.5cm)

  // ── Capo indicator ──────────────────────────────────────────────
  if capo != none {
    block(inset: (bottom: 0.3cm))[
      #text(size: 9pt, fill: luma(110), style: "italic")[Capo +#capo]
    ]
  }

  // ── Song body ───────────────────────────────────────────────────
  body

  // ── Footer ──────────────────────────────────────────────────────
  v(1fr)
  block(
    width: 100%,
    inset: (top: 0.3cm),
    stroke: (top: 0.5pt + luma(200)),
  )[
    #set align(center)
    #if soundcloud != none [
      #link(soundcloud)[
        #text(size: 8pt, fill: rgb("#ff5500"))[SoundCloud ↗]
      ]
      #h(0.5em)
      #text(size: 8pt, fill: luma(200))[·]
      #h(0.5em)
    ]
    #text(size: 8pt, fill: luma(150))[#eff-album · #album-year]
  ]
}
