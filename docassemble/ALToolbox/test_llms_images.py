# do not pre-load
"""Sending images through chat_completion.

The endpoint takes a message whose content is a list of parts; everything here
is about getting that shape right without disturbing the ordinary
string-content path.

`llms` reads the docassemble configuration at import, and the fixture that
stands in for a server is session-scoped, so it is not registered yet while
pytest is collecting. Hence the imports inside the tests rather than at the top.
"""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64
JPEG = b"\xff\xd8\xff" + b"0" * 64


def _llms():
    from docassemble.ALToolbox import llms

    return llms


class TestImageNormalisation(unittest.TestCase):
    def test_bytes_become_a_data_uri_with_a_sniffed_media_type(self):
        as_url = _llms()._as_image_url
        self.assertTrue(as_url(PNG).startswith("data:image/png;base64,"))
        self.assertTrue(as_url(JPEG).startswith("data:image/jpeg;base64,"))

    def test_urls_and_data_uris_pass_through(self):
        as_url = _llms()._as_image_url
        self.assertEqual(
            as_url("https://example.com/a.png"), "https://example.com/a.png"
        )
        self.assertEqual(as_url("data:image/png;base64,AA"), "data:image/png;base64,AA")

    def test_anything_else_is_refused_clearly(self):
        with self.assertRaises(ValueError) as caught:
            _llms()._as_image_url("/tmp/not-a-url.png")
        self.assertIn("DAFile", str(caught.exception))

    def test_da_file_bytes_are_read_from_path(self):
        """A DAFile is resolved to bytes via .path() before sniffing the media type."""
        llms = _llms()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(PNG)
            tmp_path = tmp.name
        try:
            da_file = MagicMock(spec=llms.DAFile)
            da_file.path.return_value = tmp_path
            result = llms._as_image_url(da_file)
            self.assertTrue(result.startswith("data:image/png;base64,"))
        finally:
            os.unlink(tmp_path)


class TestMessageText(unittest.TestCase):
    def test_string_content_is_returned_unchanged(self):
        self.assertEqual(_llms()._message_text({"content": "hello"}), "hello")

    def test_only_the_text_parts_are_read(self):
        message = {
            "content": [
                {"type": "text", "text": "what is this"},
                {
                    "type": "image_url",
                    "image_url": {"url": "data:image/png;base64,AA"},
                },
            ]
        }
        self.assertEqual(_llms()._message_text(message), "what is this")


class TestAttachImages(unittest.TestCase):
    def test_the_last_user_message_becomes_multimodal(self):
        messages = [
            {"role": "system", "content": "be brief"},
            {"role": "user", "content": "what is this"},
        ]
        attached = _llms()._attach_images(messages, [PNG])
        self.assertEqual(attached[0], {"role": "system", "content": "be brief"})
        parts = attached[1]["content"]
        self.assertEqual([part["type"] for part in parts], ["text", "image_url"])
        self.assertEqual(parts[0]["text"], "what is this")
        # The caller's own list is left alone.
        self.assertEqual(messages[1]["content"], "what is this")

    def test_no_images_changes_nothing(self):
        messages = [{"role": "user", "content": "hello"}]
        self.assertEqual(_llms()._attach_images(messages, []), messages)

    def test_a_user_message_is_added_when_there_is_none(self):
        attached = _llms()._attach_images(
            [{"role": "system", "content": "be brief"}], [PNG]
        )
        self.assertEqual(attached[-1]["role"], "user")
        self.assertEqual(
            [part["type"] for part in attached[-1]["content"]],
            ["text", "image_url"],
        )

    def test_detail_is_passed_through_when_asked_for(self):
        attached = _llms()._attach_images(
            [{"role": "user", "content": "x"}], [PNG], image_detail="low"
        )
        self.assertEqual(attached[0]["content"][1]["image_url"]["detail"], "low")

    def test_several_images_all_arrive_on_one_message(self):
        attached = _llms()._attach_images(
            [{"role": "user", "content": "x"}], [PNG, JPEG]
        )
        self.assertEqual(
            [part["type"] for part in attached[0]["content"]],
            ["text", "image_url", "image_url"],
        )


def _fake_client(reply="ok"):
    client = MagicMock()
    moderation_result = MagicMock()
    moderation_result.flagged = False
    client.moderations.create.return_value.results = [moderation_result]
    choice = MagicMock()
    choice.finish_reason = "stop"
    choice.message.content = reply
    completion = MagicMock()
    completion.choices = [choice]
    client.chat.completions.create.return_value = completion
    return client


class TestChatCompletionWithImages(unittest.TestCase):
    """The three things that used to get in the way of sending a picture."""

    def _call(self, reply="ok", **kwargs):
        # The module-level client, rather than the openai_client argument:
        # chat_completion sets openai_base_url from config before it checks,
        # and then discards the caller's client because the url is truthy.
        llms = _llms()
        fake = _fake_client(reply)
        with patch.object(llms, "client", fake):
            llms.chat_completion(model="gpt-4o", skip_moderation=True, **kwargs)
        return fake.chat.completions.create.call_args.kwargs

    def test_an_image_reaches_the_endpoint_as_a_part(self):
        sent = self._call(
            system_message="be brief", user_message="what is this", images=[PNG]
        )
        parts = sent["messages"][-1]["content"]
        self.assertEqual([part["type"] for part in parts], ["text", "image_url"])
        self.assertTrue(
            parts[1]["image_url"]["url"].startswith("data:image/png;base64,")
        )

    def test_json_mode_and_images_can_be_combined(self):
        """The json check used to call .lower() on a list and raise."""
        sent = self._call(
            reply='{"alt": "a seal"}',
            system_message="reply with json",
            user_message="what is this",
            images=[PNG],
            json_mode=True,
        )
        self.assertEqual(sent["response_format"], {"type": "json_object"})

    def test_a_large_image_does_not_trip_the_input_limit(self):
        """Counting base64 as text made the endpoint refuse its own input."""
        big = b"\x89PNG\r\n\x1a\n" + b"0" * (2 * 1024 * 1024)
        sent = self._call(
            system_message="be brief",
            user_message="what is this",
            images=[big],
            image_detail="low",
        )
        self.assertEqual(
            [part["type"] for part in sent["messages"][-1]["content"]],
            ["text", "image_url"],
        )

    def test_image_is_included_in_multimodal_moderation(self):
        llms = _llms()
        fake = _fake_client()
        with patch.object(llms, "client", fake):
            llms.chat_completion(
                model="gpt-4o",
                system_message="be brief",
                user_message="what is this",
                images=[PNG],
                image_detail="high",
                skip_moderation=False,
            )
        moderation_call = fake.moderations.create.call_args.kwargs
        self.assertEqual(moderation_call["model"], "omni-moderation-latest")
        self.assertEqual(
            [part["type"] for part in moderation_call["input"]],
            ["text", "image_url"],
        )
        self.assertNotIn("detail", moderation_call["input"][1]["image_url"])

    def test_nano_image_cost_is_applied_to_input_limit(self):
        llms = _llms()
        fake = _fake_client()
        with patch.object(llms, "client", fake), self.assertRaises(Exception) as caught:
            llms.chat_completion(
                model="gpt-4.1-nano",
                system_message="be brief",
                user_message="what is this",
                images=[PNG],
                image_detail="high",
                max_input_tokens=2000,
                skip_moderation=True,
            )
        self.assertIn("Input to OpenAI is too long", str(caught.exception))
        fake.chat.completions.create.assert_not_called()

    def test_nothing_changes_when_no_images_are_supplied(self):
        sent = self._call(system_message="be brief", user_message="hello")
        self.assertEqual(
            sent["messages"],
            [
                {"role": "system", "content": "be brief"},
                {"role": "user", "content": "hello"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
