"""One AI-assisted question: the person answers, AI helps, the person reviews.

An `AIAssist` object holds the settings and the runtime state for a single
assisted answer. The interview itself keeps two ordinary questions: the one
that collects the input and the one that shows the suggestion in editable
fields. `ai_assist.yml` supplies everything between them: permission, the
call to the AI service, and what happens when the person declines or the
service fails.

The object never assigns interview variables. Its suggestions are only
defaults on the review screen, so the person's edited answer is what the
interview keeps.
"""

import hashlib
import json
from typing import Any, Dict, List, Optional, Union

from docassemble.base.util import (
    DAFile,
    DAFileList,
    DAObject,
    log,
    value,
)

from . import llms

__all__ = ["AIAssist", "AIAssistFollowUps", "AI_ASSIST_TASKS"]

# Each task's output shape: "text" fills one text area, "fields" fills
# several typed fields, and "choice" picks one of the author's choices.
AI_ASSIST_TASKS: Dict[str, str] = {
    "rewrite": "text",
    "goal": "text",
    "summarize": "text",
    "translate": "text",
    "prompt": "text",
    "extract": "fields",
    "extract_file": "fields",
    "classify": "choice",
}

_PURPOSES = {
    "rewrite": "organize your answer and make it easier to read",
    "goal": "ask you a few follow-up questions so your answer is complete",
    "summarize": "write a short summary of your answer",
    "translate": "translate your answer",
    "prompt": "help with your answer",
    "extract": "find the information we need in what you gave us",
    "extract_file": "find the information we need in your document",
    "classify": "suggest the choice that fits best",
}

_REWRITE_INSTRUCTIONS = (
    "Rewrite the user's text so it is clear, well organized and easy to read. "
    "Keep the user's voice and point of view. Do not add facts, names, dates "
    "or amounts that are not in the text. Reply with the rewritten text only."
)

_SUMMARIZE_INSTRUCTIONS = (
    "Summarize the user's text in a few plain sentences. Do not add facts "
    "that are not in the text. Reply with the summary only."
)


class AIAssist(DAObject):
    """Settings and state for one AI-assisted answer.

    Attributes:
        task (str): One of `AI_ASSIST_TASKS`. Defaults to "rewrite".
        source (str): Name of the variable that holds the person's input,
            such as "incident_description". Read when the AI runs.
        inputs (List[str]): Names of more variables to send along with
            `source`, for "prompt" and "summarize".
        instructions (str): The prompt for "prompt"; extra instructions for
            every other task. For "goal" they shape the answer written from
            the follow-up questions.
        outputs (Dict[str, str]): For "extract" and "extract_file", maps each
            destination variable name to a description of what to find.
        choices (Dict[str, str]): For "classify", maps each choice value to a
            description.
        language (str): For "translate", the language to translate into, as
            an ISO 639 code. Defaults to "en".
        rubric (str): For "goal", what a complete answer includes.
        initial_question (str): For "goal", the question the person answered.
        question_limit (int): For "goal", the most follow-up questions to ask.
            Defaults to 3.
        model (str): A model to use instead of the server's default.
        ask_permission (bool): Ask before sending anything to the AI service.
            Defaults to True.
        purpose (str): Finishes "AI can ..." on the permission screen.
        use_ai (bool): The person's answer on the permission screen.
        status (str): "suggested", "declined", "unavailable" or "error"
            after `run()`.

    Example:
        ```yaml
        include:
          - docassemble.ALToolbox:ai_assist.yml
        ---
        objects:
          - incident_ai: AIAssist.using(task="rewrite", source="incident_description")
        ---
        question: Review your description
        subquestion: ${ incident_ai.review_note() }
        fields:
          - no label: incident_narrative
            datatype: area
            default: ${ incident_ai.suggestion() }
        ```
    """

    _result: Any
    _status_of_result: str

    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)
        defaults: Dict[str, Any] = {
            "task": "rewrite",
            "source": "",
            "inputs": [],
            "instructions": "",
            "outputs": {},
            "choices": {},
            "language": "en",
            "rubric": "",
            "initial_question": "",
            "question_limit": 3,
            "model": None,
            "ask_permission": True,
            "purpose": "",
        }
        for name, default in defaults.items():
            if not hasattr(self, name):
                setattr(self, name, default)
        if self.task not in AI_ASSIST_TASKS:
            raise ValueError(f"Unknown AI assist task: {self.task!r}")
        if self.task == "goal" and not hasattr(self, "followups"):
            self.initializeAttribute(
                "followups",
                AIAssistFollowUps.using(
                    custom_instructions=self.instructions or "",
                    rubric=self.rubric
                    or "The response fully answers the question that was asked.",
                    initial_question=self.initial_question or "Tell us more.",
                    question_limit=int(self.question_limit),
                    **({"model": self.model} if self.model else {}),
                ),
            )

    @property
    def output_kind(self) -> str:
        """ "text", "fields" or "choice"."""
        return AI_ASSIST_TASKS[self.task]

    def ai_available(self) -> bool:
        """True when the server has an AI service configured."""
        return llms.client is not None

    def permission_purpose(self) -> str:
        return self.purpose or _PURPOSES[self.task]

    def permission_data(self) -> str:
        """Names what goes to the AI service, for the permission screen."""
        if self.task == "extract_file":
            return "The document you uploaded"
        if self.inputs:
            return "Your answer and some of your earlier answers"
        if self.task == "goal":
            return "Your answer and your answers to the follow-up questions"
        return "Your answer"

    # -- Reading the person's input --------------------------------------

    def source_value(self) -> Any:
        """The source variable's value, asking for it if necessary."""
        return value(self.source)

    def _input_text(self) -> str:
        text = _as_text(self.source_value())
        if not self.inputs:
            return text
        parts = [text]
        for name in self.inputs:
            parts.append(f"{name}:\n{_as_text(value(name))}")
        return "\n\n".join(parts)

    # -- Running the AI ----------------------------------------------------

    def _fingerprint(self, text: str) -> str:
        settings = [
            self.task,
            text,
            self.instructions,
            self.outputs,
            self.choices,
            self.language,
            self.rubric,
            self.model,
        ]
        if self.task == "extract_file":
            settings.append(_file_identity(self.source_value()))
        blob = json.dumps(settings, sort_keys=True, default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def run(self) -> Any:
        """Call the AI service once for the current input and settings.

        Gets the person's input, then asks for `use_ai`: the permission
        screen says the answer will be sent, so it has to follow the answer.
        Returns the raw, unvalidated result, or None when the person declined,
        no service is configured, or the call failed. Remembers the result, so
        showing the review screen again, going back, or resuming the session
        doesn't repeat the call. Changing the input or the settings does.
        """
        if self.task in ("goal", "extract_file"):
            self.source_value()
            text = ""
        else:
            text = self._input_text()
        if not self.use_ai:
            self.status = "declined" if self.ai_available() else "unavailable"
            return None
        if self.task == "goal":
            # The follow-up list asks its questions while it gathers, so it
            # has its own record of what has run.
            return self._run_goal()
        fingerprint = self._fingerprint(text)
        if getattr(self, "_fingerprint_of_result", None) == fingerprint:
            # A failure is remembered too: retrying on every page load would
            # make each screen slow and could repeat a paid call.
            self.status = self._status_of_result
            return self._result
        try:
            result = self._call(text)
        except Exception as err:  # A failed call must never stop the interview.
            if _interview_flow(err):
                raise
            self._failed(err)
            result = None
        else:
            self.status = "suggested"
        self._result = result
        self._fingerprint_of_result = fingerprint
        self._status_of_result = self.status
        return result

    def retry(self) -> None:
        """Forget the last result, so the next `run()` calls the AI again."""
        for name in ("_result", "_fingerprint_of_result", "_status_of_result"):
            if hasattr(self, name):
                delattr(self, name)

    def _call(self, text: str) -> Any:
        model = self.model or None
        extra = self.instructions or ""
        if self.task == "rewrite":
            return llms.chat_completion(
                system_message=_join(_REWRITE_INSTRUCTIONS, extra),
                user_message=text,
                model=model,
            )
        if self.task == "summarize":
            return llms.chat_completion(
                system_message=_join(_SUMMARIZE_INSTRUCTIONS, extra),
                user_message=text,
                model=model,
            )
        if self.task == "prompt":
            return llms.chat_completion(
                system_message=extra or "Help the user with their answer.",
                user_message=text,
                model=model,
            )
        if self.task == "translate":
            return llms.translate_text(
                text,
                output_language=self.language or "en",
                custom_instructions=extra,
                model=model,
            )
        if self.task == "classify":
            if not extra:
                return llms.classify_text(text, dict(self.choices), model=model)
            # classify_text takes no instructions, so the same request is made
            # here with the author's instructions added to the system message.
            return llms.chat_completion(
                system_message=_join(
                    "You are an expert annotator. Given a user's message, "
                    "respond with only the key of the category it fits:\n"
                    + json.dumps(dict(self.choices), ensure_ascii=False),
                    extra,
                    'If the text fits no category, respond with "null".',
                ),
                user_message=text,
                model=model,
                temperature=0,
            )
        if self.task == "extract":
            return llms.extract_fields_from_text(
                _join(extra, text) if extra else text,
                dict(self.outputs),
                model=model,
            )
        if self.task == "extract_file":
            return llms.extract_fields_from_file(
                self.source_value(),
                dict(self.outputs),
                llm_hint=extra,
                model=model,
            )
        raise ValueError(f"Unknown AI assist task: {self.task!r}")

    def _run_goal(self) -> Optional[str]:
        followups = self.followups
        source_text = _as_text(self.source_value())
        if getattr(self, "_goal_source", None) != source_text:
            # A changed answer starts the follow-up questions over.
            if getattr(self, "_goal_source", None) is not None:
                followups.clear()
                followups.reset_gathered()
                for name in (
                    "there_are_any",
                    "there_is_another",
                    "_satisfied",
                    "ai_failed",
                ):
                    if hasattr(followups, name):
                        delattr(followups, name)
                self.retry()
            followups.initial_draft = source_text
            self._goal_source = source_text
        try:
            followups.gather()  # Asks each follow-up question in turn.
        except Exception as err:
            if _interview_flow(err):
                raise
            self._failed(err)
            return None
        if getattr(followups, "ai_failed", False):
            # A follow-up question could not be written; the person still
            # reviews an answer built from what they have said so far.
            self.status = "error"
            return None
        # The answers to the follow-up questions are part of the key, so an
        # edited reply reaches the review screen.
        fingerprint = json.dumps(
            [source_text] + [_reply_text(item) for item in followups.elements],
            default=str,
        )
        if getattr(self, "_fingerprint_of_result", None) == fingerprint:
            self.status = self._status_of_result
            return self._result
        result: Optional[str] = None
        try:
            if len(followups):
                result = followups.synthesize_draft_response()
            else:
                result = source_text
        except Exception as err:
            if _interview_flow(err):
                raise
            self._failed(err)
        else:
            self.status = "suggested"
        self._result = result
        self._fingerprint_of_result = fingerprint
        self._status_of_result = self.status
        return result

    def _failed(self, err: Exception) -> None:
        # Only the class name: provider errors can quote the person's input.
        log(f"AIAssist {self.instanceName} failed: {err.__class__.__name__}")
        self.status = "error"

    # -- Values for the review screen ----------------------------------------

    def suggestion(self, name: Optional[str] = None) -> Any:
        """The suggested value to show on the review screen.

        Without `name`, the suggested text (or choice) for a one-answer task.
        With `name`, the suggested value for that destination variable of an
        extraction. Falls back to the person's own input for text tasks and to
        an empty value otherwise, so the review screen always works.
        """
        result = self.run()
        kind = self.output_kind
        if kind == "fields":
            if name is None or name not in self.outputs:
                return ""
            if not isinstance(result, dict):
                return ""
            found = result.get(name)
            return found if isinstance(found, (str, int, float, bool)) else ""
        if kind == "choice":
            return result if result in self.choices else ""
        if isinstance(result, str) and result.strip():
            return result.strip()
        if self.task in ("rewrite", "goal", "translate"):
            return _as_text(self.source_value())
        return ""

    def review_note(self) -> str:
        """One sentence for the review screen that says where the values came from."""
        self.run()
        status = getattr(self, "status", "")
        if status == "suggested" and self.output_kind == "fields":
            return (
                "AI filled in the answers below. Check them and change "
                "anything that is not right."
            )
        if status == "suggested":
            return (
                "AI suggested the answer below. Check it and change anything "
                "that is not right."
            )
        if status == "error":
            return "We could not get help from AI right now. Enter your answer below."
        return ""


class AIAssistFollowUps(llms.GoalOrientedQuestionList):
    """The follow-up questions of an AIAssist with task "goal".

    The list's own code blocks call the AI service while docassemble gathers
    it, outside any code in AIAssist. Here a failed call ends the follow-up
    questions instead of the interview: `ai_failed` is set and the person
    goes on to review what they have said so far.
    """

    custom_instructions: str

    def need_more_questions(self) -> bool:
        try:
            return super().need_more_questions()
        except Exception as err:
            if _interview_flow(err):
                raise
            log(f"AIAssist follow-up failed: {err.__class__.__name__}")
            self.ai_failed = True
            return False

    def get_next_question(self) -> Optional[Union[str, Dict[str, Any]]]:
        try:
            return super().get_next_question()
        except Exception as err:
            if _interview_flow(err):
                raise
            log(f"AIAssist follow-up failed: {err.__class__.__name__}")
            self.ai_failed = True
            return "Is there anything else you want to add?"

    def synthesize_draft_response(self) -> str:
        if not getattr(self, "custom_instructions", ""):
            return super().synthesize_draft_response()
        messages = [
            {"role": "assistant", "content": self.initial_question},
            {"role": "user", "content": self.initial_response_as_text()},
        ]
        for item in self.elements:
            question = item.question
            if isinstance(question, dict):
                question = question.get("question_text", "Follow-up question")
            messages.append({"role": "assistant", "content": str(question)})
            messages.append({"role": "user", "content": item.response_as_text()})
        return llms.synthesize_user_responses(
            custom_instructions=self.custom_instructions,
            messages=messages,
            model=self.model,
            user_language=self.user_language,
        )


def _reply_text(item: Any) -> str:
    try:
        return item.response_as_text()
    except Exception:  # An unanswered follow-up has no reply yet.
        return ""


def _interview_flow(err: Exception) -> bool:
    """True for the exceptions docassemble uses to ask a question or run code.

    Those have to propagate; catching one would stop the interview from
    asking for the variable it needs.
    """
    if isinstance(err, (NameError, AttributeError, IndexError, KeyError)):
        return True
    return type(err).__module__.startswith("docassemble.")


def _as_text(item: Any) -> str:
    if item is None:
        return ""
    if isinstance(item, (DAFile, DAFileList)):
        return ""
    return str(item)


def _file_identity(item: Any) -> List[Any]:
    files = item.elements if isinstance(item, DAFileList) else [item]
    return [getattr(f, "number", None) for f in files]


def _join(*parts: str) -> str:
    return "\n\n".join(part for part in parts if part)
