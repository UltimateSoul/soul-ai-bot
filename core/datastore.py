"""
This module holds the functionality, to work with the Datastore in Google Cloud.
"""
import typing as t

from google.cloud import datastore
from google.cloud.datastore import Key
from telegram import Update, Message
from telegram.ext import ContextTypes

from core.open_ai import ChatModel, BASIC_INTRODUCTION, OVER_INTRODUCTION, DEFAULT_MAX_TOKENS, DEFAULT_MODEL_TEMPERATURE
from core.settings import Settings

settings = Settings()
CHAT_KIND = "Chat"
UserAccount = "UserAccount"


class DatastoreManager:
    """This class is responsible for working with the Datastore."""

    def __init__(self):
        self.client = datastore.Client(project=settings.GOOGLE_CLOUD_PROJECT)

    def get_or_create_user_account_entity(self, update: Update) -> t.Tuple[datastore.Entity, Key, bool]:
        """Creates a new user account entity in the Datastore UserAccount kind."""

        user_id = update.effective_user.id
        is_created = False

        with self.client.transaction():
            user_key = self.client.key(
                UserAccount, user_id
            )
            user_entity = self.client.get(user_key)

            if not user_entity:
                is_created = True
                user_entity = datastore.Entity(user_key)
                user_entity.update({
                    "user_id": user_id,
                    "is_admin": False,
                    "model_token_usage": {
                        ChatModel.CHAT_GPT_4_8K.value: {
                            "prompt": 0,
                            "completion": 0,
                            "total_cost": 0
                        },
                        ChatModel.CHAT_GPT_4_32_K.value: {
                            "prompt": 0,
                            "completion": 0,
                            "total_cost": 0
                        },
                        ChatModel.CHAT_GPT_3_5_TURBO_0301.value: {
                            "total_tokens": 0,
                            "total_cost": 0
                        }
                    }
                })
                self.client.put(user_entity)
            return user_entity, user_key, is_created

    def get_or_create_chat_entity(self, update: Update) -> t.Tuple[datastore.Entity, Key, bool]:
        """Creates a new chat entity in the Datastore ChatData kind."""

        chat_id = update.effective_chat.id
        is_created = False

        with self.client.transaction():
            chat_key = self.client.key(
                CHAT_KIND, chat_id
            )
            chat_entity = self.client.get(chat_key)

            if not chat_entity:
                is_created = True
                chat_entity = datastore.Entity(chat_key)
                user_name = f"{update.effective_user.first_name} {update.effective_user.last_name}"
                if not user_name:
                    user_name = update.effective_user.username
                # create initial system introduction for the chat, can be changed afterwards
                intro_system_message = OVER_INTRODUCTION if chat_id == settings.MANAGED_CHAT_ID else BASIC_INTRODUCTION
                chat_entity.update({
                    "chat_id": chat_id,
                    "current_model": ChatModel.CHAT_GPT_3_5_TURBO_0301,
                    "max_tokens": DEFAULT_MAX_TOKENS,
                    "temperature": DEFAULT_MODEL_TEMPERATURE,
                    "system_message": [
                        {
                            "role": "system",
                            "content": intro_system_message
                        }
                    ],
                    "messages": [
                        {
                            "role": "user",
                            "text": f"{user_name} says:{update.effective_message.text}"
                        }
                    ]
                })
                self.client.put(chat_entity)

            return chat_entity, chat_key, is_created

    def update_or_create_chat_entity(self, data: dict) -> t.Tuple[datastore.Entity, Key, bool]:
        """Updates the chat entity in the Datastore ChatData kind or creates in instead."""

        chat_id = data["chat_id"]
        is_created = False

        with self.client.transaction():
            chat_key = self.client.key(
                CHAT_KIND, chat_id
            )
            chat_entity = self.client.get(chat_key)

            if not chat_entity:
                is_created = True
                chat_entity = datastore.Entity(chat_key)

            if not is_created:
                old_messages = chat_entity["messages"]
                new_messages = data["messages"]
                messages = old_messages + new_messages
                data["messages"] = messages
            chat_entity.update(data)
            self.client.put(chat_entity)
            return chat_entity, chat_key, is_created
