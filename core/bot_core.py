import asyncio
import logging
import typing as t
from functools import wraps

import telegram
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatType, ChatAction
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler

from core.constants import TelegramMessages, ChatModel, OPEN_AI_TIMEOUT, SupportedModels
from core.datastore import UserAccount, Chat
from core.exceptions import TooManyTokensException, UnsupportedModelException
from core.models import pydantic_model_per_gpt_model, Message
from core.sessions import ChatSession, UserSession
from core import commands
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

    @staticmethod
    def send_action(action):
        """Sends `action` while processing func command."""

        def decorator(func):
            @wraps(func)
            async def command_func(cls, update, context, *args, **kwargs):
                await context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=action)
                return await func(cls, update, context, *args, **kwargs)

            return command_func

        return decorator

    @send_action(ChatAction.TYPING)
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Starts the bot."""

        buttons = [
            [
                InlineKeyboardButton("Discover the commands", callback_data=commands.HELP),
            ],
            [
                InlineKeyboardButton("Get your current balance", callback_data=commands.GET_BALANCE),
                InlineKeyboardButton("Get your token usage", callback_data=commands.GET_TOKEN_USAGE),
            ],
            [
                InlineKeyboardButton("Get tokens number for you input message",
                                     callback_data=commands.GET_TOKENS_FOR_MESSAGE),
            ],
            [
                InlineKeyboardButton("Set maximum tokens number", callback_data=commands.SET_MAX_TOKENS),
                InlineKeyboardButton("Set temperature for the model", callback_data=commands.SET_TEMPERATURE),
            ],
            [
                InlineKeyboardButton("Set new GPT model", callback_data=commands.SET_MODEL),
                InlineKeyboardButton("Get current system message", callback_data=commands.SET_SYSTEM_MESSAGE),
            ],
            [
                InlineKeyboardButton("Start chat with i", callback_data=commands.ASK_KNOWLEDGE_GOD),
            ],
        ]

        reply_markup = InlineKeyboardMarkup(buttons)
        text = telegram.helpers.escape_markdown(
            TelegramMessages.START_PART_1.format(username=update.effective_user.username), 2)
        full_start_text = text + TelegramMessages.START_PART_2
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       reply_markup=reply_markup,
                                       parse_mode=telegram.constants.ParseMode.MARKDOWN_V2,
                                       text=full_start_text)

    @send_action(ChatAction.TYPING)
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Shows the help message."""

        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=TelegramMessages.HELP)

    @send_action(ChatAction.TYPING)
    async def get_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_session = UserSession(entity_id=update.effective_chat.id, update=update)
        user_account: UserAccount = user_session.get()
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f"Your current balance is {user_account.current_balance} "
                                            f"cents or {user_account.current_balance / 100} dollars")

    @send_action(ChatAction.TYPING)
    async def get_token_usage(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_session = UserSession(entity_id=update.effective_chat.id, update=update)
        user_account: UserAccount = user_session.get()
        token_usage = user_account.model_token_usage
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=TelegramMessages.TOKEN_USAGE.format(token_usage=token_usage),
                                       parse_mode=telegram.constants.ParseMode.MARKDOWN_V2)

    @send_action(ChatAction.TYPING)
    async def get_tokens_for_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = ' '.join(update.message.text.split()[1:])
        if not message:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text='Please, send me a message to get the number of tokens for it')
        else:
            text = ""
            try:
                chat_session = ChatSession(entity_id=update.effective_chat.id, update=update)
                chat: Chat = chat_session.get()
                system_message = chat.system_message
                current_model = chat.open_ai_config.current_model

                messages = [
                    {
                        'role': 'user',
                        'content': message
                    }
                ]

                message_token_number = num_tokens_from_messages(messages=messages, model=current_model)
                system_message_token_number = num_tokens_from_messages(messages=[system_message.dict()],
                                                                       model=current_model)
                total_token_number = message_token_number + system_message_token_number
                message_model = pydantic_model_per_gpt_model[current_model](total_tokens=message_token_number)
                system_message_model = pydantic_model_per_gpt_model[current_model](
                    total_tokens=system_message_token_number)
                system_message_cost = system_message_model.calculate_price() * 100  # cents
                message_cost = message_model.calculate_price() * 100  # cents
                total_price = message_cost + system_message_cost
                total_price = telegram.helpers.escape_markdown('{:.7f}'.format(total_price), 2)
                message_cost = telegram.helpers.escape_markdown('{:.7f}'.format(message_cost), 2)
                system_message_cost = telegram.helpers.escape_markdown('{:.7f}'.format(system_message_cost), 2)
                escaped_system_message = telegram.helpers.escape_markdown(system_message.content, 2)
                text = f'Number of all the tokens for your message alongside with systen one is *{total_token_number}*, ' \
                       f'it will cost you *{total_price}* cents' \
                       f'Don\\`t forget that in that cost is included the system message' \
                       f' You can change the system message with _set_system_message_ command ' \
                       f'The current system message is: *{escaped_system_message}*, number of tokens for it is ' \
                       f'{system_message_token_number}, it will cost you {system_message_cost} cents ' \
                       f'Token number for your message is {message_token_number}, it will cost you {message_cost} cents'

                await context.bot.send_message(chat_id=update.effective_chat.id,
                                               text=text,
                                               parse_mode=telegram.constants.ParseMode.MARKDOWN_V2)
            except Exception:
                logging.exception(text)
                await context.bot.send_message(chat_id=update.effective_chat.id,
                                               text='Sorry, something went wrong. Please, try again later')

    @send_action(ChatAction.TYPING)
    async def set_max_tokens(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            chat_session = ChatSession(entity_id=update.effective_chat.id, update=update)
            chat: Chat = chat_session.get()
            max_tokens = int(update.message.text.split()[1])
            system_message = chat.system_message
            system_message_token_number = num_tokens_from_messages(messages=[system_message.dict()],
                                                                   model=chat.open_ai_config.current_model)
            if max_tokens < system_message_token_number + 100:
                await context.bot.send_message(chat_id=update.effective_chat.id,
                                               text='Sorry, but the number of tokens you want to set is too small. '
                                                    f'Your system message has {system_message_token_number} tokens. '
                                                    f'You need to set at least {system_message_token_number + 100}'
                                                    f' tokens to proceed')
            else:
                chat.open_ai_config.max_tokens = max_tokens
                chat_session.set(chat.dict())
                await context.bot.send_message(chat_id=update.effective_chat.id,
                                               text=f'You have successfully set the number of tokens to {max_tokens}')
        except IndexError:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text='Please, send me a number of tokens')

        except ValueError:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text='Please, send me a number of tokens')

        except Exception:
            logging.exception('Error in set_max_tokens')
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text='Sorry, something went wrong. Please, try again later')

    @send_action(ChatAction.TYPING)
    async def set_temperature(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            chat_session = ChatSession(entity_id=update.effective_chat.id, update=update)
            chat: Chat = chat_session.get()
            temperature = float(update.message.text.split()[1])
            if temperature < 0.0 or temperature > 1.0:
                await context.bot.send_message(chat_id=update.effective_chat.id,
                                               text='Please, send me a number between 0.0 and 1.0')
            else:
                chat.open_ai_config.temperature = temperature
                chat_session.set(chat.dict())
                await context.bot.send_message(chat_id=update.effective_chat.id,
                                               text=f'You have successfully set the temperature to {temperature}')

        except IndexError:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text='Please, send me a number between 0.0 and 1.0')

        except ValueError:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text='Please, leave me a number between 0.0 and 1.0')

        except Exception:
            logging.exception('Error in set_temperature')
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text='Sorry, something went wrong. Please, try again later')

    @send_action(ChatAction.TYPING)
    async def set_model(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            model_buttons = [InlineKeyboardButton(model.value, callback_data=model.value) for model in
                             SupportedModels]

            reply_markup = InlineKeyboardMarkup([model_buttons])
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           reply_markup=reply_markup,
                                           text='Please, choose the model you want to use')

        except Exception:
            logging.exception('Error in set_model')
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text='Sorry, something went wrong. Please, try again later')

    @send_action(ChatAction.TYPING)
    async def set_model_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            chat_session = ChatSession(entity_id=update.effective_chat.id, update=update)
            chat: Chat = chat_session.get()
            model = SupportedModels(update.callback_query.data)
            chat.open_ai_config.current_model = ChatModel(model.value)
            chat_session.set(chat.dict())
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=f'You have successfully set the model to '
                                                f'{chat.open_ai_config.current_model.value}')

        except Exception:
            logging.exception('Error in set_model_callback')
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text='Sorry, something went wrong. Please, try again later')

    @send_action(ChatAction.TYPING)
    async def set_system_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            chat_session = ChatSession(entity_id=update.effective_chat.id, update=update)
            chat: Chat = chat_session.get()
            system_message = update.message.text.split()[1]
            chat.system_message = Message(content=system_message,
                                          role='system')
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text='You have successfully set the system message!')
        except IndexError:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text='Please send me a system message you want to set.')

        except Exception:
            logging.exception('Error in set_system_message')
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text='Sorry, something went wrong. Please, try again later')

    @send_action(ChatAction.TYPING)
    async def get_system_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            chat_session = ChatSession(entity_id=update.effective_chat.id, update=update)
            chat: Chat = chat_session.get()
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=chat.system_message.dict().get('content', 'No system message set'))

        except Exception:
            logging.exception('Error in get_system_message')
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text='Sorry, something went wrong. Please, try again later')

    @send_action(ChatAction.TYPING)
    async def ask_knowledge_god(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            chat_id = update.effective_chat.id
            managed_chat_ids = settings.MANAGED_CHAT_IDS.split(',')
            if str(chat_id) not in [*managed_chat_ids, settings.SUPERUSER_CHAT_ID]:
                # ToDo: change after production
                await context.bot.send_message(chat_id=update.effective_chat.id,
                                               text='Sorry. That bot is not working for you. '
                                                    'You can ask @ultimatesoul to change that')
                return

            chat_session = ChatSession(entity_id=update.effective_chat.id, update=update)
            user_session = UserSession(entity_id=update.effective_user.id, update=update)
            chat: Chat = chat_session.get()
            user_account: UserAccount = user_session.get()
        except Exception as e:
            logging.exception('During ask_knowledge_god something went wrong')
            response = "I'm sorry, I have some problems with my brain. Please, try again later."
            await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
            return
        try:
            messages = get_normalized_chat_messages(chat=chat, chat_session=chat_session)

            user_manager = UserTokenManager(user_account=user_account, chat=chat)
            is_user_allowed_to_talk = user_manager.can_user_ask_ai()
            if is_user_allowed_to_talk:

                open_ai_response = await asyncio.wait_for(generate_response(messages=messages,
                                                                            model=chat.open_ai_config.current_model,
                                                                            max_tokens=chat.open_ai_config.max_tokens,
                                                                            temperature=chat.open_ai_config.temperature),
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
                    price=round(user_manager.dollars_for_prompt * 100, 4)
                )
            await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
        except asyncio.TimeoutError:
            logging.exception('During ask_knowledge_god something timeout exception raised')
            response = "Sorry, i was trying to get response from OpenAI, but it took too long. Please, try again later."
            chat_data = chat.dict()
            chat_data['messages'].pop()  # get last user message
            chat_session.set(chat_data)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
        except TooManyTokensException:
            logging.exception('During ask_knowledge_god something went wrong')
            response = "Sorry, I can't answer that. Too many tokens."
            await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
        except Exception:
            logging.exception('During ask_knowledge_god something went wrong')
            response = "I'm sorry, I have some problems with my brain. Please, try again later."
            await context.bot.send_message(chat_id=update.effective_chat.id, text=response)

    async def ai_dialogue(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        effective_chat = update.effective_chat
        match effective_chat.type:
            case ChatType.PRIVATE:
                await self.ask_knowledge_god(update, context)
            case ChatType.SUPERGROUP:
                if update.message.text:
                    is_bot_was_mentioned = '@' + context.bot.username in update.message.text
                    if is_bot_was_mentioned:
                        await self.ask_knowledge_god(update, context)

    async def query_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query

        match query.data:
            case commands.HELP:
                await self.help(update, context)
            case commands.GET_BALANCE:
                await self.get_balance(update, context)
            case commands.GET_TOKEN_USAGE:
                await self.get_token_usage(update, context)
            # case commands.MANAGE_CHAT:
            #     await self.manage_chat(update, context)  # ToDo: implement
            case commands.SET_MAX_TOKENS:
                await self.set_max_tokens(update, context)  # ToDo: implement
            case commands.SET_TEMPERATURE:
                await self.set_temperature(update, context)  # ToDo: implement
            case commands.SET_MODEL:
                await self.set_model(update, context)  # ToDo: implement
            case commands.SET_SYSTEM_MESSAGE:
                await self.set_system_message(update, context)  # ToDo: implement
            case commands.ASK_KNOWLEDGE_GOD:
                update.message.text = f"Hi!"
                await self.ask_knowledge_god(update, context)
            case SupportedModels.CHAT_GPT_3_5_TURBO_0301.value | SupportedModels.CHAT_GPT_4_0314.value:
                await self.set_model_callback(update, context)
            case _:
                await update.callback_query.answer(text="Sorry, I don't know what to do with this button")


def get_normalized_chat_messages(chat: Chat, chat_session: ChatSession) -> t.List[dict[t.Any, t.Any]]:
    chat_data = chat.dict()
    chat_messages = chat_data['messages']
    model: ChatModel = chat.open_ai_config.current_model
    messages_tokens_num = num_tokens_from_messages(chat_messages, model=model)
    system_message = chat.system_message.dict()
    system_message_tokens_num = num_tokens_from_messages([system_message], model=model)
    if system_message_tokens_num > chat.open_ai_config.max_tokens:  # Make sure that infinity loop is impossible
        raise TooManyTokensException(f"System message is too long. {system_message_tokens_num}."
                                     f" Max input tokens configured for that that is: {chat.open_ai_config.max_tokens}")
    all_messages_tokens_num = messages_tokens_num + system_message_tokens_num
    if all_messages_tokens_num > chat.open_ai_config.max_tokens:
        try:
            while all_messages_tokens_num > chat.open_ai_config.max_tokens:
                # ToDo: add validation for max_tokens and system message, because without the infinity loop is possible
                chat_messages.pop(0)
                all_messages_tokens_num = num_tokens_from_messages(chat_messages,
                                                                   model=model) + system_message_tokens_num
        finally:
            chat_session.set(chat_data)
    return [system_message] + chat_messages


async def post_ai_response_logic(open_ai_response, response: str, chat: Chat, user_account: UserAccount,
                                 chat_session: ChatSession, user_session: UserSession):
    logging.info("Response: {}".format(open_ai_response))
    usage: dict = open_ai_response['usage']
    pd_model = pydantic_model_per_gpt_model[
        chat.open_ai_config.current_model](**usage)
    match chat.open_ai_config.current_model:
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
    application.add_handler(CommandHandler(commands.GET_BALANCE, soul_ai_bot.get_balance))
    application.add_handler(CommandHandler(commands.GET_TOKEN_USAGE, soul_ai_bot.get_token_usage))
    application.add_handler(CommandHandler(commands.START, soul_ai_bot.start))
    application.add_handler(CommandHandler(commands.HELP, soul_ai_bot.help))
    application.add_handler(CommandHandler(commands.GET_TOKENS_FOR_MESSAGE, soul_ai_bot.get_tokens_for_message))
    application.add_handler(CommandHandler(commands.SET_MAX_TOKENS, soul_ai_bot.set_max_tokens))
    application.add_handler(CommandHandler(commands.SET_TEMPERATURE, soul_ai_bot.set_temperature))
    application.add_handler(CommandHandler(commands.SET_MODEL, soul_ai_bot.set_model))
    application.add_handler(CommandHandler(commands.SET_SYSTEM_MESSAGE, soul_ai_bot.set_system_message))
    application.add_handler(CommandHandler(commands.GET_SYSTEM_MESSAGE, soul_ai_bot.get_system_message))
    application.add_handler(CallbackQueryHandler(soul_ai_bot.query_handler))
    application.add_handler(CommandHandler(commands.ASK_KNOWLEDGE_GOD, soul_ai_bot.ask_knowledge_god))
    application.add_handler(MessageHandler(filters.ALL, soul_ai_bot.ai_dialogue))
    application.run_polling()
