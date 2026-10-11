"""Interface languages (not the language of the generated content, which is a form field).

Spanish is the main language; English, Portuguese and French are also available. To add a language:
1. create app/i18n/<code>.py with the same MESSAGES keys as es.py (enforced by tests);
2. register it in SUPPORTED_LANGUAGES and CATALOGS.
The selector (GET /language/<code>), `<html lang>`, the `t()` helper in templates and the
JavaScript texts (keys starting with "js.") pick it up automatically.
"""

from collections.abc import Callable

from fastapi import Request

from app.i18n import en, es, fr, pt

DEFAULT_LANGUAGE = "es"
LANGUAGE_COOKIE = "ui_lang"
JS_PREFIX = "js."

# Code -> name shown in the selector, in that language.
SUPPORTED_LANGUAGES: dict[str, str] = {"es": "Español", "en": "English", "pt": "Portugués", "fr": "Francés"}
CATALOGS: dict[str, dict[str, str]] = {"es": es.MESSAGES, "en": en.MESSAGES, "pt": pt.MESSAGES, "fr": fr.MESSAGES}

Translator = Callable[..., str]


def resolve_language(request: Request) -> str:
    """The interface language: a supported `ui_lang` cookie, otherwise Spanish."""
    requested = request.cookies.get(LANGUAGE_COOKIE, "")
    return requested if requested in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def translator(language: str) -> Translator:
    catalog = CATALOGS.get(language, CATALOGS[DEFAULT_LANGUAGE])
    fallback = CATALOGS[DEFAULT_LANGUAGE]

    def t(key: str, **params: object) -> str:
        text = catalog.get(key) or fallback.get(key)
        if text is None:
            # A missing key is a programming error: show it, so tests and reviews catch it.
            return key
        return text.format(**params) if params else text

    return t


def js_messages(language: str) -> dict[str, str]:
    """The texts the JavaScript shows, in `language` (placeholders such as {max} are filled in by the JS)."""
    catalog = CATALOGS[DEFAULT_LANGUAGE] | CATALOGS.get(language, {})
    return {key: text for key, text in catalog.items() if key.startswith(JS_PREFIX)}
