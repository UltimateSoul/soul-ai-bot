"""
    Pydantic settings for the application

"""
import os

from pydantic import BaseSettings, Field

env_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")


class Settings(BaseSettings):
    """Application settings"""

    OPEN_AI_API_KEY: str = Field(env="OPEN_AI_API_KEY")
    TELEGRAM_BOT_API_TOKEN: str = Field(env="TELEGRAM_BOT_API_TOKEN")
    OPEN_AI_MODEL: str = Field(env="OPEN_AI_MODEL")
    TELEGRAM_WEBHOOK_URL: str = Field(env="TELEGRAM_WEBHOOK_URL")
    BOT_USERNAME: str = Field(env="BOT_USERNAME")
    GOOGLE_CLOUD_PROJECT: str = Field(env="GOOGLE_CLOUD_PROJECT")

    class Config:
        env_file = env_file_path  # Load settings from .env file
        env_file_encoding = "utf-8"  # Specify encoding of .env file
