"""
That module manages creation all the necessary connections within the application, alongside with the saving data from
the Memorystore to the Datastore when the application is about to stop.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
import google.auth
from google.cloud import datastore
import redis

from core.settings import Settings

settings = Settings()

datastore_client = None
redis_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global datastore_client, redis_client

    # Set up the Datastore connection
    credentials, project_id = google.auth.default()
    datastore_client = datastore.Client(project=project_id, credentials=credentials)

    # Set up the Memorystore (Redis) connection
    redis_client = redis.Redis(host=settings.MEMORY_STORE_SETTINGS.HOST,
                               port=settings.MEMORY_STORE_SETTINGS.PORT,
                               db=settings.MEMORY_STORE_SETTINGS.DB)

    yield

    # Close the Memorystore (Redis) connection
    # ToDo: Save data from the Memorystore to the Datastore
    redis_client.close()
