"""
This module contains constants used throughout the application.
"""
import enum

MINUTE = 60
TWO_MINUTES = 2 * MINUTE
EXPIRATION_TIME = TWO_MINUTES  # Redis data expiration time in seconds
OPEN_AI_TIMEOUT = 10  # OpenAI API timeout in seconds
DATASTORE_FLOAT_MULTIPLIER = 100_000  # Multiplier for float values in the datastore


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

    TOKEN_USAGE = """*Usage of models*:
*GPT 3 5 Turbo*: _{token_usage.gpt_3_5_turbo.total_tokens}_ tokens
*GPT 3 5 Turbo 0301*: _{token_usage.gpt_3_5_turbo_0301.total_tokens}_ tokens
*GPT 4*: _{token_usage.gpt_4.total_tokens}_ tokens

How are we counting tokens? ||[Open AI API](https://platform.openai.com/docs/guides/chat/introduction)||
"""
    HELP = """Commands:
/help - show this message
/get_balance - get your balance (by default you get 200 cents for free, but the API usage costs money: [Open AI Pricing](https://openai.com/pricing/)
/get_token_usage - get the usage of your tokens for each model
/get_tokens_for_message - get the number of tokens required for the message you want to send
/set_max_tokens - set the maximum number of tokens for the bot's response
/set_temperature - set the temperature of the model
/set_system_message - set the system message that will be sent to the bot when you start a conversation
/get_system_message - get the system message that will be sent to the bot when you start a conversation
/start - start a conversation with the bot
/ask_knowledge_god - start a conversation with the Open AI GPT Chat Bot
"""
    START_PART_1 = """Hello, {username}! This is a chatbot powered by Open AI API. 
You can test different Open AI models, such as GPT4 or GPT3-5-turbo from your phone in telegram! 
You also can do more with the "Context" feature. The thing is you can set a special system context to your dedicated chat.
Chat can act as a basic consultant or the God of Knowledge or whatever you specify in your system message input.
It also has memory, more info you can get after connecting with bot. Of course it have some restrictions, such as the token context limit."""
    START_PART_2 = """For instance for *GPT 3\\.5 Turbo* model that amount equals to *4,096* tokens: [Open AI API](https://platform.openai.com/docs/models/gpt-3-5)"""

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
    CHAT_GPT_4_32_K = "gpt-4-32k"


class SupportedModels(str, enum.Enum):
    """Supported models for the bot."""

    CHAT_GPT_3_5_TURBO_0301 = "gpt-3.5-turbo-0301"
    # CHAT_GPT_4_0314 = "gpt-4-0314"


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

BASIC_INTRODUCTION = "You are consultant. You can use any language you want."

DEFAULT_MAX_TOKENS = 500
DEFAULT_MODEL_TEMPERATURE = 0.7
THOUSAND = 1_000
