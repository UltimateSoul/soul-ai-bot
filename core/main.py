import logging
from contextlib import asynccontextmanager
from http import HTTPStatus

import backoff
import redis
import telegram
from fastapi import FastAPI, Request
from pydantic import BaseModel
from starlette.responses import Response, PlainTextResponse
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, filters, MessageHandler, \
    CallbackContext, ExtBot, ContextTypes, TypeHandler

from core import commands
from core.bot_core import SoulAIBot
from core.datastore import DatastoreManager
from core.settings import Settings

application = None
# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
settings = Settings()

app = FastAPI()


@backoff.on_exception(backoff.expo, telegram.error.RetryAfter, max_time=60)
async def set_webhook():
    if settings.TELEGRAM_WEBHOOK_URL != "None":
        logger.info(f"Setting webhook by URL {settings.TELEGRAM_WEBHOOK_URL}/webhook...")
        await application.bot.set_webhook(url=f"{settings.TELEGRAM_WEBHOOK_URL}/webhook")
        logger.info("Webhook set!")
    else:
        logger.info("Webhook URL is None, skipping...")


@app.on_event("startup")
async def on_start():
    """Start the bot."""
    context_types = ContextTypes(context=CustomContext)
    # Here we set updater to None because we want our custom webhook server to handle the updates
    # and hence we don't need an Updater instance
    global application
    application = (
        Application.builder()
        .token(settings.TELEGRAM_BOT_API_TOKEN)
        .updater(None)
        .context_types(context_types)
        .build()
    )
    application.bot_data["admin_chat_id"] = settings.ADMIN_CHAT_ID
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
    application.add_handler(CommandHandler(commands.CLEAR_CONTEXT, soul_ai_bot.clear_context))
    application.add_handler(CommandHandler(commands.ADD_MONEY, soul_ai_bot.add_money))
    application.add_handler(CallbackQueryHandler(soul_ai_bot.query_handler))
    application.add_handler(CommandHandler(commands.ASK_KNOWLEDGE_GOD, soul_ai_bot.ask_knowledge_god))
    application.add_handler(MessageHandler(filters.ALL, soul_ai_bot.ai_dialogue))
    application.add_handler(TypeHandler(type=WebhookUpdate, callback=webhook_update))

    await application.initialize()
    await application.start()
    await set_webhook()
    webhook_info = await application.bot.get_webhook_info()
    logger.info(f"Webhook info: {webhook_info}")


@app.on_event("shutdown")
async def on_shutdown():
    """Stop the bot."""
    logger.info("Stopping the application")
    if isinstance(application, Application):
        await application.stop()
        await application.shutdown()


class WebhookUpdate(BaseModel):
    """Simple pydantic class to wrap a custom update type"""

    user_id: int
    payload: str


class CustomContext(CallbackContext[ExtBot, dict, dict, dict]):
    """
    Custom CallbackContext class that makes `user_data` available for updates of type
    `WebhookUpdate`.
    """

    @classmethod
    def from_update(
            cls,
            update: object,
            application: "Application",
    ) -> "CustomContext":
        if isinstance(update, WebhookUpdate):
            return cls(application=application, user_id=update.user_id)
        return super().from_update(update, application)  # noqa


async def webhook_update(update: WebhookUpdate, context: CustomContext) -> None:
    """Callback that handles the custom updates."""
    chat_member = await context.bot.get_chat_member(chat_id=update.user_id, user_id=update.user_id)
    payloads = context.user_data.setdefault("payloads", [])
    payloads.append(update.payload)
    combined_payloads = "</code>\n• <code>".join(payloads)
    text = (
        f"The user {chat_member.user.mention_html()} has sent a new payload. "
        f"So far they have sent the following payloads: \n\n• <code>{combined_payloads}</code>"
    )
    await context.bot.send_message(
        chat_id=context.bot_data["admin_chat_id"], text=text, parse_mode=ParseMode.HTML
    )


@app.post("/webhook")
async def telegram(request: Request) -> Response:
    """Handle incoming Telegram updates by putting them into the `update_queue`"""
    await application.update_queue.put(
        Update.de_json(data=await request.json(), bot=application.bot)
    )
    return Response()


@app.get("/healthcheck")
async def health(_: Request) -> PlainTextResponse:
    """For the health endpoint, reply with a simple plain text message."""
    return PlainTextResponse(content="The bot is still running fine :)")


@app.api_route("/custom_updates", methods=["GET", "POST"])
async def custom_updates(request: Request) -> PlainTextResponse:
    """
    Handle incoming webhook updates by also putting them into the `update_queue` if
    the required parameters were passed correctly.
    """
    try:
        user_id = int(request.query_params["user_id"])
        payload = request.query_params["payload"]
    except KeyError:
        return PlainTextResponse(
            status_code=HTTPStatus.BAD_REQUEST,
            content="Please pass both `user_id` and `payload` as query parameters.",
        )
    except ValueError:
        return PlainTextResponse(
            status_code=HTTPStatus.BAD_REQUEST,
            content="The `user_id` must be a string!",
        )

    await application.update_queue.put(WebhookUpdate(user_id=user_id, payload=payload))
    return PlainTextResponse("Thank you for the submission! It's being forwarded.")
