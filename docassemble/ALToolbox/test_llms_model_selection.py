# do not pre-load
"""Model discovery should recognize size tiers without substring collisions."""

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def load_llms(docassemble_context):
    global llms
    from docassemble.ALToolbox import llms


@pytest.fixture
def discovery():
    with (
        patch.object(llms, "list_available_models") as models,
        patch.object(llms, "get_config", side_effect=lambda key, default=None: default),
        patch.object(llms, "log") as log,
    ):
        models.return_value = []
        yield models, log


@pytest.mark.parametrize(
    "model",
    [
        "gpt-5.6-luna",
        "GPT-6-LUNA",
        "luna",
        "luna-2026-09-01",
        "openai/gpt-5.6-luna",
        "deployment_luna:latest",
    ],
)
def test_luna_discovery(discovery, model):
    models, _ = discovery
    models.return_value = [model]
    assert llms.get_first_small_model() == model


@pytest.mark.parametrize(
    "model",
    [
        "lunaris",
        "sublunar",
        "gpt-5.6-terra",
        "gpt-5.6-sol",
        "gpt-5.6-terra-fast",
        "gpt-5.6-sol-turbo",
        "SOL-mini",
        "terra/luna",
        "gemini-2.5-pro",
        "satellite-large",
    ],
)
def test_non_small_models_are_excluded(discovery, model):
    models, log = discovery
    models.return_value = [model]
    assert llms.get_first_small_model() is None
    assert model in log.call_args.args[0]


def test_provider_order_and_legacy_keywords(discovery):
    models, _ = discovery
    models.return_value = ["gpt-5.6-sol-fast", "claude-3-haiku", "gpt-5.6-luna"]
    assert llms.get_first_small_model() == "claude-3-haiku"


def test_config_keywords_and_explicit_override(discovery):
    models, _ = discovery
    models.return_value = ["custom-TINY", "gpt-5.6-luna"]
    with patch.object(
        llms, "get_config", return_value={"small model keywords": ["tiny"]}
    ):
        assert llms.get_first_small_model() == "custom-TINY"
        assert llms.get_first_small_model(keywords=["luna"]) == "gpt-5.6-luna"
        assert llms.get_first_small_model(keywords=[]) is None


@pytest.mark.parametrize("keywords", ["tiny", [None], 42])
def test_invalid_config_uses_defaults(discovery, keywords):
    models, _ = discovery
    models.return_value = ["gpt-5.6-luna"]
    with patch.object(
        llms, "get_config", return_value={"small model keywords": keywords}
    ):
        assert llms.get_first_small_model() == "gpt-5.6-luna"


def test_empty_keywords_do_not_match_every_model(discovery):
    models, _ = discovery
    models.return_value = ["large-model"]
    assert llms.get_first_small_model(keywords=[""]) is None


@pytest.mark.parametrize(
    "size,new,old",
    [
        ("small", "gpt-5.6-luna", "gpt-5-nano"),
        ("medium", "gpt-5.6-terra", "gpt-5-mini"),
        ("large", "gpt-5.6-sol", "gpt-5"),
    ],
)
def test_default_preferences_and_fallbacks(discovery, size, new, old):
    models, _ = discovery
    for available, expected in [
        ([old, new], new),
        ([new], new),
        ([old], old),
        ([], old),
    ]:
        models.return_value = available
        assert llms.get_default_model(size) == expected


def test_configured_model_takes_precedence(discovery):
    with patch.object(
        llms,
        "get_config",
        side_effect=lambda key, default=None: (
            {"default small model": "deployment"} if key == "open ai" else default
        ),
    ):
        assert llms.get_default_model() == "deployment"


@pytest.mark.parametrize("model", ["gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"])
def test_tier_model_family(model):
    assert llms.detect_model_family(model) == "openai"


def test_unrelated_family():
    assert llms.detect_model_family("lunaris-large") == "lunaris"


@pytest.mark.parametrize("size", ["medium", "large"])
def test_larger_tiers_do_not_fall_back_to_small(discovery, size):
    models, _ = discovery
    models.return_value = ["gpt-5.6-luna"]
    assert llms.get_default_model(size) == llms.MODEL_TYPE_FALLBACKS[size]


def test_default_discovery_logs_no_match_once(discovery):
    models, log = discovery
    models.return_value = ["large-only"]
    assert llms.get_default_model() == "gpt-5-nano"
    log.assert_called_once()


def test_custom_keywords_override_tier_exclusions(discovery):
    models, _ = discovery
    models.return_value = ["terrazzo", "gpt-5.6-terra"]
    assert llms.get_first_small_model(keywords=["terra"]) == "gpt-5.6-terra"


def test_configured_empty_keywords_disable_matching(discovery):
    models, _ = discovery
    models.return_value = ["gpt-5.6-luna"]
    with patch.object(llms, "get_config", return_value={"small model keywords": []}):
        assert llms.get_first_small_model() is None
