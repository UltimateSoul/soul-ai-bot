"""
    Bot Core

    This is the core of the telegram bot. It handles all the commands and events.
"""
import telegram

from core.settings import Settings
from core.open_ai import generate_response

settings = Settings()

bot_token = settings.TELEGRAM_BOT_API_TOKEN
bot = telegram.Bot(bot_token)


def handle_message(update, context):
    message = update.message.text
    chat_id = update.message.chat_id
    response = generate_response(message)
    bot.send_message(chat_id=chat_id, text=response)

