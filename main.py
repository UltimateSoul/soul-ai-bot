from fastapi import FastAPI, Request
import telegram

from core import commands
from core.open_ai import generate_response
from core.settings import Settings

app = FastAPI()
settings = Settings()
bot = telegram.Bot(settings.TELEGRAM_BOT_API_TOKEN)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/" + settings.TELEGRAM_BOT_API_TOKEN)
async def handle_telegram_request(request: Request):
    data = await request.json()
    message = data['message']['text']

    if message.startswith(commands.GOD_LISTEN_US):
        ...  # ToDo: Implement this

    if message.startswith(commands.ASK_KNOWLEDGE_GOD):
        # Extract the input text from the message
        input_text = ' '.join(message.split()[1:])
        if not input_text:
            await bot.send_message(chat_id=data['message']['chat']['id'], text='Please provide an input text.')
            return

        # Call the OpenAI API to generate a response
        response = await generate_response(input_text)

        # Send the response back to the user
        await bot.send_message(chat_id=data['message']['chat']['id'], text=response)
    else:
        ...  # ToDo: save context messages in the database

    return {'response': 'success'}
