"""
    Pydantic settings for the application

"""
import os

from dotenv import load_dotenv
from pydantic import BaseSettings, Field

env_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(dotenv_path=env_file_path)  # ToDo: remove this line when the application is deployed


class MemoryStoreSettings(BaseSettings):
    """MemoryStore settings"""

    HOST: str = Field(env="MEMORYSTORE_HOST", default="localhost")
    PORT: int = Field(env="MEMORYSTORE_PORT", default=6379)
    DB: int = Field(env="MEMORYSTORE_DB", default=0)


class Settings(BaseSettings):
    """Application settings"""

    OPEN_AI_API_KEY: str = Field(env="OPEN_AI_API_KEY")
    TELEGRAM_BOT_API_TOKEN: str = Field(env="TELEGRAM_BOT_API_TOKEN")
    TELEGRAM_WEBHOOK_URL: str = Field(env="TELEGRAM_WEBHOOK_URL")
    BOT_USERNAME: str = Field(env="BOT_USERNAME")
    GOOGLE_CLOUD_PROJECT: str = Field(env="GOOGLE_CLOUD_PROJECT")
    ADMIN_CHAT_ID: str = Field(env="ADMIN_CHAT_ID")
    MEMORY_STORE_SETTINGS: MemoryStoreSettings = MemoryStoreSettings()

    class Config:
        env_file = env_file_path  # Load settings from .env file
        env_file_encoding = "utf-8"  # Specify encoding of .env file
