import asyncio
import logging
import typing as t

from telegram import Update
from telegram.constants import ChatType
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

from core.constants import TelegramMessages, ChatModel, OPEN_AI_TIMEOUT
from core.datastore import UserAccount, Chat
from core.exceptions import TooManyTokensException, UnsupportedModelException
from core.models import pydantic_model_per_gpt_model, Message, GPT_3_5_Turbo
from core.sessions import ChatSession, UserSession
from core.commands import ASK_KNOWLEDGE_GOD
from core.open_ai import generate_response, num_tokens_from_messages, UserTokenManager
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
            chat: Chat = chat_session.get()
            user_account: UserAccount = user_session.get()
            chat_messages = chat.dict()['messages']
            messages = [chat.system_message.dict()] + chat_messages
            model: ChatModel = chat.current_model
            messages_tokens_num = num_tokens_from_messages(chat_messages, model=model)
            if messages_tokens_num > chat.max_tokens:
                while messages_tokens_num > chat.max_tokens:
                    messages.pop(0)
                    messages_tokens_num = num_tokens_from_messages(messages, model=model)
            user_manager = UserTokenManager(user_account=user_account, chat=chat)
            is_user_allowed_to_talk = user_manager.can_user_ask_ai()
            if is_user_allowed_to_talk:
                open_ai_response = await asyncio.wait_for(generate_response(messages=messages,
                                                                            model=chat.current_model,
                                                                            max_tokens=chat.max_tokens,
                                                                            temperature=chat.temperature),
                                                          timeout=OPEN_AI_TIMEOUT)

                logging.info("Response: {}".format(open_ai_response))
                response = open_ai_response.choices[0].message.content
                await post_ai_response_logic(open_ai_response=open_ai_response,
                                             response=response,
                                             chat=chat,
                                             user_account=user_account,
                                             chat_session=chat_session,
                                             user_session=user_session)
            else:
                response = TelegramMessages.construct_message(
                    message=TelegramMessages.LOW_BALANCE,
                    balance=user_account.current_balance,
                    price=user_manager.dollars_for_prompt * 100
                )
                # ToDo: calculate price for prompt and completion price and save it to the user account entity
            await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
        except asyncio.TimeoutError as e:
            logging.exception('During ask_knowledge_god something timeout exception raised')
            response = "Sorry, i was trying to get response from OpenAI, but it took too long. Please, try again later."
            # ToDo: remove last message from chat_session
            await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
        except TooManyTokensException as e:
            logging.exception('During ask_knowledge_god something went wrong')
            response = "Sorry, I can't answer that. Too many tokens."
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


async def post_ai_response_logic(open_ai_response, response, chat, user_account, chat_session, user_session):
    logging.info("Response: {}".format(open_ai_response))
    usage: dict = open_ai_response['usage']
    pd_model = pydantic_model_per_gpt_model[
        chat.current_model](**usage)
    match chat.current_model:
        case ChatModel.CHAT_GPT_3_5_TURBO:
            user_account.model_token_usage.gpt_3_5_turbo += pd_model

        case ChatModel.CHAT_GPT_3_5_TURBO_0301:
            user_account.model_token_usage.gpt_3_5_turbo_0301 += pd_model
        case ChatModel.CHAT_GPT_4:
            user_account.model_token_usage.gpt_4 += pd_model
        case _:
            raise UnsupportedModelException("That model is unsupported.")
    user_account.current_balance -= pd_model.calculate_price() * 100
    assistant_message = {
        'role': 'assistant',
        'content': response,
    }
    chat.messages.append(Message(**assistant_message))
    chat_session.set(entity=chat.dict())
    user_session.set(entity=user_account.dict())


if __name__ == '__main__':
    application = ApplicationBuilder() \
        .token(settings.TELEGRAM_BOT_API_TOKEN).build()  # ToDo: add normal settings get
    soul_ai_bot = SoulAIBot()

    application.add_handler(CommandHandler(ASK_KNOWLEDGE_GOD, soul_ai_bot.ask_knowledge_god))
    application.add_handler(MessageHandler(filters.ALL, soul_ai_bot.ai_dialogue))
    application.run_polling()
