"""
    Pydantic settings for the application

"""
import os

from pydantic import BaseSettings, Field, AnyHttpUrl, PostgresDsn, validator


class Settings(BaseSettings):
    """Application settings"""

    OPEN_AI_API_KEY: str = Field(env="OPEN_AI_API_KEY")
    TELEGRAM_BOT_API_TOKEN: str = Field(env="TELEGRAM_BOT_API_TOKEN")
    OPEN_AI_MODEL: str = Field(env="OPEN_AI_MODEL")
    TELEGRAM_WEBHOOK_URL: str = Field(env="TELEGRAM_WEBHOOK_URL")

    class Config:
        env_file = ".env"  # Load settings from .env file
        env_file_encoding = "utf-8"  # Specify encoding of .env file
