"""Minimal docassemble runtime context for the python-only unit tests.

As of docassemble 1.10, per-request state lives in a contextvar exposed as
`docassemble.base.thread_context.this_thread`, and the defaults that back it
(language, locale, timezone, ...) come from pluggy hooks that only
`docassemble.webapp` registers when a server starts up. Under plain pytest
neither exists, so library code that calls `get_locale()` or `as_datetime()`
fails on `None`.

These fixtures stand in for the server: they register the handful of default
hooks the tests need and wrap each test in a fresh global context.
"""

import locale

import pluggy
import pytest

from docassemble.base.plugin_manager import pm
from docassemble.base.thread_context import empty_globals, global_context

hookimpl = pluggy.HookimplMarker("docassemble")

# The locale the tests assume unless one of them overrides it. The workflow
# runs locale-gen for this and for ar_AE.UTF-8.
TEST_LOCALE = "en_US.UTF-8"


class DefaultsPlugin:
    """Supplies the same defaults a docassemble server would with no config."""

    @hookimpl
    def get_default_language(self) -> str:
        return "en"

    @hookimpl
    def get_default_dialect(self) -> str:
        return "us"

    @hookimpl
    def get_default_locale(self) -> str:
        return "en_US.utf8"

    @hookimpl
    def get_default_country(self) -> str:
        return "US"

    @hookimpl
    def get_default_timezone(self) -> str:
        return "America/New_York"

    @hookimpl
    def get_configuration(self) -> dict:
        return {}


@pytest.fixture(scope="session", autouse=True)
def docassemble_defaults():
    plugin = DefaultsPlugin()
    pm.register(plugin, name="altoolbox_test_defaults")
    yield
    pm.unregister(plugin)


@pytest.fixture(autouse=True)
def docassemble_context(docassemble_defaults):
    """Give each test its own `this_thread`, so state can't leak between them."""
    with global_context(empty_globals()):
        yield


@pytest.fixture(autouse=True)
def us_locale():
    """Run every test under the US locale.

    `frac_digits` drives currency rounding in al_income, so tests that expect
    two decimal places need a locale that specifies them. Restoring afterwards
    keeps the tests that deliberately switch locales from leaking.
    """
    previous = locale.setlocale(locale.LC_ALL)
    locale.setlocale(locale.LC_ALL, TEST_LOCALE)
    yield
    locale.setlocale(locale.LC_ALL, previous)
