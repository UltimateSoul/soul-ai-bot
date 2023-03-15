import logging

from telegram import Update
from telegram.constants import ChatType
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

from core.commands import ASK_KNOWLEDGE_GOD
from core.datastore import DatastoreManager
from core.open_ai import generate_response
from core.settings import Settings

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)
settings = Settings()


class SoulAIBot:
    """This class is responsible for the bot logic."""

    async def ask_knowledge_god(self, update: Update, context: ContextTypes.DEFAULT_TYPE, need_to_split=True, input_text=None):
        if need_to_split and not input_text:
            input_text = ' '.join(update.message.text.split()[1:])
        if not input_text:
            input_text = update.message.text
        logging.info("Input text: {}".format(input_text))
        user_data = update.effective_user.to_dict()
        datastore_manager = DatastoreManager()
        chat_entity = await datastore_manager.get_or_create_chat_entity(update, context)
        chat_message = datastore_manager.create_chat_message(user_data, )
        response = await generate_response(input_text)
        logging.info("Response: {}".format(response))
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)


    async def ai_private_chat_dialogue(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        effective_chat = update.effective_chat
        if effective_chat.type is ChatType.PRIVATE:
            await self.ask_knowledge_god(update, context, need_to_split=False)
        message = update.message
        for member in message.new_chat_members:
            welcome_message = f"{member.first_name} присоединился к группе!"
            # ToDo: add member to the chat entity in Datastore
            await self.ask_knowledge_god(update, context, need_to_split=False, input_text=welcome_message)
        message = update.message
        removed_member = message.left_chat_member
        if removed_member:
            # ToDo: remove member from the chat entity in Datastore
            goodbye_message = f"{removed_member.first_name} покинул телеграм канал, скажи пока."  # ToDo: add dynamic language
            await self.ask_knowledge_god(update, context, need_to_split=False, input_text=goodbye_message)

    async def save_user_data(self, update: Update):
        user = update.effective_user
        chat = update.effective_chat

        username = user.username
        firstname = user.first_name
        lastname = user.last_name
        chat_id = chat.id
        is_private = chat.type == ChatType.PRIVATE
        datastore_manager = DatastoreManager()
        datastore_manager.store_data(username, firstname, lastname, chat_id, is_private)


if __name__ == '__main__':
    application = ApplicationBuilder() \
        .token(settings.TELEGRAM_BOT_API_TOKEN).build()  # ToDo: add normal settings get
    soul_ai_bot = SoulAIBot()

    application.add_handler(CommandHandler(ASK_KNOWLEDGE_GOD, soul_ai_bot.ask_knowledge_god))
    application.add_handler(MessageHandler(filters.ALL, soul_ai_bot.ai_private_chat_dialogue))
    application.run_polling()
