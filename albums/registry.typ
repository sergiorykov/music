// Central album registry — maps album-id string to album metadata.
// template.typ imports this to resolve album data by id.
// When adding a new album: add one import line and one registry entry.

#import "Кукла Маша/album.typ": album as _kukla_masha
#import "Тишина/album.typ":     album as _tishina

#let registry = (
  "kukla-masha": _kukla_masha,
  "the-silence": _tishina,
)
