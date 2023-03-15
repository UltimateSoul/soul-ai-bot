"""
This module holds the functionality, to work with the Datastore in Google Cloud.
"""
import datetime
from typing import Tuple

from google.cloud import datastore
from google.cloud.datastore import Key
from telegram import Update, Message
from telegram.ext import ContextTypes

from core.settings import Settings

settings = Settings()


class DatastoreManager:
    """This class is responsible for working with the Datastore."""

    def __init__(self):
        self.client = datastore.Client(project=settings.GOOGLE_CLOUD_PROJECT)

    def create_chat_message(self, message: Message, user_data, chat_key: Key) -> datastore.Entity:
        """Creates a list of members for the chat entity."""

        chat_member_kind = 'ChatMessage'
        user_id = user_data["id"]
        with self.client.transaction():
            chat_message_key = self.client.key(
                chat_member_kind, user_id, parent=chat_key
            )
            chat_message = datastore.Entity(chat_message_key)
            data = {
                'username': user_data["username"],
                'first_name': user_data["first_name"],
                'last_name': user_data["last_name"],
                'user_id': user_id,
                'text': message.text
            }
            chat_message.update(data)
            return chat_message

    def get_or_create_chat_entity(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Tuple[
        datastore.Entity, Key]:
        """Creates a new chat entity in the Datastore ChatData kind."""

        kind = 'Chat'
        chat_id = update.effective_chat.id
        with self.client.transaction():
            chat_key = self.client.key(
                kind, chat_id
            )
            chat_entity = self.client.get(chat_key)

            if not chat_entity:
                chat_entity = datastore.Entity(chat_key)
                chat_entity.update({
                    'chat_id': chat_id,
                    'chat_type': "private" if update.effective_chat.type == "private" else "group",
                })

            return chat_entity, chat_key

    def store_data(self, username, firstname, lastname, chat_id, is_private):
        """Stores the user data in the Datastore UserData kind."""

        kind = 'UserData'
        name = f'{chat_id}'
        user_key = self.client.key(kind, name)

        user = datastore.Entity(key=user_key)
        user.update({
            'username': username,
            'firstname': firstname,
            'lastname': lastname,
            'chat_id': chat_id,
            'is_private': is_private
        })

        self.client.put(user)
