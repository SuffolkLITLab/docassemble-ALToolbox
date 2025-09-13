# do not pre-load

import unittest
from unittest.mock import patch, MagicMock
import os
from .llms import _get_openai_api_key, chat_completion


class TestLLMSConfig(unittest.TestCase):
    """Test configuration lookup and parameter handling for LLM functions."""

    @patch("docassemble.ALToolbox.llms.get_config")
    @patch.dict(os.environ, {}, clear=True)
    def test_get_openai_api_key_priority_order(self, mock_get_config):
        """Test that _get_openai_api_key follows the correct priority order."""

        # Test priority 1: direct key configuration "openai api key"
        mock_get_config.side_effect = lambda key, default=None: {
            "openai api key": "direct-key"
        }.get(key, default)

        result = _get_openai_api_key()
        self.assertEqual(result, "direct-key")

        # Test priority 2: standardized nested configuration "openai: key"
        mock_get_config.side_effect = lambda key, default=None: {
            "openai api key": None,
            "openai": {"key": "standardized-key"},
        }.get(key, default)

        result = _get_openai_api_key()
        self.assertEqual(result, "standardized-key")

        # Test priority 3: legacy nested configuration "open ai: key"
        mock_get_config.side_effect = lambda key, default=None: {
            "openai api key": None,
            "openai": {},
            "open ai": {"key": "legacy-key"},
        }.get(key, default)

        result = _get_openai_api_key()
        self.assertEqual(result, "legacy-key")

    @patch("docassemble.ALToolbox.llms.get_config")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}, clear=True)
    def test_get_openai_api_key_environment_fallback(self, mock_get_config):
        """Test that environment variable is used as last resort."""

        # No config keys found, should fall back to environment
        mock_get_config.side_effect = lambda key, default=None: default

        result = _get_openai_api_key()
        self.assertEqual(result, "env-key")

    @patch("docassemble.ALToolbox.llms.get_config")
    @patch.dict(os.environ, {}, clear=True)
    def test_get_openai_api_key_no_key_found(self, mock_get_config):
        """Test that None is returned when no key is found."""

        mock_get_config.side_effect = lambda key, default=None: default

        result = _get_openai_api_key()
        self.assertIsNone(result)

    @patch("docassemble.ALToolbox.llms.get_config")
    def test_get_openai_api_key_handles_non_dict_config(self, mock_get_config):
        """Test that non-dict config values are handled gracefully."""

        # Test when config returns a string instead of dict
        mock_get_config.side_effect = lambda key, default=None: {
            "openai api key": None,
            "openai": "not-a-dict",  # This should be handled gracefully
            "open ai": {"key": "fallback-key"},
        }.get(key, default)

        result = _get_openai_api_key()
        self.assertEqual(result, "fallback-key")

    @patch("docassemble.ALToolbox.llms.OpenAI")
    @patch("docassemble.ALToolbox.llms._get_openai_api_key")
    def test_chat_completion_parameter_backwards_compatibility(
        self, mock_get_key, mock_openai
    ):
        """Test that both openai_api and openai_api_key parameters work."""

        # Mock the OpenAI client
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Mock successful response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].finish_reason = "stop"
        mock_response.choices[0].message.content = "test response"
        mock_client.chat.completions.create.return_value = mock_response

        # Mock moderation
        mock_moderation = MagicMock()
        mock_moderation.results = [MagicMock()]
        mock_moderation.results[0].flagged = False
        mock_client.moderations.create.return_value = mock_moderation

        mock_get_key.return_value = "config-key"

        # Test new parameter name
        result = chat_completion(
            system_message="test", user_message="test", openai_api_key="new-param-key"
        )

        # Should use new parameter value
        mock_openai.assert_called_with(
            base_url="https://api.openai.com/v1/", api_key="new-param-key"
        )

        # Test old parameter name
        result = chat_completion(
            system_message="test", user_message="test", openai_api="old-param-key"
        )

        # Should use old parameter value
        mock_openai.assert_called_with(
            base_url="https://api.openai.com/v1/", api_key="old-param-key"
        )

        # Test both parameters (new should take priority)
        result = chat_completion(
            system_message="test",
            user_message="test",
            openai_api_key="new-param-key",
            openai_api="old-param-key",
        )

        # Should prioritize new parameter
        mock_openai.assert_called_with(
            base_url="https://api.openai.com/v1/", api_key="new-param-key"
        )

        # Test neither parameter (should fall back to config)
        result = chat_completion(system_message="test", user_message="test")

        # Should use config key
        mock_openai.assert_called_with(
            base_url="https://api.openai.com/v1/", api_key="config-key"
        )


if __name__ == "__main__":
    unittest.main()
