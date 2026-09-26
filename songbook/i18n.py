"""UI strings: i18n.json at the repo root maps key -> {ui_language: text}."""

from __future__ import annotations

import json
from functools import lru_cache
from html import escape

from .catalog import ROOT, CatalogError, load_settings

I18N_PATH = ROOT / "i18n.json"


@lru_cache(maxsize=1)
def strings() -> dict[str, dict[str, str]]:
    return json.loads(I18N_PATH.read_text(encoding="utf-8"))


def ui_languages() -> list[str]:
    """UI languages in display order (settings.json: ui-languages)."""
    return load_settings()["ui-languages"]


def validate() -> None:
    """Every key must have a non-empty text in every UI language."""
    missing = [
        f"{key}.{lang}"
        for key, texts in strings().items()
        for lang in ui_languages()
        if not texts.get(lang)
    ]
    if missing:
        raise CatalogError(f"{I18N_PATH.name}: missing translations: {', '.join(missing)}")


class Translator:
    """UI strings for one UI language; t(key) returns HTML-escaped text."""

    def __init__(self, lang: str):
        self.lang = lang

    def raw(self, key: str, **fmt: object) -> str:
        text = strings()[key][self.lang]
        return text.format(**fmt) if fmt else text

    def __call__(self, key: str, **fmt: object) -> str:
        return escape(self.raw(key, **fmt))
