"""
This module holds the functionality, to work with the Datastore in Google Cloud.
"""
import logging
import typing as t
from sys import getsizeof

from google.cloud import datastore
from google.cloud.datastore import Key
from telegram import Update

from core.constants import BASIC_INTRODUCTION, DATASTORE_FLOAT_MULTIPLIER
from core.models import Chat, Message, UserAccount, ModelTokenUsage
from core.settings import Settings

settings = Settings()
CHAT_KIND = "Chat"
USER_ACCOUNT_KIND = "UserAccount"

logger = logging.getLogger('datastore: ')
logger.setLevel(logging.DEBUG)


class DatastoreManager:
    """This class is responsible for working with the Datastore."""

    def __init__(self):
        self.client = datastore.Client(project=settings.GOOGLE_CLOUD_PROJECT)

    def get_user_account_by_username(self, username: str):
        """Returns a user account entity by its username."""
        query = self.client.query(kind=USER_ACCOUNT_KIND)
        query.add_filter('username', '=', username.replace("@", ""))
        for user in query.fetch(limit=1):
            user.update({'current_balance': user['current_balance'] / DATASTORE_FLOAT_MULTIPLIER})
            return user

    def get_or_create_user_account_entity(self, data: t.Union[Update, dict]) -> t.Tuple[datastore.Entity, Key, bool]:
        """Creates a new user account entity in the Datastore UserAccount kind."""

        user_id = data.effective_user.id if isinstance(data, Update) else data['user_id']
        is_created = False

        with self.client.transaction():
            user_key = self.client.key(
                USER_ACCOUNT_KIND, user_id
            )
            user_entity = self.client.get(user_key)
            if not user_entity:
                is_created = True
                user_entity = datastore.Entity(user_key)
                username = data.effective_user.username if isinstance(data, Update) else data['username']
                user_account = UserAccount(user_id=user_id,
                                           is_admin=user_id == settings.ADMIN_CHAT_ID,
                                           username=username,
                                           model_token_usage=ModelTokenUsage()).dict()
                current_balance = user_account['current_balance']
                user_account[
                    'current_balance'] = current_balance * DATASTORE_FLOAT_MULTIPLIER  # datastore cant store floats
                user_entity.update(user_account)
                self.client.put(user_entity)
            user_entity['current_balance'] = user_entity['current_balance'] / DATASTORE_FLOAT_MULTIPLIER
            return user_entity, user_key, is_created

    def update_or_create_user_account_entity(self, data: dict) -> t.Tuple[datastore.Entity, Key, bool]:
        """Creates a new user account entity in the Datastore UserAccount kind."""

        user_id = data.get("user_id")
        is_created = False

        with self.client.transaction():
            user_key = self.client.key(
                USER_ACCOUNT_KIND, user_id
            )
            data['current_balance'] = data['current_balance'] * DATASTORE_FLOAT_MULTIPLIER
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
            new_message = Message(**new_message)
            new_message_entity = datastore.Entity(exclude_from_indexes=list(new_message.dict().keys()))  # noqa
            new_message_entity.update(new_message.dict())
            if not chat_entity:
                is_created = True
                chat_entity = datastore.Entity(chat_key,
                                               exclude_from_indexes=('messages', 'system_message'))
                intro_system_message = BASIC_INTRODUCTION
                system_message = Message(content=intro_system_message)
                system_message_entity = datastore.Entity(
                    exclude_from_indexes=list(system_message.dict().keys()))  # noqa
                system_message_entity.update(system_message.dict())

                chat = Chat(**{
                    "chat_id": chat_id,
                    "system_message": system_message_entity,
                    "messages": [
                        new_message_entity
                    ]
                })
                chat_entity.update(chat.dict())
            else:
                chat_message_entities = []
                for message in chat_entity["messages"]:
                    message_entity = datastore.Entity(exclude_from_indexes=list(message.keys()))  # noqa
                    message_entity.update(message)
                    chat_message_entities.append(message_entity)
                chat_entity.update({
                    "messages": chat_message_entities + [new_message_entity]
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
            logger.debug(f"chat_entity: {chat_entity}")
            logger.debug(f'Data size: {getsizeof(data)}')
            logger.debug(f'Data: {data}')
            if not chat_entity:
                is_created = True
                chat_entity = datastore.Entity(chat_key,
                                               exclude_from_indexes=('messages', 'system_message'))
                intro_system_message = data["system_message"]["content"]
                system_message = Message(content=intro_system_message)
                system_message_entity = datastore.Entity(
                    exclude_from_indexes=list(system_message.dict().keys()))  # noqa
                system_message_entity.update(system_message.dict())
                chat_message_entities = []
                for message in data["messages"]:
                    message_entity = datastore.Entity(exclude_from_indexes=list(message.keys()))  # noqa
                    message_entity.update(message)
                    chat_message_entities.append(message_entity)
                chat = Chat(**{
                    "chat_id": chat_id,
                    "system_message": system_message_entity,
                    "messages": chat_message_entities
                })
                chat_entity.update(chat.dict())
            else:
                chat_message_entities = []
                for message in data["messages"]:
                    message_entity = datastore.Entity(exclude_from_indexes=list(message.keys()))  # noqa
                    message_entity.update(message)
                    chat_message_entities.append(message_entity)
                data.pop("messages")
                chat_entity.update(dict(messages=chat_message_entities, **data))
            self.client.put(chat_entity)
            return chat_entity, chat_key, is_created
