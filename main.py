from fastapi import FastAPI, Request
import telegram

from core import commands
from core.open_ai import generate_response
from core.settings import Settings

app = FastAPI()
settings = Settings()
