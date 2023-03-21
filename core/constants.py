"""
This module contains constants used throughout the application.
"""
import enum

MINUTE = 60
TWO_MINUTES = 10
EXPIRATION_TIME = TWO_MINUTES


class RedisPrefixes(str, enum.Enum):
    CHAT_SESSION = "chat_session"
    USER_SESSION = "user_session"