from typing import Any, Dict, List, Optional, Union
import os
import json
import tiktoken
from openai import OpenAI
from docassemble.base.util import get_config

__all__ = ["chat_completion"]

if os.getenv("OPENAI_API_KEY"):
    client:Optional[OpenAI] = OpenAI()
else:
    client = None


def chat_completion(
    system_message: str,
    user_message: str,
    openai_client: Optional[OpenAI] = None,
    openai_api: Optional[str] = None,
    temperature: float = 0.5,
    json_mode=False,
    model: str = "gpt-3.5-turbo",
) -> Union[List[Any], Dict[str, Any], str]:
    """A light wrapper on the OpenAI chat endpoint.

    Includes support for token limits, error handling, and moderation queue.

    It is also possible to specify an alternative model, and we support GPT-4-turbo's JSON
    mode.

    As of today (1/2/2024) JSON mode requires the model to be set to "gpt-4-1106-preview"

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
    token_count = len(encoding.encode(system_message + user_message))

    if model.startswith("gpt-4-"):  # E.g., "gpt-4-1106-preview"
        max_input_tokens = 128000
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
        response_format={"type": "json_object"} if json_mode else None, # type: ignore
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
