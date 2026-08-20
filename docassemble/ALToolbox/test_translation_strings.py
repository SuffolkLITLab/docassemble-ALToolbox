# do not pre-load

import os
import re
import unittest
from unittest.mock import patch

from .translation_strings import (
    ALTOOLBOX_JS_STRINGS,
    _catalog_response_body,
    _match_shape,
    _normalize,
    add_translations,
    translate,
    translation_catalog,
)

FAKE_WORDS = {
    "es": {
        "Copied!": "¡Copiado!",
        "you have entered %d characters.": "Ha escrito %d caracteres.",
        "Cancel": None,
    },
    "es-MX": {
        "Copied!": "¡Ya se copió!",
    },
}


# Depending on how the tests are run, this package is importable under either
# name, and each import is a distinct module object, so both have to be patched.
MODULE_PATHS = (
    "docassemble.ALToolbox.translation_strings",
    "ALToolbox.translation_strings",
)


def with_fake_words(func):
    """Swap in a small, predictable word_collection for the duration of a test."""
    for module_path in MODULE_PATHS:
        func = patch(f"{module_path}.word_collection", FAKE_WORDS)(func)
    return func


def with_language(language: str):
    """Pretend the server's current language is `language`."""

    def decorate(func):
        for module_path in MODULE_PATHS:
            func = patch(f"{module_path}.get_language", lambda: language)(func)
        return func

    return decorate


class TestNormalize(unittest.TestCase):
    def test_collapses_whitespace_punctuation_and_case(self) -> None:
        self.assertEqual(_normalize("  Copied!  "), "copied")
        self.assertEqual(_normalize("Are you\n  sure?"), "are you sure")
        self.assertEqual(_normalize("Name:"), "name")

    def test_leaves_interior_punctuation_alone(self) -> None:
        self.assertEqual(_normalize("Yes. No."), "yes. no")


class TestMatchShape(unittest.TestCase):
    def test_restores_capitalization_and_trailing_punctuation(self) -> None:
        self.assertEqual(_match_shape("Copied!", "copiado"), "Copiado!")

    def test_does_not_double_up_punctuation(self) -> None:
        self.assertEqual(_match_shape("Copied!", "¡Copiado!"), "¡Copiado!")

    def test_leaves_a_lowercase_source_lowercase(self) -> None:
        self.assertEqual(_match_shape("copied", "copiado"), "copiado")

    def test_empty_translation_falls_back_to_the_source(self) -> None:
        self.assertEqual(_match_shape("Copied!", "   "), "Copied!")


class TestTranslationCatalog(unittest.TestCase):
    @with_fake_words
    def test_returns_the_catalog_for_a_language(self) -> None:
        catalog = translation_catalog("es")
        self.assertEqual(catalog["Copied!"], "¡Copiado!")

    @with_fake_words
    def test_drops_entries_with_no_translation(self) -> None:
        self.assertNotIn("Cancel", translation_catalog("es"))

    @with_fake_words
    def test_a_regional_language_layers_on_top_of_its_base(self) -> None:
        catalog = translation_catalog("es-MX")
        # Overridden by the regional catalog...
        self.assertEqual(catalog["Copied!"], "¡Ya se copió!")
        # ...but the base language's other entries still come through.
        self.assertIn("you have entered %d characters.", catalog)

    @with_fake_words
    def test_an_unknown_language_is_empty_rather_than_an_error(self) -> None:
        self.assertEqual(translation_catalog("fr"), {})

    @with_fake_words
    @with_language("es")
    def test_defaults_to_the_current_language(self) -> None:
        self.assertEqual(translation_catalog()["Copied!"], "¡Copiado!")


class TestTranslate(unittest.TestCase):
    @with_fake_words
    def test_exact_match(self) -> None:
        self.assertEqual(translate("Copied!", "es"), "¡Copiado!")

    @with_fake_words
    def test_fuzzy_match_restores_the_shape_of_the_source(self) -> None:
        # The catalog entry is lowercase and the source is not.
        self.assertEqual(
            translate("You have entered %d characters.", "es"),
            "Ha escrito %d caracteres.",
        )

    @with_fake_words
    def test_untranslated_strings_come_back_unchanged(self) -> None:
        self.assertEqual(translate("Not in the catalog", "es"), "Not in the catalog")

    @with_fake_words
    def test_an_unknown_language_returns_the_source(self) -> None:
        self.assertEqual(translate("Copied!", "fr"), "Copied!")


class TestAddTranslations(unittest.TestCase):
    def test_added_translations_are_visible_to_translate(self) -> None:
        # Deliberately not patched: this has to reach docassemble's real,
        # process-wide word_collection to be worth anything.
        add_translations("zz", {"Copied!": "Xopied"})
        try:
            self.assertEqual(translate("Copied!", "zz"), "Xopied")
        finally:
            from docassemble.base.functions import word_collection as real_words

            real_words.pop("zz", None)

    def test_interviews_can_reach_it(self) -> None:
        """`modules: - .translation_strings` only exposes names in __all__."""
        from . import translation_strings

        self.assertIn("add_translations", translation_strings.__all__)


class TestCatalogResponseBody(unittest.TestCase):
    @with_fake_words
    def test_body_is_stable_json_with_the_language_and_words(self) -> None:
        body = _catalog_response_body("es")
        self.assertIn('"language": "es"', body)
        self.assertIn("¡Copiado!", body)
        # Sorted keys, so an unchanged catalog always produces the same ETag.
        self.assertEqual(body, _catalog_response_body("es"))


class TestAltoolboxJsStrings(unittest.TestCase):
    """Keep the translator's checklist in step with the shipped JavaScript."""

    def _static_path(self, name: str) -> str:
        return os.path.join(os.path.dirname(__file__), "data", "static", name)

    def test_loader_uses_the_json_catalog_endpoint(self) -> None:
        with open(self._static_path("al_translate.js"), encoding="utf-8") as loader:
            source = loader.read()
        self.assertIn("al_translations.json?lang=", source)
        self.assertNotIn("al_translations.js?lang=", source)

    def test_every_string_passed_to_the_translator_is_listed(self) -> None:
        with open(self._static_path("TextCounter.js"), encoding="utf-8") as counter_js:
            source = counter_js.read()
        with open(
            self._static_path("phone-number-validation.js"), encoding="utf-8"
        ) as phone_js:
            source += phone_js.read()
        found = set(
            re.findall(r'\b_\(\s*"((?:[^"\\]|\\.)*)"', source)
            + re.findall(r'\btranslate\(\s*"((?:[^"\\]|\\.)*)"', source)
        )
        self.assertTrue(found, "expected ALToolbox JavaScript to call a translator")
        self.assertTrue(
            found.issubset(set(ALTOOLBOX_JS_STRINGS)),
            f"missing from ALTOOLBOX_JS_STRINGS: {found - set(ALTOOLBOX_JS_STRINGS)}",
        )

        with open(
            os.path.join(os.path.dirname(__file__), "PhoneNumberDataType.py"),
            encoding="utf-8",
        ) as phone_datatype:
            self.assertIn(
                'This phone number doesn\'t look right. Note that a non-US number needs a "+" before the number.',
                phone_datatype.read(),
            )

    def test_the_shipped_word_file_covers_every_string(self) -> None:
        import yaml  # type: ignore[import-untyped]

        path = os.path.join(
            os.path.dirname(__file__), "data", "sources", "altoolbox_words.yml"
        )
        with open(path, encoding="utf-8") as word_file:
            words = yaml.safe_load(word_file)
        for language, entries in words.items():
            missing = set(ALTOOLBOX_JS_STRINGS) - set(entries)
            self.assertFalse(missing, f"{language} is missing: {missing}")


if __name__ == "__main__":
    unittest.main()
