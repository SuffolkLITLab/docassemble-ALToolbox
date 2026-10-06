# do not pre-load
"""Which models get `reasoning_effort` instead of a temperature.

OpenAI's thinking models reject any temperature but the default, so sending
one to gpt-6-luna failed with a 400 "Unsupported value: 'temperature'".

`llms` reads the docassemble configuration at import, so it is imported inside
the tests (see test_llms_images.py).
"""

import unittest
from unittest.mock import MagicMock, patch


def _llms():
    from docassemble.ALToolbox import llms

    return llms


class TestIsThinkingModel(unittest.TestCase):
    def test_gpt_5_and_every_later_version_are_thinking_models(self):
        for model in [
            "gpt-5",
            "gpt-5-mini",
            "gpt-5-nano",
            "gpt-5.6-luna",
            "gpt-6-luna",
            "gpt-6-sol",
            "gpt-6.1-sol",
            "gpt-7",
            "gpt-10-mini",
        ]:
            with self.subTest(model=model):
                self.assertTrue(_llms()._is_thinking_model(model))

    def test_o_series_models_still_are(self):
        for model in ["o1", "o1-mini", "o3", "o3-mini"]:
            with self.subTest(model=model):
                self.assertTrue(_llms()._is_thinking_model(model))

    def test_earlier_gpt_models_take_a_temperature(self):
        for model in [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-3.5-turbo",
        ]:
            with self.subTest(model=model):
                self.assertFalse(_llms()._is_thinking_model(model))


class TestChatCompletionParameters(unittest.TestCase):
    def _sent(self, model):
        llms = _llms()
        fake = MagicMock()
        choice = MagicMock()
        choice.finish_reason = "stop"
        choice.message.content = "ok"
        fake.chat.completions.create.return_value.choices = [choice]
        with patch.object(llms, "client", fake):
            llms.chat_completion(
                model=model,
                system_message="be brief",
                user_message="hello",
                skip_moderation=True,
            )
        return fake.chat.completions.create.call_args.kwargs

    def test_gpt_6_is_sent_reasoning_effort_and_no_temperature(self):
        sent = self._sent("gpt-6-luna")
        self.assertNotIn("temperature", sent)
        self.assertIn("reasoning_effort", sent)

    def test_gpt_4o_still_gets_its_temperature(self):
        sent = self._sent("gpt-4o")
        self.assertIn("temperature", sent)
        self.assertNotIn("reasoning_effort", sent)
