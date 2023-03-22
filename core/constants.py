"""
This module contains constants used throughout the application.
"""
import enum

MINUTE = 60
TWO_MINUTES = 10
EXPIRATION_TIME = TWO_MINUTES  # Redis data expiration time in seconds


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
