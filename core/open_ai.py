"""
    This file holds the logic for interacting with the OpenAI API.
"""
import logging
import typing as t

import backoff
import openai
import tiktoken


from core.models import UserAccount, Chat
from core.settings import Settings
from core.constants import ChatModel, THOUSAND, MODEL_PRICING, DEFAULT_MAX_TOKENS, DEFAULT_MODEL_TEMPERATURE

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

settings = Settings()

# Set up OpenAI API
openai.api_key = settings.OPEN_AI_API_KEY  # ToDo: add normal settings get


class UserTokenManager:

    def __init__(self, user_account: UserAccount, chat: Chat):
        self.user_account = user_account
        self.chat = chat
        self.model = chat.current_model
        if self.model in [ChatModel.CHAT_GPT_4_8K, ChatModel.CHAT_GPT_4_32_K]:
            self.model = ChatModel.CHAT_GPT_4
        self.tokens_for_messages = 0
        self.dollars_for_prompt = 0

    def count_tokens_from_messages(self):
        """Returns the number of tokens used by the user in the chat."""
        chat_data = self.chat.dict()
        messages = [chat_data["system_message"]] + chat_data["messages"]
        self.tokens_for_messages = num_tokens_from_messages(messages, model=self.model)
        return self.tokens_for_messages

    def count_tokens_to_dollars(self, tokens: int, is_prompt: bool = False):
        """Returns the number of cents used by the user in the chat."""
        model = self.chat.current_model
        match model:
            case ChatModel.CHAT_GPT_3_5_TURBO | ChatModel.CHAT_GPT_3_5_TURBO_0301:
                self.dollars_for_prompt = (
                        tokens / THOUSAND * MODEL_PRICING[ChatModel.CHAT_GPT_3_5_TURBO_0301]['price_per_1k_tokens'])
                return self.dollars_for_prompt
            case ChatModel.CHAT_GPT_4 | ChatModel.CHAT_GPT_4_0314 | ChatModel.CHAT_GPT_4_8K | ChatModel.CHAT_GPT_4_32_K:
                self.dollars_for_prompt = tokens / THOUSAND * MODEL_PRICING[ChatModel.CHAT_GPT_4][
                    'prompt'] if is_prompt else \
                    tokens / THOUSAND * MODEL_PRICING[ChatModel.CHAT_GPT_4]['completion']
                return self.dollars_for_prompt
            case _:
                raise ValueError(f"Model {model} not found.")

    def can_user_ask_ai(self) -> bool:
        """Returns True if the user has enough tokens to ask the AI."""
        tokens = self.count_tokens_from_messages()
        dollars = self.count_tokens_to_dollars(tokens, is_prompt=True)
        current_balance = self.user_account.current_balance
        return current_balance >= dollars * 100  # convert dollars to cents


def num_tokens_from_messages(messages: t.List[t.Dict[str, str]], model: ChatModel = ChatModel.CHAT_GPT_3_5_TURBO_0301):
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        logger.warning("Model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    match model:
        case ChatModel.CHAT_GPT_3_5_TURBO:
            logger.warning("gpt-3.5-turbo may change over time. Returning num tokens assuming gpt-3.5-turbo-0301.")
            return num_tokens_from_messages(messages, model=ChatModel.CHAT_GPT_3_5_TURBO_0301)
        case ChatModel.CHAT_GPT_4:
            logger.warning("gpt-4 may change over time. Returning num tokens assuming gpt-4-0314.")
            return num_tokens_from_messages(messages, model=ChatModel.CHAT_GPT_4_0314)
        case ChatModel.CHAT_GPT_3_5_TURBO_0301:
            tokens_per_message = 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
            tokens_per_name = -1  # if there's a name, the role is omitted
        case ChatModel.CHAT_GPT_4_0314:
            tokens_per_message = 3
            tokens_per_name = 1
        case _:
            raise NotImplementedError(
                f"""num_tokens_from_messages() is not implemented for model {model}.
                 See https://github.com/openai/openai-python/blob/main/chatml.md for information on how
                  messages are converted to tokens.""")
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 2  # every reply is primed with <im_start>assistant
    return num_tokens


# Define function to generate response with OpenAI API
@backoff.on_exception(
    wait_gen=backoff.expo,
    exception=(openai.error.RateLimitError, openai.error.InvalidRequestError, openai.error.APIError,
               openai.error.ServiceUnavailableError, openai.error.Timeout),
    max_tries=5,
    logger="open-ai-generate-response",
    backoff_log_level=logging.DEBUG,
)
async def generate_response(messages: list[dict],
                            model: ChatModel = ChatModel.CHAT_GPT_3_5_TURBO_0301.value,
                            max_tokens=DEFAULT_MAX_TOKENS,
                            temperature=DEFAULT_MODEL_TEMPERATURE):
    response = openai.ChatCompletion.create(
        model=model,  # The name of the OpenAI chatbot model to use
        messages=messages,  # The conversation history up to this point, as a list of dictionaries
        max_tokens=max_tokens,  # The maximum number of tokens (words or subwords) in the generated response
        stop=None,  # The stopping sequence for the generated response, if any (not used here)
        temperature=temperature,  # The "creativity" of the generated response (higher temperature = more creative)
    )

    # Find the first response from the chatbot that has text in it (some responses may not have text)
    for choice in response.choices:
        if "text" in choice:
            return choice.text

    # If no response with text is found, return the first response's content (which may be empty)
    return response
