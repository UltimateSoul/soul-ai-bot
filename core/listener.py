import json
import logging
import sys

import redis

from core.constants import RedisPrefixes
from core.settings import Settings
from core.datastore import DatastoreManager
settings = Settings()

logger = logging.getLogger('listener')
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)

redis_client = redis.Redis(host=settings.MEMORY_STORE_SETTINGS.HOST,
                           port=settings.MEMORY_STORE_SETTINGS.PORT)

EXPIRED_KEY_EVENT = "__keyevent@0__:expired"


def expire_event_handler(message):  # pragma: no cover
    try:
        logger.debug(f"Got a message from Redis: {message}.")
        initial_key = message["data"].decode("utf-8").strip()
        _, prefix, chat_id = initial_key.split(":")
        logger.debug(f"Session Type: {prefix}. Chat ID: {chat_id}.")
        redis_key = f"{prefix}:{chat_id}"
        prefix = RedisPrefixes(prefix)
        logger.debug(f"Getting the value from Redis: {redis_key}.")
        data = json.loads(redis_client.get(redis_key).decode("utf-8"))
        logger.debug(f"Got the value from Redis: {data}.")
        datastore_manager = DatastoreManager()
        match prefix:
            case RedisPrefixes.CHAT_SESSION:
                save_chat_session_to_datastore(data, datastore_manager)
            case RedisPrefixes.USER_SESSION:
                save_user_session_to_datastore(chat_id, data, datastore_manager)
                ...  # ToDo: save to the Datastore
        # Once we got to know the value we remove it from Redis and do whatever required
        logger.debug(f"Deleting used data from Redis: {redis_key}.")
        redis_client.delete(redis_key)
        logger.debug(f"Data were successfully deleted from Redis: {redis_key}.")
    except Exception as exp:
        logger.debug("Got an exception: ", exp)


def save_chat_session_to_datastore(data: dict, datastore_manager: DatastoreManager):
    """Saves the chat_session object to the Datastore"""
    logger.debug("Saving chat session to the Datastore: ", data)
    chat, key, created = datastore_manager.update_or_create_chat_entity(data)
    logger.debug(f"Data were successfully saved to the datastore. Data was created: {created}."
                 f" Chat: {chat}. Key: {key}.")


def save_user_session_to_datastore(chat_id: str, data: dict, datastore_manager: DatastoreManager):
    """Saves the user_session object to the Datastore"""
    logger.debug(chat_id, data)

logger.info("Start listening to Redis")
pubsub = redis_client.pubsub()
logger.info("Subscribing to Redis")
pubsub.psubscribe(**{EXPIRED_KEY_EVENT: expire_event_handler})
logger.info("Running Redis in thread")
pubsub.run_in_thread(sleep_time=0.01)
logger.info("Done")
