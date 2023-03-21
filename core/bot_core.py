import logging

from telegram import Update
from telegram.constants import ChatType
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

from core.chat_session import ChatSession
from core.commands import ASK_KNOWLEDGE_GOD
from core.settings import Settings

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)  # ToDo: move that to main.py

logger = logging.getLogger(__name__)
settings = Settings()


class SoulAIBot:
    """This class is responsible for the bot logic."""

    async def ask_knowledge_god(self, update: Update, context: ContextTypes.DEFAULT_TYPE, need_to_split=True,
                                input_text=None):
        if need_to_split and not input_text:
            input_text = ' '.join(update.message.text.split()[1:])
        if not input_text:
            input_text = update.message.text
        logging.info("Input text: {}".format(input_text))
        chat_session = ChatSession(chat_id=update.effective_chat.id, update=update, context=context)
        chat = chat_session.get()

        # response = await generate_response(input_text)
        response = "Hello, world!"
        logging.info("Response: {}".format(response))
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)

    async def ai_dialogue(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        effective_chat = update.effective_chat
        match effective_chat.type:
            case ChatType.PRIVATE:
                await self.ask_knowledge_god(update, context, need_to_split=False)
            case ChatType.GROUP:
                message = update.message
                for member in message.new_chat_members:
                    welcome_message = f"{member.first_name} присоединился к группе!"  # ToDo: add dynamic language
                    # ToDo: add member to the chat entity in Datastore
                    await self.ask_knowledge_god(update, context, need_to_split=False, input_text=welcome_message)
                message = update.message
                removed_member = message.left_chat_member
                if removed_member:
                    # ToDo: remove member from the chat entity in Datastore
                    goodbye_message = f"{removed_member.first_name} покинул телеграм канал, скажи пока."
                    # ToDo: add dynamic language
                    await self.ask_knowledge_god(update, context, need_to_split=False, input_text=goodbye_message)


if __name__ == '__main__':
    application = ApplicationBuilder() \
        .token(settings.TELEGRAM_BOT_API_TOKEN).build()  # ToDo: add normal settings get
    soul_ai_bot = SoulAIBot()

    application.add_handler(CommandHandler(ASK_KNOWLEDGE_GOD, soul_ai_bot.ask_knowledge_god))
    application.add_handler(MessageHandler(filters.ALL, soul_ai_bot.ai_dialogue))
    application.run_polling()
