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
]

if os.getenv("OPENAI_API_KEY"):
    client: Optional[OpenAI] = OpenAI()
else:
    api_key = get_config("open ai", {}).get("key")
    client = OpenAI(api_key=api_key)

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
    system_message: str,
    user_message: str,
    openai_client: Optional[OpenAI] = None,
    openai_api: Optional[str] = None,
    temperature: float = 0.5,
    json_mode=False,
    model: str = "gpt-3.5-turbo",
    messages: Optional[List[Dict[str, str]]] = None,
) -> Union[List[Any], Dict[str, Any], str]:
    """A light wrapper on the OpenAI chat endpoint.

    Includes support for token limits, error handling, and moderation queue.

    It is also possible to specify an alternative model, and we support GPT-4-turbo's JSON
    mode.

    As of today (1/2/2024) JSON mode requires the model to be set to "gpt-4-1106-preview" or "gpt-3.5-turbo-1106"

    Args:
        system_message (str): The role the chat engine should play
        user_message (str): The message (data) from the user
        openai_client (Optional[OpenAI]): An OpenAI client object, optional. If omitted, will fall back to creating a new OpenAI client with the API key provided as an environment variable
        openai_api (Optional[str]): the API key for an OpenAI client, optional. If provided, a new OpenAI client will be created.
        temperature (float): The temperature to use for the GPT-4-turbo API
        json_mode (bool): Whether to use JSON mode for the GPT-4-turbo API

    Returns:
        A string with the response from the API endpoint or JSON data if json_mode is True
    """
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
                        "You need to pass an OpenAI client or API key to use this function, or the API key needs to be set in the environment."
                    )

    encoding = tiktoken.encoding_for_model(model)

    encoding = tiktoken.encoding_for_model(model)
    if messages:
        token_count = len(encoding.encode(str(messages)))
    else:
        token_count = len(encoding.encode(system_message + user_message))

    if model.startswith("gpt-4-"):  # E.g., "gpt-4-1106-preview"
        max_input_tokens = 128000
        max_output_tokens = 4096
    elif (
        model == "gpt-3.5-turbo-1106"
    ):  # TODO: when gpt-3.5-turbo-0613 is deprecated we can expand our check
        max_input_tokens = 16385
        max_output_tokens = 4096
    else:
        max_input_tokens = 4096
        max_output_tokens = 4096 - token_count - 100  # small safety margin

    if token_count > max_input_tokens:
        raise Exception(
            f"Input to OpenAI is too long ({ token_count } tokens). Maximum is {max_input_tokens} tokens."
        )

    moderation_response = openai_client.moderations.create(
        input=system_message + user_message
    )
    if moderation_response.results[0].flagged:
        raise Exception(f"OpenAI moderation error: { moderation_response.results[0] }")

    response = openai_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
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
        return json.loads(response.choices[0].message.content)
    else:
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

    return chat_completion(
        system_message=system_message,
        user_message=text,
        model=model,
        openai_client=openai_client,
        openai_api=openai_api,
        temperature=temperature,
        json_mode=True,
    )


def match_goals_from_text(
    text: str,
    goals: List[str],
    openai_client: Optional[OpenAI] = None,
    openai_api: Optional[str] = None,
    temperature: float = 0,
    model="gpt-3.5-turbo-1106",
) -> Dict[str, Any]:
    """Read's a user's message and determines whether it meets a set of goals, with the help of an LLM.

    Args:
        text (str): The text to extract goals from
        field_list (Dict[str,str]): A list of goals to extract, with the key being the goal name and the value being a description of the goal

    Returns:
        A dictionary of fields extracted from the text
    """
    system_message = f"""
    The user message represents an answer to an open-ended question, as well as follow-up questions and answers. Review the answer to determine if it meets the
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

    return chat_completion(
        system_message=system_message,
        user_message=text,
        model=model,
        openai_client=openai_client,
        openai_api=openai_api,
        temperature=temperature,
        json_mode=True,
    )


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
    return chat_completion(
        system_message=system_prompt,
        user_message=text,
        model=model,
        openai_client=openai_client,
        openai_api=openai_api,
        temperature=temperature,
        json_mode=False,
    )


def synthesize_user_responses(
    initial_draft: str,
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
    system_message = f"""You are a helpful editor. You are helping a user write a response to an open-ended question.
    You will see the user's initial draft, followed by a series of questions and answers that clarified additional content to include
    in the response. Synthesize the user's responses into a single, coherent response while matching the user's tone and without adding
    additional facts.

    {custom_instructions}
    """

    user_message = f"""
    Initial draft response from the user: 
    ```
    {initial_draft}

    Follow-up conversation thread:
    ```
    {repr(messages)}
    ```
    """

    return chat_completion(
        system_message=system_message,
        user_message=user_message,
        model=model,
        openai_client=openai_client,
        openai_api=openai_api,
        temperature=temperature,
        json_mode=False,
        messages=messages,
    )


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
        self, response: str, openai_client: Optional[OpenAI] = None
    ) -> bool:
        """Returns True if the response satisfies the goal, False otherwise.

        Args:
            response (str): The response to check

        Returns:
            True if the response satisfies the goal, False otherwise
        """
        system_message = f"""The user's message represents an answer to this 
        question: "{ self.description }". If the answer satisfies the goal,
        return the exact text "satisfied" with no other text. Otherwise, 
        return the text of a follow-up question that gets closer to the goal."""
        user_message = f"""```
        { response }
        ```"""
        return chat_completion(
            system_message=system_message,
            user_message=user_message,
            openai_client=openai_client,
        )

    def get_next_question(
        self,
        thread_so_far: List[Dict[str, str]],
        openai_client: Optional[OpenAI] = None,
        model="gpt-3.5",
    ) -> str:
        """Returns the text of the next question to ask the user."""

        system_instructions = f"""You are helping the user to satisfy this goal with their response: "{ self.description }". Ask a brief appropriate follow-up question that directs the user toward the goal."""

        messages = [{"system": system_instructions}]
        return chat_completion(
            messages=messages + thread_so_far,
            openai_client=openai_client,
            temperature=0.5,
            model=model,
        )

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

    pass


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
        initial_draft (str): The initial draft of the user's response
    """

    def init(self, *pargs, **kwargs):
        super().init(*pargs, **kwargs)
        self.object_type = GoalQuestion
        self.complete_attribute = [
            "goal",
            "question",
            "response",
        ]
        if not hasattr(self, "there_are_any"):
            self.there_are_any = True

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
            self.goal_dict.gathered = True

        if not hasattr(self, "model"):
            self.model = "gpt-3.5-turbo-1106"

    def mark_satisfied_goals(self, user_response: str) -> None:
        """Marks goals as satisfied if the user's response satisfies the goal.
        This should be used as soon as the user gives their initial reply.

        Args:
            user_response (str): The user's response to the question

        Returns:
            None
        """
        extracted_fields = match_goals_from_text(
            user_response,
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

    @property
    def there_is_another(self):
        """Returns True if there is at least one unsatisfied goal, False otherwise.

        Also has the side effect of checking the user's most recent response to see if it satisfies the goal.
        """
        goal = self._get_next_unsatisfied_goal()
        if not goal:
            return False
        
        status = goal.response_satisfies_me_or_follow_up(
            messages=self._get_related_thread(goal),
            model=self.model,
        )

        if status.trim().lower() == "satisfied":
            goal.satisfied = True
            return self.there_is_another
        else:
            self.next_question = status

        return self.keep_going()

    def satisfied(self):
        """Returns True if all goals are satisfied, False otherwise."""
        return self.goal_dict.satisfied()

    def _get_next_unsatisfied_goal(self):
        """Returns the next unsatisfied goal, starting with the goal of the most recently asked question if there is one."""
        if len(self.elements) and hasattr(self.elements[-1], "goal"):
            # Make sure the goal isn't already satisfied (But I don't think we can reach this branch)
            if not (
                hasattr(self.elements[-1].goal, "satisfied")
                and self.elements[-1].goal.satisfied
            ):
                return self.elements[-1].goal
        return next(
            (goal for goal in self.goal_dict.values() if not goal.satisfied), None
        )

    def get_next_goal_and_question(self):
        """Returns the next unsatisfied goal, along with a follow-up question to ask the user, if relevant.

        Returns:
            A tuple of (Goal, str) where the first item is the next unsatisfied goal and the second item is the next question to ask the user, if relevant.
            If the user's response to the last question satisfied the goal, returns (None, None).
        """
        goal = self._get_next_unsatisfied_goal()
        
        if not goal:
            return None, None
        else:
            # This should have been set by the last call to there_is_another
            if not (hasattr(self, "next_question") and self.next_question):
                self.next_question = goal.get_next_question(
                    self._get_related_thread(goal),
                    model=self.model,
                )
            return goal, self.next_question

    def _get_related_thread(self, goal: Goal) -> List[Dict[str, str]]:
        """Returns a list of messages (with corresponding role) related to the given goal.

        This is appropriate to pass to the OpenAI ChatCompletion APIs.

        Args:
            goal (Goal): The goal to get the related thread for

        Returns:
            A list of messages (with corresponding role) related to the given goal.
        """
        messages = [{"role": "user", "content": self.initial_draft}]
        for element in self.elements:
            # TODO: see how this performs. It could save some tokens to skip the ones that aren't related to the current goal.
            if element.goal != goal:
                continue
            messages.append({"role": "system", "content": element.question})
            messages.append({"role": "user", "content": element.response})

        return messages

    def synthesize_draft_response(self):
        """Returns a draft response that synthesizes the user's responses to the questions."""
        messages = []
        for question in self.elements:
            messages.append({"role": "system", "content": question.question})
            messages.append({"role": "user", "content": question.response})
        return synthesize_user_responses(
            custom_instructions="",
            initial_draft=self.initial_draft,
            messages=messages,
            model=self.model,
        )
