"""
This module holds the functionality, to work with the Datastore in Google Cloud.
"""
import typing as t

from google.cloud import datastore
from google.cloud.datastore import Key
from telegram import Update

from core.models import Chat, Message, UserAccount, ModelTokenUsage
from core.constants import BASIC_INTRODUCTION, OVER_INTRODUCTION
from core.settings import Settings

settings = Settings()
CHAT_KIND = "Chat"
USER_ACCOUNT_KIND = "UserAccount"


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
                USER_ACCOUNT_KIND, user_id
            )
            user_entity = self.client.get(user_key)

            if not user_entity:
                is_created = True
                user_entity = datastore.Entity(user_key)
                user_account = UserAccount(user_id=user_id, model_token_usage=ModelTokenUsage())
                user_entity.update(user_account.dict())
                self.client.put(user_entity)
            return user_entity, user_key, is_created

    def update_or_create_user_account_entity(self, data: dict) -> t.Tuple[datastore.Entity, Key, bool]:
        """Creates a new user account entity in the Datastore UserAccount kind."""

        user_id = data.get("user_id")
        is_created = False

        with self.client.transaction():
            user_key = self.client.key(
                USER_ACCOUNT_KIND, user_id
            )
            user_entity = self.client.get(user_key)

            if not user_entity:
                is_created = True
                user_entity = datastore.Entity(user_key)

            user_entity.update(data)
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
            user_name = f"{update.effective_user.first_name} {update.effective_user.last_name}"
            if not user_name:
                user_name = update.effective_user.username
            new_message = {
                            "role": "user",
                            "content": f"{user_name} says:{update.effective_message.text}"
                        }
            if not chat_entity:
                is_created = True
                chat_entity = datastore.Entity(chat_key)
                # create initial system introduction for the chat, can be changed afterwards
                intro_system_message = OVER_INTRODUCTION if chat_id == settings.MANAGED_CHAT_ID else BASIC_INTRODUCTION
                chat = Chat(**{
                    "chat_id": chat_id,
                    "system_message": Message(content=intro_system_message),
                    "messages": [
                        Message(**new_message)
                    ]
                })
                chat_entity.update(chat.dict())
            else:
                chat_entity.update({
                    "messages": chat_entity["messages"] + [new_message]
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
            chat_entity.update(data)
            self.client.put(chat_entity)
            return chat_entity, chat_key, is_created
