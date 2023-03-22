import logging
import typing as t

from google.cloud import datastore
from telegram import Update
from telegram.constants import ChatType
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

from core.constants import TelegramMessages
from core.sessions import ChatSession, UserSession
from core.commands import ASK_KNOWLEDGE_GOD
from core.open_ai import generate_response, num_tokens_from_messages, ChatModel, UserTokenManager
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
        try:
            chat_id = update.effective_chat.id
            if str(chat_id) not in [settings.MANAGED_CHAT_ID, settings.SUPERUSER_CHAT_ID]:
                # ToDo: change after production
                await context.bot.send_message(chat_id=update.effective_chat.id,
                                               text='Sorry. That bot is not working for you. '
                                                    'You can ask @ultimatesoul to change that')
                return
            if need_to_split and not input_text:
                input_text = ' '.join(update.message.text.split()[1:])
            if not input_text:
                input_text = update.message.text
            logging.info("Input text: {}".format(input_text))
            chat_session = ChatSession(entity_id=update.effective_chat.id, update=update)
            user_session = UserSession(entity_id=update.effective_user.id, update=update)
            chat: t.Union[dict, datastore.Entity] = chat_session.get()
            user: t.Union[dict, datastore.Entity] = user_session.get()
            messages = [chat.get('system_message')] + chat.get('messages')
            model: ChatModel = chat.get('current_model')
            messages_tokens_num = num_tokens_from_messages(chat.get('messages'), model=model)
            if messages_tokens_num > chat.get('max_tokens'):
                ...  # ToDo: add truncation of first messages
            user_manager = UserTokenManager(user=user, chat=chat)
            is_user_allowed_to_talk = user_manager.can_user_ask_ai()
            if is_user_allowed_to_talk:

                response = await generate_response(messages=messages,
                                                   model=chat.get('current_model'),
                                                   max_tokens=chat.get('max_tokens'),
                                                   temperature=chat.get('temperature'))

                logging.info("Response: {}".format(response))
                response = response.choices[0].message.content
            else:
                response = TelegramMessages.construct_message(
                    message=TelegramMessages.LOW_BALANCE,
                    balance=user.get('current_balance'),
                    price=user_manager.dollars_for_prompt * 100
                )
                # ToDo: calculate price for prompt and completion price and save it to the user account entity
            await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
        except Exception as e:
            logging.exception('During ask_knowledge_god something went wrong')
            response = "I'm sorry, I have some problems with my brain. Please, try again later."
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
