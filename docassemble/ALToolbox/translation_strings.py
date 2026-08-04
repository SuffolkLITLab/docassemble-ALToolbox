# pre-load
"""Serve docassemble's ``word()`` translations to JavaScript.

Docassemble can translate any string that reaches Python through ``word()``, but
JavaScript running in the browser has no way to reach that catalog.  Custom
datatypes, validation messages and small widgets therefore end up hardcoded in
English.

This module adds one unauthenticated endpoint, ``/al_translations.json``, that
returns the ``word()`` catalog for a language code.  The companion
``al_translate.js`` fetches it once, caches it in ``localStorage``, and exposes
``_("Some string")`` to any JavaScript on the page.

Authors add translations the ordinary docassemble way: a word translation file
listed under ``words:`` in the server configuration.  See the README for the
file format.

The endpoint is registered with Flask using the "Building a custom page with
Flask" recipe (https://docassemble.org/docs/recipes.html#flask%20page), which
requires the ``# pre-load`` marker on the first line of this file.
"""

import json
import re
from typing import Dict, Iterator, Optional

from docassemble.base.functions import (
    get_language,
    update_word_collection,
    word_collection,
)
from docassemble.base.util import log

__all__ = ["add_translations", "translate", "translation_catalog"]

# Every string ALToolbox's own JavaScript passes to `_()`. Nothing reads this at
# runtime; it is the checklist a translator needs, and a test keeps it honest by
# grepping the shipped .js files.
ALTOOLBOX_JS_STRINGS = [
    "You have entered %d character.",
    "You have entered %d characters.",
]

_TRAILING_PUNCTUATION = ".:!?"


def _normalize(text: str) -> str:
    """Reduce a string to the form used for fuzzy matching.

    Collapses runs of whitespace, drops trailing punctuation, and lowercases,
    so that "Copied!" and "copied" find the same translation.
    """
    collapsed = re.sub(r"\s+", " ", text).strip()
    return collapsed.rstrip(_TRAILING_PUNCTUATION).lower()


def _match_shape(source: str, translated: str) -> str:
    """Give `translated` the capitalization and trailing punctuation of `source`.

    Only used after a fuzzy match, so that translating "Copied!" against a
    catalog entry for "copied" still comes back as "¡Copiado!" rather than
    "copiado".
    """
    stripped_source = source.strip()
    result = translated.strip()
    if not result:
        return source
    trailing = re.search(r"[" + _TRAILING_PUNCTUATION + r"]+$", stripped_source)
    if trailing and result[-1] not in _TRAILING_PUNCTUATION:
        result += trailing.group(0)
    if stripped_source[:1].isupper() and result[:1].islower():
        result = result[0].upper() + result[1:]
    return result


def _language_candidates(language: str) -> Iterator[str]:
    """Yield the languages to merge, least to most specific.

    A page in "es-MX" should get the "es" catalog with any "es-MX" entries
    layered on top.
    """
    base = re.split(r"[-_]", language)[0]
    if base and base != language:
        yield base
    yield language


def translation_catalog(language: Optional[str] = None) -> Dict[str, str]:
    """Return the whole ``word()`` catalog for a language as ``{source: translation}``.

    Args:
        language: A language code such as ``"es"`` or ``"es-MX"``. Defaults to
            the current language.

    Returns:
        A copy of the catalog. Unknown languages return an empty dictionary,
        which is correct: every string then falls back to its source text.
    """
    if language is None:
        language = get_language()
    catalog: Dict[str, str] = {}
    for candidate in _language_candidates(language):
        entries = word_collection.get(candidate)
        if isinstance(entries, dict):
            catalog.update(
                {
                    str(source): str(translated)
                    for source, translated in entries.items()
                    if translated is not None
                }
            )
    return catalog


def translate(text: str, language: Optional[str] = None) -> str:
    """Translate one string exactly the way ``al_translate.js`` does.

    Tries an exact match first, then a match that ignores whitespace,
    capitalization and trailing punctuation. Returns `text` unchanged when
    there is no translation.

    This is the server-side twin of the JavaScript ``_()``; use it when Python
    and JavaScript need to agree on the same string.
    """
    catalog = translation_catalog(language)
    if text in catalog:
        return catalog[text]
    normalized = _normalize(text)
    for source, translated in catalog.items():
        if _normalize(source) == normalized:
            return _match_shape(text, translated)
    return text


def add_translations(language: str, translations: Dict[str, str]) -> None:
    """Add entries to the ``word()`` catalog at runtime.

    A word translation file listed under ``words:`` in the server configuration
    is the better home for anything permanent: it loads once at startup and
    every interview on the server sees it. Use this when the translations come
    from somewhere else, or in a demo that has to run without a configuration
    change.

    Docassemble exposes ``update_word_collection()`` for this, but does not
    include it in the names an interview can reach, so this is a thin wrapper
    that ``include:``-ing ``translation_strings.yml`` makes available.

    Args:
        language: A language code such as ``"es"``.
        translations: ``{source string: translation}``.

    Note:
        The catalog is process-wide and shared by every session, so pass the
        same translations on every run rather than anything derived from one
        user's answers.
    """
    update_word_collection(language, translations)


def _catalog_response_body(language: str) -> str:
    """Build the JSON body served by the endpoint."""
    return json.dumps(
        {
            "language": language,
            "words": translation_catalog(language),
        },
        ensure_ascii=False,
        sort_keys=True,
    )


try:
    try:
        from docassemble.webapp.app_object import flaskapp as app  # 1.10 and later
    except ImportError:
        from docassemble.webapp.app_object import app  # type: ignore[no-redef]  # 1.9.x

    from flask import Response, request
    from werkzeug.wrappers import Response as BaseResponse

    @app.route("/al_translations.json", methods=["GET"])
    def al_translations_json() -> BaseResponse:
        """Return the ``word()`` catalog for ``?lang=<code>`` as JSON.

        Unauthenticated and session-independent on purpose: the response is the
        same for every user of a given language, which is what makes it worth
        caching in the browser. It serves the server's configured ``word()``
        catalog for that language.
        """
        language = request.args.get("lang") or get_language()
        body = _catalog_response_body(language)
        response = Response(body, mimetype="application/json")
        # A short max-age keeps a newly installed word file from taking hours to
        # show up; the ETag means the usual revalidation costs a 304.
        response.headers["Cache-Control"] = "public, max-age=300"
        response.add_etag()
        return response.make_conditional(request)

except BaseException as error:  # pragma: no cover - depends on the environment
    # BaseException, not Exception: outside a configured web server (in a test
    # run, say) importing the Flask app calls sys.exit(). A server that cannot
    # register the route should serve untranslated JavaScript; nothing here is
    # worth taking the process down for.
    log(
        "ALToolbox: could not register /al_translations.json: "
        f"{error.__class__.__name__}: {error}"
    )
