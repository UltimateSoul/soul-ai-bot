"""
That module holds the functionality connected with ChatSession from Memorystore (Redis) in-memory database.
ChatSessions reduce the load on the Datastore database, by storing the data in the Memorystore.
"""
import json
import logging
from telegram import Update

from core.constants import TWO_MINUTES, DATASTORE_FLOAT_MULTIPLIER
from core.datastore import DatastoreManager, UserAccount, Chat
from core.redis_tools import redis_client

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Session:
    """This class is responsible for working with the ChatSession in the Memorystore (Redis)"""

    PREFIX = "session:"

    def __init__(self, entity_id, update: Update):
        self._id = entity_id
        self.redis_key = f"{self.PREFIX}{entity_id}"
        self.datastore_manager = DatastoreManager()
        self.update = update

    def set(self, entity: dict):
        logger.debug(f"Setting {type(self).__name__} in Redis.")
        """The first key value pair is without the expiration time, it will be deleted afterwards in 
        listener.pu functionality"""
        redis_client.set(self.redis_key, json.dumps(entity))
        """The second key value pair has the expiration time, listener consumes it and retrieves the ID 
        to delete afterwards"""
        redis_client.set(f"shadow:{self.redis_key}", "", TWO_MINUTES)
        logger.debug("Session set in Redis.")

    def get(self, *args, **kwargs):
        raise NotImplementedError("This method should be implemented in the child class.")

    def delete(self):
        redis_client.delete(self.redis_key)

    def __repr__(self):
        return f"{type(self).__name__} - ({self._id})"

    __str__ = __repr__


class ChatSession(Session):
    """This class is responsible for working with the ChatSession in the Memorystore (Redis)"""

    PREFIX = "chat_session:"

    def get(self) -> Chat:
        logger.debug("Trying to get the ChatSession from Redis.")
        chat: str = redis_client.get(self.redis_key)
        user_name = f"{self.update.effective_user.first_name} {self.update.effective_user.last_name}"
        if not user_name:
            user_name = self.update.effective_user.username
        new_message = {
            'role': 'user',
            'content': f"{user_name} says:{self.update.effective_message.text}"
        }
        if chat:
            chat_data: dict = json.loads(chat)
            logger.debug(f"ChatSession found in Redis: {chat_data}")
            chat_data["messages"].append(new_message)
            self.set(chat_data)
            return Chat(**chat_data)
        logger.debug("ChatSession not found in Redis, getting it from the Datastore.")
        chat_entity, _, created = self.datastore_manager.get_or_create_chat_entity(self.update)
        logger.debug(f"ChatSession found in the Datastore: {chat_entity}. Created - {created}")
        chat_data: dict = json.loads(json.dumps(chat_entity), parse_int=str)
        self.set(chat_data)
        logger.debug("Updated ChatSession set in Redis.")
        return Chat(**chat_data)


class UserSession(Session):
    """This class is responsible for working with the UserSession in the Memorystore (Redis)"""

    PREFIX = "user_session:"

    def get(self) -> UserAccount:
        logger.debug("Trying to get the UserSession from Redis.")
        user: str = redis_client.get(self.redis_key)
        if user:
            user_data: dict = json.loads(user)
            logger.debug(f"UserSession found in Redis: {user_data}")
            return UserAccount(**user_data)
        logger.debug("UserSession not found in Redis, getting it from the Datastore.")
        user_entity, _, created = self.datastore_manager.get_or_create_user_account_entity(self.update)
        logger.debug(f"UserSession found in the Datastore: {user_entity}. Created - {created}")
        user_data: dict = json.loads(json.dumps(user_entity), parse_int=str)
        self.set(user_data)
        logger.debug("UserSession set in Redis.")
        return UserAccount(**user_data)
