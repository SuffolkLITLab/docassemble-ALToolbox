# do not pre-load
"""AIAssist: permission, one call per input, validated suggestions, fallbacks.

`llms` reads the docassemble configuration at import, so `ai_assist` is
imported inside the tests (see test_llms_images.py).
"""

import unittest
from unittest.mock import patch


def _module():
    from docassemble.ALToolbox import ai_assist

    return ai_assist


def _assist(answers, **settings):
    """An AIAssist whose `value()` reads from `answers`."""
    module = _module()
    assist = module.AIAssist("assist", **settings)
    patcher = patch.object(module, "value", side_effect=lambda name: answers[name])
    patcher.start()
    available = patch.object(module.llms, "client", object())
    available.start()
    return assist, [patcher, available]


class AIAssistTestCase(unittest.TestCase):
    def make(self, answers, **settings):
        assist, patchers = _assist(answers, **settings)
        for patcher in patchers:
            self.addCleanup(patcher.stop)
        return assist


class TestPermission(AIAssistTestCase):
    def test_asks_for_permission_before_calling(self):
        assist = self.make({"story": "It rained."}, source="story")
        with patch.object(_module().llms, "chat_completion") as call:
            with self.assertRaises(AttributeError):
                assist.suggestion()  # docassemble asks for assist.use_ai here
            call.assert_not_called()

    def test_the_answer_comes_before_the_permission_question(self):
        assist = self.make({}, source="story")
        with self.assertRaises(KeyError):  # docassemble asks for story here
            assist.suggestion()

    def test_declining_keeps_the_original_text(self):
        assist = self.make({"story": "It rained."}, source="story", use_ai=False)
        with patch.object(_module().llms, "chat_completion") as call:
            self.assertEqual(assist.suggestion(), "It rained.")
            call.assert_not_called()
        self.assertEqual(assist.status, "declined")
        self.assertEqual(assist.review_note(), "")

    def test_no_service_is_reported_as_unavailable(self):
        assist = self.make({"story": "x"}, source="story", use_ai=False)
        with patch.object(_module().llms, "client", None):
            self.assertFalse(assist.ai_available())
            assist.run()
        self.assertEqual(assist.status, "unavailable")


class TestText(AIAssistTestCase):
    def test_rewrite_sends_only_the_source_and_caches(self):
        assist = self.make(
            {"story": "it rained", "secret": "nope"}, source="story", use_ai=True
        )
        with patch.object(
            _module().llms, "chat_completion", return_value=" It rained. "
        ) as call:
            self.assertEqual(assist.suggestion(), "It rained.")
            self.assertEqual(assist.suggestion(), "It rained.")
            assist.review_note()
        self.assertEqual(call.call_count, 1)
        self.assertEqual(call.call_args.kwargs["user_message"], "it rained")
        self.assertIn("Do not add facts", call.call_args.kwargs["system_message"])
        self.assertEqual(assist.status, "suggested")
        self.assertIn("AI suggested", assist.review_note())

    def test_changed_input_calls_again(self):
        answers = {"story": "first"}
        assist = self.make(answers, source="story", use_ai=True)
        with patch.object(
            _module().llms, "chat_completion", side_effect=["one", "two"]
        ) as call:
            self.assertEqual(assist.suggestion(), "one")
            answers["story"] = "second"
            self.assertEqual(assist.suggestion(), "two")
        self.assertEqual(call.call_count, 2)

    def test_prompt_uses_the_author_prompt_and_extra_inputs(self):
        assist = self.make(
            {"story": "s", "county": "Suffolk"},
            task="prompt",
            source="story",
            inputs=["county"],
            instructions="List the deadlines.",
            model="small-model",
            use_ai=True,
        )
        with patch.object(
            _module().llms, "chat_completion", return_value="none"
        ) as call:
            assist.suggestion()
        self.assertEqual(call.call_args.kwargs["system_message"], "List the deadlines.")
        self.assertEqual(call.call_args.kwargs["user_message"], "s\n\ncounty:\nSuffolk")
        self.assertEqual(call.call_args.kwargs["model"], "small-model")

    def test_failure_falls_back_and_says_so(self):
        assist = self.make({"story": "mine"}, source="story", use_ai=True)
        with (
            patch.object(
                _module().llms, "chat_completion", side_effect=RuntimeError("boom mine")
            ),
            patch.object(_module(), "log") as log,
        ):
            self.assertEqual(assist.suggestion(), "mine")
        self.assertEqual(assist.status, "error")
        self.assertIn("could not get help", assist.review_note())
        self.assertNotIn("mine", log.call_args.args[0])

    def test_a_failure_is_not_retried_on_every_page_load(self):
        assist = self.make({"story": "mine"}, source="story", use_ai=True)
        with (
            patch.object(
                _module().llms, "chat_completion", side_effect=[RuntimeError(), "ok"]
            ) as call,
            patch.object(_module(), "log"),
        ):
            assist.suggestion()
            assist.review_note()
            self.assertEqual(call.call_count, 1)
            self.assertEqual(assist.status, "error")
            assist.retry()
            self.assertEqual(assist.suggestion(), "ok")
        self.assertEqual(assist.status, "suggested")

    def test_docassemble_lookups_are_not_treated_as_failures(self):
        assist = self.make({"story": "s"}, source="story", use_ai=True)
        with patch.object(
            _module().llms, "chat_completion", side_effect=NameError("x")
        ):
            with self.assertRaises(NameError):
                assist.suggestion()

    def test_translate_passes_the_language(self):
        assist = self.make(
            {"story": "hola"},
            task="translate",
            source="story",
            language="en",
            use_ai=True,
        )
        with patch.object(
            _module().llms, "translate_text", return_value="hello"
        ) as call:
            self.assertEqual(assist.suggestion(), "hello")
        self.assertEqual(call.call_args.kwargs["output_language"], "en")


class TestStructured(AIAssistTestCase):
    def test_extract_only_returns_declared_fields(self):
        assist = self.make(
            {"notice": "Hearing on May 1"},
            task="extract",
            source="notice",
            outputs={"hearing_date": "The hearing date"},
            use_ai=True,
        )
        with patch.object(
            _module().llms,
            "extract_fields_from_text",
            return_value={"hearing_date": "2026-05-01", "evil": "x", "nested": {}},
        ) as call:
            self.assertEqual(assist.suggestion("hearing_date"), "2026-05-01")
            self.assertEqual(assist.suggestion("evil"), "")
            self.assertEqual(assist.suggestion(), "")
        self.assertEqual(call.call_count, 1)
        self.assertEqual(call.call_args.args[1], {"hearing_date": "The hearing date"})

    def test_extract_ignores_values_that_are_not_scalars(self):
        assist = self.make(
            {"notice": "n"},
            task="extract",
            source="notice",
            outputs={"court": "Court"},
            use_ai=True,
        )
        with patch.object(
            _module().llms, "extract_fields_from_text", return_value={"court": ["a"]}
        ):
            self.assertEqual(assist.suggestion("court"), "")

    def test_classify_only_returns_a_declared_choice(self):
        assist = self.make(
            {"story": "s"},
            task="classify",
            source="story",
            choices={"eviction": "Eviction", "repairs": "Repairs"},
            use_ai=True,
        )
        with patch.object(_module().llms, "classify_text", return_value="other"):
            self.assertEqual(assist.suggestion(), "")
        assist2 = self.make(
            {"story": "s"},
            task="classify",
            source="story",
            choices={"eviction": "Eviction"},
            use_ai=True,
        )
        with patch.object(_module().llms, "classify_text", return_value="eviction"):
            self.assertEqual(assist2.suggestion(), "eviction")

    def test_unknown_task_is_rejected(self):
        with self.assertRaises(ValueError):
            _module().AIAssist("assist", task="run_anything")


class TestGoal(AIAssistTestCase):
    def test_goal_synthesizes_after_the_follow_ups(self):
        assist = self.make(
            {"story": "it happened"},
            task="goal",
            source="story",
            rubric="When and where",
            question_limit=2,
            use_ai=True,
        )
        self.assertEqual(assist.followups.question_limit, 2)
        self.assertEqual(assist.followups.rubric, "When and where")
        with (
            patch.object(type(assist.followups), "gather", return_value=True),
            patch.object(
                type(assist.followups),
                "synthesize_draft_response",
                return_value="It happened on Monday.",
            ),
        ):
            assist.followups.append(object())
            self.assertEqual(assist.suggestion(), "It happened on Monday.")
        self.assertEqual(assist.followups.initial_draft, "it happened")


if __name__ == "__main__":
    unittest.main()
