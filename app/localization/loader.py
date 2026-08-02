"""Loads locale JSON files once at startup and exposes t(key, lang, **kwargs).
Adding a new language later = drop a new locales/xx.json + add it to
config.SUPPORTED_LANGUAGES. No other code changes needed."""

import json
from pathlib import Path

from app.config import SUPPORTED_LANGUAGES, settings

_LOCALES_DIR = Path(__file__).parent / "locales"
_catalog: dict[str, dict[str, str]] = {}


def load_locales() -> None:
    for lang in SUPPORTED_LANGUAGES:
        path = _LOCALES_DIR / f"{lang}.json"
        with open(path, encoding="utf-8") as f:
            _catalog[lang] = json.load(f)


def t(key: str, lang: str | None, **kwargs) -> str:
    lang = lang if lang in _catalog else settings.default_language
    template = _catalog.get(lang, {}).get(key) or _catalog[settings.default_language].get(key, key)
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template
