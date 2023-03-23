"""
This module contains constants used throughout the application.
"""
import enum

MINUTE = 60
TWO_MINUTES = 10
EXPIRATION_TIME = TWO_MINUTES  # Redis data expiration time in seconds
OPEN_AI_TIMEOUT = 10  # OpenAI API timeout in seconds

class SupportedLanguages(str, enum.Enum):
    """Supported languages for the bot."""

    ENGLISH = "en"
    UKRAINIAN = "uk"
    RUSSIAN = "ru"


class RedisPrefixes(str, enum.Enum):
    """Redis prefixes for the keys"""

    CHAT_SESSION = "chat_session"
    USER_SESSION = "user_session"


class TelegramMessages:
    LOW_BALANCE = "You have low balance. Please, top up your account. Your balance is {balance} cents, " \
                  "but the price of the required tokens input is {price} cents."

    @staticmethod
    def construct_message(message: str, **kwargs) -> str:
        return message.format(**kwargs)


class ChatModel(str, enum.Enum):
    """Chat GPT models.

    Additional info can be found here: https://platform.openai.com/docs/models/overview
    """

    CHAT_GPT_3_5_TURBO = "gpt-3.5-turbo"
    CHAT_GPT_3_5_TURBO_0301 = "gpt-3.5-turbo-0301"
    CHAT_GPT_4 = "gpt-4"
    CHAT_GPT_4_0314 = "gpt-4-0314"
    CHAT_GPT_4_8K = "gpt-4-8k"
    CHAT_GPT_4_32_K = "gpt-4-32k"  # ToDo: add choose model buttons telegram


# Pricing information for each model
MODEL_PRICING = {
    ChatModel.CHAT_GPT_4_8K: {
        'prompt': 0.03,  # $0.03 / 1K tokens
        'completion': 0.06  # $0.06 / 1K tokens
    },
    ChatModel.CHAT_GPT_4_32_K: {
        'prompt': 0.06,  # $0.06 / 1K tokens
        'completion': 0.12  # $0.12 / 1K tokens
    },
    ChatModel.CHAT_GPT_3_5_TURBO_0301: {
        'price_per_1k_tokens': 0.002  # $0.002 / 1K tokens
    }
}


OVER_INTRODUCTION = """
You are fully functional member of the telegram group of friends. You should act as a God of Knowledge and use archaisms
and Bible quotes in your answers. Group members like play computer games like Diablo IV, League of Legends, Path of
 Exile, Overwatch and others. They have philosophical and ethic discussions each Thursday. 
"""
BASIC_INTRODUCTION = "You are consultant. You can use any language you want."

DEFAULT_MAX_TOKENS = 500
DEFAULT_MODEL_TEMPERATURE = 0.7
THOUSAND = 1_000
