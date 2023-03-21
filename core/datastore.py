"""
This module holds the functionality, to work with the Datastore in Google Cloud.
"""
import typing as t

from google.cloud import datastore
from google.cloud.datastore import Key
from telegram import Update, Message
from telegram.ext import ContextTypes

from core.open_ai import ChatModel
from core.settings import Settings

settings = Settings()
CHAT_KIND = 'Chat'
CHAT_MESSAGE_KIND = 'ChatMessage'


class DatastoreManager:
    """This class is responsible for working with the Datastore."""

    def __init__(self):
        self.client = datastore.Client(project=settings.GOOGLE_CLOUD_PROJECT)

    def get_or_create_chat_entity(self, update: Update,
                                  context: ContextTypes.DEFAULT_TYPE) -> t.Tuple[datastore.Entity, Key, bool]:
        """Creates a new chat entity in the Datastore ChatData kind."""

        chat_id = update.effective_chat.id
        is_created = False

        with self.client.transaction():
            chat_key = self.client.key(
                CHAT_KIND, chat_id
            )
            chat_entity = self.client.get(chat_key)
            username = update.effective_user.username
            message = {
                'username': update.effective_user.username,
                'first_name': update.effective_user.first_name,
                'last_name': update.effective_user.last_name,
                'user_id': update.effective_user.id,
                'text': f"{username} says:{update.effective_message.text}"
            }

            if not chat_entity:
                is_created = True
                chat_entity = datastore.Entity(chat_key)
                chat_entity.update({
                    'chat_id': chat_id,
                    'current_model': ChatModel.CHAT_GPT_3_5_TURBO_0301,
                    'messages': [message]
                })

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

            return chat_entity, chat_key, is_created
