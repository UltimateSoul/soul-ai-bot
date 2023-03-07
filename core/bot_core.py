import logging

import telegram
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext

from core.open_ai import generate_response
from core.settings import Settings

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
settings = Settings()
bot = telegram.Bot(token=settings.TELEGRAM_BOT_API_TOKEN)
updater = Updater(bot=bot)


# Define command handlers
def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    update.message.reply_text('')


def help(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text('You can use the /start command to get started!')


def echo(update: Update, context: CallbackContext) -> None:
    """Echo the user message."""
    update.message.reply_text(update.message.text)


def ask_knowledge_god(update: Update, context: CallbackContext) -> None:
    """Send a message to the OpenAI API and return the response."""
    # Get the input text from the message
    input_text = ' '.join(context.args)
    if not input_text:
        update.message.reply_text('Please provide an input text.')
        return

    # Call the OpenAI API to generate a response
    knowledge_god_answer = generate_response(input_text)

    # Send the response back to the user
    update.message.reply_text(knowledge_god_answer)


# Get the dispatcher to register handlers

dispatcher = updater.dispatcher

# Add command handlers
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("help", help))
dispatcher.add_handler(CommandHandler("ask_knowledge_god", ask_knowledge_god))

# Add message handler
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))