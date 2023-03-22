"""
That module holds the functionality connected with ChatSession from Memorystore (Redis) in-memory database.
ChatSessions reduce the load on the Datastore database, by storing the data in the Memorystore.
"""
import json
import logging

from telegram import Update
from telegram.ext import ContextTypes

from core.constants import TWO_MINUTES
from core.datastore import DatastoreManager, CHAT_KIND
from core.redis_tools import redis_client

logger = logging.getLogger(__name__)


class ChatSession:
    """This class is responsible for working with the ChatSession in the Memorystore (Redis)"""

    def __init__(self, chat_id, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.chat_id = chat_id
        self.redis_key = f"chat_session:{chat_id}"
        self.datastore_manager = DatastoreManager()
        self.update = update
        self.context = context

    def set(self, chat: dict):
        logger.debug("Setting chat session in Redis.")
        """The first key value pair is without the expiration time, it will be deleted afterwards in 
        listener.pu functionality"""
        redis_client.set(self.redis_key, json.dumps(chat))
        """The second key value pair has the expiration time, listener consumes it and retrieves the ID 
        to delete afterwards"""
        redis_client.set(f"shadow:{self.redis_key}", "", TWO_MINUTES)
        logger.debug("Session set in Redis.")

    def get(self):
        logger.debug("Trying to get the ChatSession from Redis.")
        chat = redis_client.get(self.redis_key)
        if chat:
            dict_chat = json.loads(chat)
            new_message = {
                'user_id': self.update.effective_user.id,
                'text': f"{self.update.effective_user.username} says:{self.update.effective_message.text}"
            }
            dict_chat["messages"].append(new_message)
            self.set(dict_chat)
            logger.debug(f"ChatSession found in Redis: {dict_chat}")
            return dict_chat
        logger.debug("ChatSession not found in Redis, getting it from the Datastore.")
        chat_entity, chat_key, created = self.datastore_manager.get_or_create_chat_entity(self.update)
        logger.debug(f"ChatSession found in the Datastore: {chat_entity}. Created - {created}")
        self.set(chat_entity)
        logger.debug("ChatSession set in Redis.")
        return chat_entity

    def delete(self):
        redis_client.delete(self.redis_key)
