# do not pre-load
"""A supplied client must not be replaced by a default or configured endpoint."""

import os
import unittest
from contextlib import ExitStack
from unittest.mock import MagicMock, patch


def fake_client(base_url="https://api.openai.com/v1/"):
    client = MagicMock()
    client.base_url = base_url
    choice = MagicMock()
    choice.finish_reason = "stop"
    choice.message.content = "ok"
    client.chat.completions.create.return_value.choices = [choice]
    client.moderations.create.return_value.results[0].flagged = False
    return client


class TestClientSelection(unittest.TestCase):
    def setUp(self):
        from docassemble.ALToolbox import llms

        self.llms = llms
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.config = {}
        self.default = fake_client()
        self.created = fake_client()
        self.stack.enter_context(patch.dict(os.environ, {}, clear=True))
        self.stack.enter_context(patch.object(llms, "client", self.default))
        self.stack.enter_context(
            patch.object(
                llms,
                "get_config",
                side_effect=lambda key, default=None: self.config.get(key, default),
            )
        )
        self.factory = self.stack.enter_context(
            patch.object(llms, "OpenAI", return_value=self.created)
        )
        encoding = MagicMock()
        encoding.encode.return_value = []
        self.stack.enter_context(
            patch.object(llms.tiktoken, "encoding_for_model", return_value=encoding)
        )

    def complete(self, **kwargs):
        return self.llms.chat_completion(
            system_message="Be brief", user_message="Hello", model="gpt-4o", **kwargs
        )

    def test_supplied_client_survives_default_and_configured_urls(self):
        for config in (
            {},
            {
                "open ai": {
                    "base url": "https://configured.example/v1/",
                    "key": "test-key",
                }
            },
        ):
            with self.subTest(config=config):
                self.config = config
                supplied = fake_client()
                self.assertEqual(self.complete(openai_client=supplied), "ok")
                supplied.chat.completions.create.assert_called_once()
        self.default.chat.completions.create.assert_not_called()
        self.factory.assert_not_called()

    def test_supplied_client_wins_over_explicit_url_and_key(self):
        supplied = fake_client()
        self.complete(
            openai_client=supplied,
            openai_base_url="https://other.example/v1/",
            openai_api="test-key",
        )
        supplied.chat.completions.create.assert_called_once()
        self.default.chat.completions.create.assert_not_called()
        self.factory.assert_not_called()

    def test_falsey_supplied_client_is_still_authoritative(self):
        supplied = fake_client()
        supplied.__bool__.return_value = False
        self.complete(openai_client=supplied)
        supplied.chat.completions.create.assert_called_once()
        self.factory.assert_not_called()

    def test_default_module_client_remains_the_fallback(self):
        self.complete()
        self.default.chat.completions.create.assert_called_once()
        self.factory.assert_not_called()

    def test_explicit_key_constructs_client_at_default_url(self):
        self.complete(openai_api="test-key")
        self.factory.assert_called_once_with(
            api_key="test-key", base_url="https://api.openai.com/v1/"
        )
        self.created.chat.completions.create.assert_called_once()

    def test_custom_url_constructs_client_from_explicit_or_configured_key(self):
        for configured in (False, True):
            with self.subTest(configured=configured):
                self.factory.reset_mock()
                if configured:
                    self.config = {
                        "open ai": {
                            "base url": "https://local.example/v1/",
                            "key": "test-key",
                        }
                    }
                    self.complete()
                else:
                    self.complete(
                        openai_api="test-key",
                        openai_base_url="https://local.example/v1/",
                    )
                self.factory.assert_called_once_with(
                    api_key="test-key", base_url="https://local.example/v1/"
                )
        self.default.chat.completions.create.assert_not_called()

    def test_moderation_uses_the_supplied_clients_actual_endpoint(self):
        supplied = fake_client()
        self.complete(
            openai_client=supplied,
            openai_base_url="https://ignored.example/v1/",
            skip_moderation=False,
        )
        supplied.moderations.create.assert_called_once()
        custom = fake_client("https://custom.example/v1/")
        self.complete(openai_client=custom, skip_moderation=False)
        custom.moderations.create.assert_not_called()
