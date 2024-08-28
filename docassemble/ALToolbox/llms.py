from typing import Any, Dict, List, Optional, Union
import keyword
import os
import json
import tiktoken
from openai import OpenAI
import docassemble.base.util
from docassemble.base.util import (
    get_config,
    log,
    define,
    DAList,
    DAObject,
    DADict,
    get_config,
)

__all__ = [
    "chat_completion",
    "extract_fields_from_text",
    "match_goals_from_text",
    "classify_text",
    "synthesize_user_responses",
    "define_fields_from_dict",
    "GoalSatisfactionList",
    "IntakeQuestionList",
]

if os.getenv("OPENAI_API_KEY"):
    client: Optional[OpenAI] = OpenAI()
elif get_config("open ai"):
    api_key = get_config("open ai", {}).get("key")
    client = OpenAI(api_key=api_key)
else:
    client = None

always_reserved_names = set(
    docassemble.base.util.__all__
    + keyword.kwlist
    + list(dir(__builtins__))
    + [
        "_attachment_email_address",
        "_attachment_include_editable",
        "_back_one",
        "_checkboxes",
        "_datatypes",
        "_email_attachments",
        "_files",
        "_question_number",
        "_question_name",
        "_save_as",
        "_success",
        "_the_image",
        "_track_location",
        "_tracker",
        "_varnames",
        "_internal",
        "nav",
        "session_local",
        "device_local",
        "user_local",
        "url_args",
        "role_needed",
        "x",
        "i",
        "j",
        "k",
        "l",
        "m",
        "n",
        "role",
        "speak_text",
        "track_location",
        "multi_user",
        "menu_items",
        "allow_cron",
        "incoming_email",
        "role_event",
        "cron_hourly",
        "cron_daily",
        "cron_weekly",
        "cron_monthly",
        "_internal",
        "allow_cron",
        "cron_daily",
        "cron_hourly",
        "cron_monthly",
        "cron_weekly",
        "caller",
        "device_local",
        "loop",
        "incoming_email",
        "menu_items",
        "multi_user",
        "nav",
        "role_event",
        "role_needed",
        "row_index",
        "row_item",
        "self",
        "session_local",
        "speak_text",
        "STOP_RENDERING",
        "track_location",
        "url_args",
        "user_local",
        "user_dict",
        "allow_cron",
    ]
)


def chat_completion(
    system_message: Optional[str] = None,
    user_message: Optional[str] = None,
    openai_client: Optional[OpenAI] = None,
    openai_api: Optional[str] = None,
    temperature: float = 0.5,
    json_mode=False,
    model: str = "gpt-3.5-turbo",
    messages: Optional[List[Dict[str, str]]] = None,
    skip_moderation: bool = False,
) -> Union[List[Any], Dict[str, Any], str]:
    """A light wrapper on the OpenAI chat endpoint.

    Includes support for token limits, error handling, and moderation queue.

    It is also possible to specify an alternative model, and we support GPT-4-turbo's JSON
    mode.

    As of May 2024, json mode is available with both GPT-4-turbo and GPT-3.5-turbo (and no longer requires the 1106-preview versions)

    Args:
        system_message (str): The role the chat engine should play
        user_message (str): The message (data) from the user
        openai_client (Optional[OpenAI]): An OpenAI client object, optional. If omitted, will fall back to creating a new OpenAI client with the API key provided as an environment variable
        openai_api (Optional[str]): the API key for an OpenAI client, optional. If provided, a new OpenAI client will be created.
        temperature (float): The temperature to use for the GPT API
        json_mode (bool): Whether to use JSON mode for the GPT API. Requires the word `json` in the system message, but will add if you omit it.
        model (str): The model to use for the GPT API
        messages (Optional[List[Dict[str, str]]]): A list of messages to send to the chat engine. If provided, system_message and user_message will be ignored.
        skip_moderation (bool): Whether to skip the OpenAI moderation step, which may save seconds but risks banning your account. Only enable when you have full control over the inputs.

    Returns:
        A string with the response from the API endpoint or JSON data if json_mode is True
    """
    if not messages and not system_message:
        raise Exception(
            "You must provide either a system message and user message or a list of messages to use this function."
        )

    if (
        isinstance(system_message, str)
        and system_message
        and json_mode
        and not "json" in system_message.lower()
    ):
        log(
            f"Warning: { system_message } does not contain the word 'json' but json_mode is set to True. Adding 'json' silently"
        )
        system_message = f"{ system_message }\n\nRespond only with a JSON object"
    elif (
        messages
        and json_mode
        and not any("json" in message["content"].lower() for message in messages)
    ):
        log(
            f"Warning: None of the messages contain the word 'json' but json_mode is set to True. Adding 'json' silently"
        )
        messages.append(
            {"role": "system", "content": "Respond only with a JSON object"}
        )

    if not messages:
        assert isinstance(system_message, str)
        assert isinstance(user_message, str)
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ]
    if openai_api:
        openai_client = OpenAI(api_key=openai_api)
    else:
        if openai_client is None:
            if client:
                openai_client = client
            else:
                if get_config("open ai", {}).get("key"):
                    openai_client = OpenAI(api_key=get_config("open ai", {}).get("key"))
                else:
                    raise Exception(
                        "You need to pass an OpenAI client or API key to use this function, or the API key needs to be set in the environment or Docassemble configuration. Try adding a new section in your global config that looks like this:\n\nopen ai:\n    key: sk-..."
                    )

    encoding = tiktoken.encoding_for_model(model)

    encoding = tiktoken.encoding_for_model(model)
    token_count = len(encoding.encode(str(messages)))

    if model.startswith("gpt-4-"):  # E.g., "gpt-4-turbo"
        max_input_tokens = 128000
        max_output_tokens = 4096
    elif model.startswith("gpt-3.5-turbo"):
        max_input_tokens = 16385
        max_output_tokens = 4096
    else:
        max_input_tokens = 4096
        max_output_tokens = 4096 - token_count - 100  # small safety margin

    if token_count > max_input_tokens:
        raise Exception(
            f"Input to OpenAI is too long ({ token_count } tokens). Maximum is {max_input_tokens} tokens."
        )

    if not skip_moderation:
        moderation_response = openai_client.moderations.create(input=str(messages))
        if moderation_response.results[0].flagged:
            raise Exception(
                f"OpenAI moderation error: { moderation_response.results[0] }"
            )

    response = openai_client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"} if json_mode else None,  # type: ignore
        temperature=temperature,
        max_tokens=max_output_tokens,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )

    # check finish reason
    if response.choices[0].finish_reason != "stop":
        raise Exception(
            f"OpenAI did not finish processing the document. Finish reason: {response.choices[0].finish_reason}"
        )

    if json_mode:
        assert isinstance(response.choices[0].message.content, str)
        # log(f"JSON response is { response.choices[0].message.content }")
        return json.loads(response.choices[0].message.content)
    else:
        # log(f"Response is { response.choices[0].message.content }")
        return response.choices[0].message.content


def extract_fields_from_text(
    text: str,
    field_list: Dict[str, str],
    openai_client: Optional[OpenAI] = None,
    openai_api: Optional[str] = None,
    temperature: float = 0,
    model="gpt-3.5-turbo-1106",
) -> Dict[str, Any]:
    """Extracts fields from text.

    Args:
        text (str): The text to extract fields from
        field_list (Dict[str,str]): A list of fields to extract, with the key being the field name and the value being a description of the field

    Returns:
        A dictionary of fields extracted from the text
    """
    system_message = f"""
    The user message represents notes from an unstructured conversation. Review the notes and extract the following fields:
    
    ```
    {repr(field_list)}
    ```

    If a field cannot be defined from the notes, omit it from the JSON response.
    """

    result = chat_completion(
        system_message=system_message,
        user_message=text,
        model=model,
        openai_client=openai_client,
        openai_api=openai_api,
        temperature=temperature,
        json_mode=True,
    )
    assert isinstance(result, dict)
    return result


def match_goals_from_text(
    question: str,
    user_response: str,
    goals: Dict[str, str],
    openai_client: Optional[OpenAI] = None,
    openai_api: Optional[str] = None,
    temperature: float = 0,
    model="gpt-3.5-turbo-1106",
) -> Dict[str, Any]:
    """Reads a user's message and determines whether it meets a set of goals, with the help of an LLM.

    Args:
        text (str): The text to extract goals from
        field_list (Dict[str,str]): A list of goals to extract, with the key being the goal name and the value being a description of the goal

    Returns:
        A dictionary of fields extracted from the text
    """
    system_message = f"""
    The user message represents an answer to the following question:

    ```
    { question }
    ```
    
    Review the answer to determine if it meets the
    following goals:
    
    ```
    {repr(goals)}
    ```

    Reply with a JSON object that includes only the satisfied goals in the following format:
    
    ```
    {{
        "goal_name": true,
    }}
    ```

    If there are no satisfied goals, return an empty dictionary.
    """
    results = chat_completion(
        system_message=system_message,
        user_message=user_response,
        model=model,
        openai_client=openai_client,
        openai_api=openai_api,
        temperature=temperature,
        json_mode=True,
    )
    assert isinstance(results, dict)
    return results


def classify_text(
    text: str,
    choices: Dict[str, str],
    default_response: str = "null",
    openai_client: Optional[OpenAI] = None,
    openai_api: Optional[str] = None,
    temperature: float = 0,
    model="gpt-3.5-turbo-1106",
) -> str:
    """Given a text, classify it into one of the provided choices with the assistance of a large language model.

    Args:
        text (str): The text to classify
        choices (Dict[str,str]): A list of choices to classify the text into, with the key being the choice name and the value being a description of the choice
        openai_client (Optional[OpenAI]): An OpenAI client object, optional. If omitted, will fall back to creating a new OpenAI client with the API key provided as an environment variable
        openai_api (Optional[str]): the API key for an OpenAI client, optional. If provided, a new OpenAI client will be created.
        temperature (float): The temperature to use for GPT. Defaults to 0.
        model (str): The model to use for the GPT API
    """
    system_prompt = f"""You are an expert annotator. Given a user's message, respond with the classification into one of the following categories:
    ```
    { repr(choices) }
    ```

    If the text cannot be classified, respond with "{ default_response }".
    """
    results = chat_completion(
        system_message=system_prompt,
        user_message=text,
        model=model,
        openai_client=openai_client,
        openai_api=openai_api,
        temperature=temperature,
        json_mode=False,
    )
    assert isinstance(results, str)
    return results


def synthesize_user_responses(
    messages: List[Dict[str, str]],
    custom_instructions: Optional[str] = "",
    openai_client: Optional[OpenAI] = None,
    openai_api: Optional[str] = None,
    temperature: float = 0,
    model: str = "gpt-3.5-turbo-1106",
) -> str:
    """Given a first draft and a series of follow-up questions and answers, use an LLM to synthesize the user's responses
    into a single, coherent reply.

    Args:
        custom_instructions (str): Custom instructions for the LLM to follow in constructing the synthesized response
        initial_draft (str): The initial draft of the response from the user
        messages (List[Dict[str, str]]): A list of questions from the LLM and responses from the user
        openai_client (Optional[OpenAI]): An OpenAI client object, optional. If omitted, will fall back to creating a new OpenAI client with the API key provided as an environment variable
        openai_api (Optional[str]): the API key for an OpenAI client, optional. If provided, a new OpenAI client will be created.
        temperature (float): The temperature to use for GPT. Defaults to 0.
        model (str): The model to use for the GPT API
    """
    system_message = f"""You are a helpful editor engaging in a conversation with the user. You are helping a user write a response to an open-ended question.
    You will see the user's initial draft, followed by a series of questions and answers that clarified additional content to include
    in the response.

    {custom_instructions}
    """

    ending_message = """
    Now that you have helped the user add more details, synthesize the response into a single coherent answer
    to the first question. It will rephrase and incorporate the follow-up questions if needed to add context 
    and clarity to the final response. You will write a reply in the user's voice. It will use the same pronouns,
    such as "I" and as many of the user's words as possible. It will be addressed to a third party
    reading the conversation and in the voice and style of the user.
    """
    results = chat_completion(
        messages=[
            {"role": "system", "content": system_message},
        ]
        + messages
        + [
            {"role": "system", "content": ending_message},
        ],
        model=model,
        openai_client=openai_client,
        openai_api=openai_api,
        temperature=temperature,
        json_mode=False,
    )
    assert isinstance(results, str)
    return results


def define_fields_from_dict(
    field_dict: Dict[str, Any], fields_to_ignore: Optional[List] = None
) -> None:
    """Assigns the values in a dictionary of fields to the corresponding fields in a Docassemble interview.

    Docassemble and built-in keywords are never defined by this function. If fields_to_ignore is provided, those fields will also be ignored.

    Args:
        field_dict (Dict[str, Any]): A dictionary of fields to define, with the key being the field name and the value
            presumably taken from the output of extract_fields_from_text.
        fields_to_ignore (Optional[List]): A list of fields to ignore. Defaults to None. Should be used to ensure
            safety when defining fields from untrusted sources. E.g., ["user_is_logged_in"]

    Returns:
        None
    """
    if not isinstance(field_dict, dict):
        log("Field dict is not a dictionary.")
        return

    for field in field_dict:
        if field in always_reserved_names or (
            fields_to_ignore and field in fields_to_ignore
        ):
            continue
        define(field, field_dict[field])


class Goal(DAObject):
    """A class to represent a goal.

    Attributes:
        name (str): The name of the goal
        description (str): A description of the goal
        satisfied (bool): Whether the goal is satisfied
    """

    def response_satisfies_me_or_follow_up(
        self,
        messages: List[Dict[str, str]],
        openai_client: Optional[OpenAI] = None,
        model="gpt-3.5-turbo",
    ) -> str:
        """Returns the text of the next question to ask the user or the string "satisfied"
        if the user's response satisfies the goal.

        Args:
            response (str): The response to check

        Returns:
            True if the response satisfies the goal, False otherwise
        """
        system_message = f"""You are a good conversationalist who is helping to improve and get relevant and thoughtful information from a person. 
        Read the entire exchange with the user, in light of this goal: 
        ```{ self.description }```

        Respond with the exact text "satisfied" (and no other text) if the goal is satisfied. If the goal is not satisfied, 
        respond with a brief follow-up question that directs the user toward the goal. If they have already provided a partial 
        response, explain why and how they should expand on it.
        """

        results = chat_completion(
            messages=[
                {"role": "system", "content": system_message},
            ]
            + messages,
            openai_client=openai_client,
            model=model,
        )
        assert isinstance(results, str)
        return results

    def get_next_question(
        self,
        thread_so_far: List[Dict[str, str]],
        openai_client: Optional[OpenAI] = None,
        model="gpt-3.5",
    ) -> str:
        """Returns the text of the next question to ask the user."""

        system_instructions = f"""You are helping the user to satisfy this goal with their response: "{ self.description }". Ask a brief appropriate follow-up question that directs the user toward the goal. If they have already provided a partial response, explain why and how they should expand on it."""

        messages = [{"role": "system", "content": system_instructions}]
        results = chat_completion(
            messages=messages + thread_so_far,
            openai_client=openai_client,
            temperature=0.5,
            model=model,
        )
        assert isinstance(results, str)
        return results

    def __str__(self):
        return f'"{ self.name }": "{ self.description }"'


class GoalDict(DADict):
    """A class to represent a DADict of Goals."""

    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)
        self.object_type = Goal
        self.auto_gather = False

    def satisfied(self):
        """Returns True if all goals are satisfied, False otherwise."""
        return all(
            [
                goal.satisfied if hasattr(goal, "satisfied") else False
                for goal in self.values()
            ]
        )


class GoalQuestion(DAObject):
    """A class to represent a question about a goal.

    Attributes:
        goal (Goal): The goal the question is about
        question (str): The question to ask the user
        response (str): The user's response to the question
    """

    @property
    def complete(self):
        self.goal
        self.question
        self.response
        return True


class GoalSatisfactionList(DAList):
    """A class to help ask the user questions until all goals are satisfied.

    Uses an LLM to prompt the user with follow-up questions if the initial response isn't complete.
    By default, the number of follow-up questions is limited to 10.

    This can consume a lot of tokens, as each follow-up has a chance to send the whole conversation
    thread to the LLM.

    By default, this will use the OpenAI API key defined in the global configuration under this path:

    ```
    open ai:
        key: sk-...
    ```

    You can specify the path to an alternative configuration by setting the `openai_configuration_path` attribute.

    This object does NOT accept the key as a direct parameter, as that will be leaked in the user's answers.

    Attributes:
        goals (List[Goal]): The goals in the list, provided as a dictionary
        goal_list (GoalList): The list of Goals
        question_limit (int): The maximum number of follow-up questions to ask the user
        question_per_goal_limit (int): The maximum number of follow-up questions to ask the user per goal
        initial_draft (str): The initial draft of the user's response
        initial_question (str): The original question posed in the interview
    """

    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)
        self.object_type = GoalQuestion
        self.complete_attribute = "complete"

        if not hasattr(self, "question_limit"):
            self.question_limit = 10

        if not hasattr(self, "goal_dict"):
            self.initializeAttribute("goal_dict", GoalDict)

        if hasattr(self, "goals"):
            if isinstance(self.goals, dict):
                for goal in self.goals:
                    self.goal_dict.initializeObject(
                        goal["name"],
                        Goal.using(
                            name=goal["name"],
                            description=goal["description"],
                            satisfied=False,
                        ),
                    )
            elif isinstance(self.goals, list):
                for idx, goal in enumerate(self.goals):
                    self.goal_dict.initializeObject(
                        f"goal_{idx}",
                        Goal.using(
                            name=f"goal_{idx}", description=goal, satisfied=False
                        ),
                    )
            del self.goals
            self.goal_dict.gathered = True

        if not hasattr(self, "model"):
            self.model = "gpt-3.5-turbo-1106"

        if not hasattr(self, "question_per_goal_limit"):
            self.question_per_goal_limit = 3

    # def count_attempts(self, goal: Goal) -> int:
    #    """Returns the number of times the user has attempted to satisfy the given goal."""
    #    log("Counting attempts")
    #    return len([e for e in self.elements if e.goal == goal])

    def mark_satisfied_goals(self) -> None:
        """Marks goals as satisfied if the user's response satisfies the goal.
        This should be used as soon as the user gives their initial reply.

        Returns:
            None
        """
        extracted_fields = match_goals_from_text(
            self.initial_question,
            self.initial_draft,
            self.goal_dict,
            model=self.model,
        )
        for field in extracted_fields:
            if field in self.goal_dict and extracted_fields[field]:
                self.goal_dict[field].satisfied = True

    def keep_going(self):
        """Returns True if there is at least one unsatisfied goal and if the number of follow-up questions asked is less than the question limit, False otherwise."""
        if not self._get_next_unsatisfied_goal() or self.satisfied():
            return False
        return len(self.elements) < self.question_limit

    def need_more_questions(self):
        """Returns True if there is at least one unsatisfied goal, False otherwise.

        Also has the side effect of checking the user's most recent response to see if it satisfies the goal
        and updating the next question to be asked.
        """
        goal = self._get_next_unsatisfied_goal()
        if not goal:
            return False

        status = goal.response_satisfies_me_or_follow_up(
            messages=self._get_related_thread(goal),
            model=self.model,
        )

        # log(
        #     f"Checking if {goal} was satisfied by thread { self._get_related_thread(goal) }. Status is { status }"
        # )
        if status.strip().lower() == "satisfied":
            goal.satisfied = True
            # log(f"Goal { goal } was satisfied by the user's follow-up response")
            return self.need_more_questions()
        else:
            # log(f"Goal { goal } was not satisfied by the user's follow-up response")
            # log(f"Setting the next question to { status }.")
            self.next_question = status

        return self.keep_going()

    def satisfied(self):
        """Returns True if all goals are satisfied, False otherwise."""
        return self.goal_dict.satisfied()

    def _get_next_unsatisfied_goal(self) -> Optional[Goal]:
        """Returns the next unsatisfied goal."""
        next_goal = next((g for g in self.goal_dict.values() if not g.satisfied), None)
        # log(f"Next unsatisfied candidate goal is { next_goal }")

        # if next_goal and (self.count_attempts(next_goal) >= self.question_per_goal_limit):
        #    # Move on after 3 tries
        #    log(f"Moving on from { next_goal } after { self.question_per_goal_limit } tries")
        #    next_goal.satisfied = True
        #    new_goal = self._get_next_unsatisfied_goal()
        #    if new_goal:
        #        # update the question to reflect the new goal
        #        self.next_question = new_goal.get_next_question(self._get_related_thread(new_goal), model=self.model)
        #    return new_goal
        #
        # log(f"Next goal is { next_goal }")
        return next_goal

    def get_next_goal_and_question(self):
        """Returns the next unsatisfied goal, along with a follow-up question to ask the user, if relevant.

        Returns:
            A tuple of (Goal, str) where the first item is the next unsatisfied goal and the second item is the next question to ask the user, if relevant.
            If the user's response to the last question satisfied the goal, returns (None, None).
        """
        goal = self._get_next_unsatisfied_goal()

        if not goal:
            # log("No more unsatisfied goals")
            return None, None
        else:
            # This should have been set by the last call to there_is_another
            # unless we're just starting out with the first question
            if not (hasattr(self, "next_question") and self.next_question):
                # log("No question was set by call to there_is_another, getting one now")
                self.next_question = goal.get_next_question(
                    self._get_related_thread(goal),
                    model=self.model,
                )
            else:
                log(
                    f"Using next question { self.next_question } which was previously set"
                )
            temp_question = self.next_question
            del self.next_question
            return goal, temp_question

    def _get_related_thread(self, goal: Goal) -> List[Dict[str, str]]:
        """Returns a list of messages (with corresponding role) related to the given goal.

        This is appropriate to pass to the OpenAI ChatCompletion APIs.

        Args:
            goal (Goal): The goal to get the related thread for

        Returns:
            A list of messages (with corresponding role) related to the given goal.
        """
        messages = [
            {"role": "assistant", "content": self.initial_question},
            {"role": "user", "content": self.initial_draft},
        ]
        for element in self.elements:
            # TODO: see how this performs. It could save some tokens to skip the ones that aren't related to the current goal.
            # if element.goal != goal:
            #    continue
            messages.append({"role": "assistant", "content": element.question})
            messages.append({"role": "user", "content": element.response})

        return messages

    def synthesize_draft_response(self):
        """Returns a draft response that synthesizes the user's responses to the questions."""
        messages = [
            {"role": "assistant", "content": self.initial_question},
            {"role": "user", "content": self.initial_draft},
        ]
        for question in self.elements:
            messages.append({"role": "assistant", "content": question.question})
            messages.append({"role": "user", "content": question.response})
        return synthesize_user_responses(
            custom_instructions="",
            messages=messages,
            model=self.model,
        )

    def provide_feedback(self, feedback_prompt: str = ""):
        """Returns feedback to the user based on the goals they satisfied."""
        if not feedback_prompt:
            feedback_prompt = """
            You are a helpful instructor who is providing feedback to a student
            based on their reflection and response to any questions you asked.

            Review the student's response and provide feedback on how well they
            addressed the goals you set out for them. If they met the goals but
            could dig deeper, offer specific feedback on how they could do so
            in their next reflection.
            """
        messages = [
            {"role": "assistant", "content": self.initial_question},
            {"role": "user", "content": self.initial_draft},
        ]
        for question in self.elements:
            messages.append({"role": "assistant", "content": question.question})
            messages.append({"role": "user", "content": question.response})

        messages.append({"role": "assistant", "content": feedback_prompt})

        return chat_completion(
            messages=messages,
            model=self.model,
        )


class IntakeQuestion(DAObject):
    """A class to represent a question in an LLM-assisted intake questionnaire.

    Attributes:
        question (str): The question to ask the user
        response (str): The user's response to the question
    """

    @property
    def complete(self):
        self.question
        self.response
        return True


class IntakeQuestionList(DAList):
    """
    Class to help create an LLM-assisted intake questionnaire.

    The LLM will be provided a free-form set of in/out criteria (like that
    provided to a phone intake worker), an initial draft question from the user,
    and then guide the user through a series of follow-up questions to gather only
    enough information to determine if the user meets the criteria.

    In/out criteria are often pretty short, so we do not make or support
    embeddings at the moment.

    Attributes:
        criteria (Dict[str, str]): A dictionary of criteria to match, indexed by problem type
        problem_type_descriptions (Dict[str, str]): A dictionary of descriptions of the problem types
        problem_type (str): The type of problem to match. E.g., a unit/department inside the law firm
        initial_problem_description (str): The initial description of the problem from the user
        initial_question (str): The original question posed in the interview
        question_limit (int): The maximum number of follow-up questions to ask the user. Defaults to 10.
        model (str): The model to use for the GPT API. Defaults to gpt-4-turbo. gpt-3.5 is not smart enough
        llm_role (str): The role the LLM should play. Allows you to customize the script the LLM uses to guide the user.
            We have provided a default script that should work for most intake questionnaires.
        llm_user_qualifies_prompt (str): The prompt to use to determine if the user qualifies. We have provided a default prompt.
        out_of_questions (bool): Whether the user has run out of questions to answer
        qualifies (bool): Whether the user qualifies based on the criteria
    """

    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)
        self.object_type = IntakeQuestion
        self.complete_attribute = "complete"
        self.out_of_questions = False
        self.qualifies = None

        if not hasattr(self, "model"):
            self.model = "gpt-4-turbo"

        if not hasattr(self, "question_limit"):
            self.question_limit = 10

        if not hasattr(self, "llm_role"):
            self.llm_role = """
            You are an expert intake worker at a law firm. You want to quickly help the client understand if
            the problem they have is one that your firm can help with. You will ask a series of questions to
            determine if the client meets the criteria for your services. You will only ask questions that are
            necessary to determine if the client meets the criteria. If the client does not meet the criteria,
            you will stop asking questions and let them know as soon as possible.
            """
        if not hasattr(self, "problem_type_descriptions"):
            self.problem_type_descriptions = {
                "housing": "problems with housing, such as getting housing or a housing subsidy, eviction or unsafe living conditions",
                "family": "problems with family law, such as divorce, child custody, guardianship, name changes, or domestic violence",
                "employment": "problems with employment law, such as discrimination, wrongful termination, or wage theft",
                "immigration": "problems with immigration, such as getting asylum, temporary protected status, a visa, green card, or citizenship, or avoiding deportation",
                "consumer": "problems with consumer law, such as debt collection, credit reporting, or identity theft",
                "welfare": "problems with public benefits, such as getting food stamps or cash assistance",
                "veterans": "problems with veterans benefits, such as getting disability benefits, appealing a denial, or getting help with housing",
                "health": "problems with health care, such as getting health insurance, Medicaid, or Medicare, or dealing with medical debt",
                "education": "problems with education, such as getting special education services, dealing with school discipline, or getting student loans",
                "criminal": "problems with criminal law, such as getting a public defender, expunging a criminal record, or avoiding deportation",
                "traffic": "problems with driving related rights, such as getting a ticket dismissed, avoiding points on your license, or avoiding a license suspension",
                "torts": "problems with personal injury law, such as getting compensation for an injury, dealing with insurance companies, or suing someone for negligence",
                "disaster": "problems with disaster recovery, such as getting FEMA assistance, dealing with insurance companies, or getting help with rebuilding",
                "elder": "problems with elder law, such as getting help with guardianship, elder abuse, or long-term care",
                "environmental": "problems with environmental law, such as getting help with pollution, land use, or environmental justice",
                "business": "problems with business law, such as forming a business, dealing with contracts, or getting help with a business dispute",
                "tax": "problems with tax law, such as getting help with tax debt, dealing with the IRS, or getting help with tax preparation",
            }

    def _classify_problem_type(self):
        """Classifies the problem type based on the user's initial description."""
        return classify_text(
            self.initial_problem_description,
            self.problem_type_descriptions,
            model=self.model,
        )

    def _keep_going(self):
        """Returns True if the user can and needs to answer more questions, False otherwise.

        It respects the limit defined by self.question_limit.

        As a side effect, checks if the user has run out of questions to answer and updates the next question to be asked
        to be a closing message instead of a follow-up.
        """
        self.out_of_questions = len(self.elements) >= self.question_limit
        if self.out_of_questions:
            self.next_question = self._ran_out_of_questions_message()
            return False
        return True

    def need_more_questions(self):
        """Returns True if the user needs to answer more questions, False otherwise.

        Also has the side effect of checking the user's most recent response to see if it satisfies the criteria
        and updating both the next question to be asked and the current qualification status.
        """
        status = self._current_qualification_status()
        self.qualifies = status["qualifies"]
        self.next_question = status["narrative"]
        if not (status["qualifies"] is None):
            return False
        return self._keep_going()

    def _current_qualification_status(self):
        """Returns a dictionary with the user's current qualification status"""
        if not hasattr(self, "problem_type"):
            self.problem_type = self._classify_problem_type()

        criteria = self.criteria.get(self.problem_type, None)
        if not criteria:
            return False

        qualification_prompt = f"""
        Based on the qualification criteria,
        assess whether the user meets at least the *minimum* criteria for the following problem type:
        `{ self.problem_type }`.

        Rely only on the information about in/out criteria that are provided.

        You can have one of 3 possible responses:

        1. The user qualifies (true)
        2. The user does not qualify (false)
        3. You need more information to determine if the user qualifies (null)

        Use direct address. Provide a qualified answer in the narrative, without guaranteeing
        the user will be accepted as a client. All narratives should use plain language at a 6th grade reading level, and
        are written in the active voice.

        Answer in the form of a JSON object like this:

        Example:
        {{"qualifies": null,
        "narrative": "Is your eviction case scheduled for the judge to hear in the next 10 days?"}} # if more information is needed

        Example:
        {{"qualifies": true,
         "narrative": "You probably qualify because you are facing eviction within the next 10 days."}}

        Example:
        {{"qualifies" false,
        "narrative": "You probably do not qualify because your divorce does not involve children and you are not facing domestic violence."}}
        """

        criteria_prompt = f"The only criteria you will rely on in your answer are as follows: \n```{ criteria }\n```"

        results = chat_completion(
            messages=[
                {"role": "system", "content": self.llm_role},
                {"role": "system", "content": qualification_prompt},
                {"role": "system", "content": criteria_prompt},
            ]
            + self._get_thread(),
            model=self.model,
            json_mode=True,
        )

        if isinstance(results, dict):
            return results

        raise Exception(f"Unexpected response from LLM: { results }")

    def _get_thread(self):
        """Returns a list of messages (with corresponding role) related to the given goal."""
        messages = [
            {"role": "assistant", "content": self.initial_question},
            {"role": "user", "content": self.initial_problem_description},
        ]

        for element in self.elements:
            messages.append({"role": "assistant", "content": element.question})
            messages.append({"role": "user", "content": element.response})

        return messages

    def _ran_out_of_questions_message(self):
        """Returns a message to display when the user has run out of questions to answer."""
        summary_prompt = """
        Explain to the user that you have asked all the questions you need to determine if they qualify for services
        and you still do not have a response. Explain why the answer that they gave was still incomplete.
        """
        return chat_completion(
            messages=[
                {"role": "system", "content": self.llm_role},
            ]
            + self._get_thread()
            + [
                {"role": "system", "content": summary_prompt},
            ],
            model=self.model,
            json_mode=False,
        )
