"""
That module manages creation all the necessary connections within the application, alongside with the saving data from
the Memorystore to the Datastore when the application is about to stop.
"""
import redis

from core.settings import Settings

settings = Settings()

# Set up the Memorystore (Redis) connection
redis_client = redis.Redis(host=settings.MEMORY_STORE_SETTINGS.HOST,
                           port=settings.MEMORY_STORE_SETTINGS.PORT)
