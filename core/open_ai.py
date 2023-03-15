"""
    This file holds the logic for interacting with the OpenAI API.
"""
import logging

import backoff
import openai
import tiktoken

from core.settings import Settings

settings = Settings()

# Set up OpenAI API
openai.api_key = settings.OPEN_AI_API_KEY  # ToDo: add normal settings get
INTRODUCTION = """You Active 'Overdrotch Legends' member, fusing Overwatch & LoL. Play various games, discuss philosophy on Discord Thursdays. Alias: 'God's Soul', multilingual, friendly. Impart wisdom, use archaisms & Bible quotes."""


# ToDo: add backoff retry logic
def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301"):
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    if model == "gpt-3.5-turbo-0301":  # note: future models may deviate from this
        num_tokens = 0
        for message in messages:
            num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
            for key, value in message.items():
                num_tokens += len(encoding.encode(value))
                if key == "name":  # if there's a name, the role is omitted
                    num_tokens += -1  # role is always required and always 1 token
        num_tokens += 2  # every reply is primed with <im_start>assistant
        return num_tokens
    else:
        raise NotImplementedError(f"""num_tokens_from_messages() is not presently implemented for model {model}.
  See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens.""")


# Define function to generate response with OpenAI API
@backoff.on_exception(
    wait_gen=backoff.expo,
    exception=(openai.error.RateLimitError, openai.error.InvalidRequestError, openai.error.APIError,
               openai.error.ServiceUnavailableError, openai.error.Timeout),
    max_tries=5,
    logger="open-ai-generate-response",
    backoff_log_level=logging.DEBUG,
)
async def generate_response(message):
    context = [
        {"role": "system", "content": INTRODUCTION},
        {"role": "user", "content": message},  # ToDo: add here messages from the Database
    ]
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # The name of the OpenAI chatbot model to use
        messages=context,  # The conversation history up to this point, as a list of dictionaries
        max_tokens=3800,  # The maximum number of tokens (words or subwords) in the generated response
        stop=None,  # The stopping sequence for the generated response, if any (not used here)
        temperature=0.7,  # The "creativity" of the generated response (higher temperature = more creative)
    )

    # Find the first response from the chatbot that has text in it (some responses may not have text)
    for choice in response.choices:
        if "text" in choice:
            return choice.text

    # If no response with text is found, return the first response's content (which may be empty)
    return response.choices[0].message.content
