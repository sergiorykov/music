// template.typ
#import "settings.typ": *

// Подсвечиваем аккорды: латинские A-G с модификаторами (русские тексты — кириллица, не пересекается)
#let chord-show = it => text(weight: "bold", fill: chord-color, font: "Courier New", size: 0.9em, it)

#let song-template(
  title: "",
  cover-image: none,
  capo: none,
  soundcloud: none,
  body,
) = {
  set page(
    paper: "a5",
    margin: (x: 1.2cm, y: 1cm),
  )

  set text(font: main-font, size: 11pt, fill: text-color)
  set par(leading: 0.55em, spacing: 1em)

  // Подсветка аккордов через show rule (работает по всему документу)
  show regex("\\b[A-G][#b]?m?(maj7|min7|7|dim7|dim|aug|sus4|sus2|add9)?(/[A-G][#b]?)?\\b"): chord-show

  // ── Шапка ──────────────────────────────────────────────────────
  block(
    width: 100%,
    inset: (bottom: 0.4cm),
    stroke: (bottom: 0.5pt + luma(200)),
  )[
    #grid(
      columns: (auto, 1fr, auto),
      gutter: 0.4cm,
      align: horizon,
      image(author-photo, width: author-icon-size, height: author-icon-size, fit: "cover"),
      [
        #text(weight: "bold", author) \
        #text(size: 9pt, style: "italic", fill: luma(130))[#album · #album-year]
      ],
      text(size: 8pt, fill: luma(150), datetime.today().display("[day].[month].[year]")),
    )
  ]

  v(0.3cm)

  // ── Заголовок + обложка ────────────────────────────────────────
  grid(
    columns: (cover-size, 1fr),
    gutter: 0.5cm,
    align: horizon,
    image(cover-image, width: cover-size, height: cover-size, fit: "cover"),
    block(inset: (top: 0pt))[
      #text(size: 17pt, weight: "bold", title)
      #if capo != none [
        \ #text(size: 9pt, fill: luma(110), style: "italic")[Capo #capo]
      ]
    ],
  )

  v(0.5cm)

  // ── Текст песни ────────────────────────────────────────────────
  body

  // ── Подвал ─────────────────────────────────────────────────────
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
    #text(size: 8pt, fill: luma(150))[#album · #album-year]
  ]
}
