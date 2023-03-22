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
