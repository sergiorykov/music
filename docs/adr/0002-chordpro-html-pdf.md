# ChordPro sources, HTML pages, PDF printed from HTML

Songs are written in ChordPro (a portable, standard format) and rendered by our own Python build into HTML; the PDF is the same HTML printed by headless Chromium (Playwright) with print CSS, instead of a separate Typst layout. This keeps one layout for web and print and all music logic (transposition, sharps/flats, fingerings) in Python at build time; the browser only swaps precomputed values. Build outputs (`/<ui>/`, `print/`, `pdf/`) are generated in CI and not committed.

## Considered Options

- Typst for PDF (previous setup): better typography, but a second layout to maintain and no interactive web view.
- ChordSheetJS in the browser: fuller ChordPro coverage, but splits logic between JS and Python and adds a Node dependency.
