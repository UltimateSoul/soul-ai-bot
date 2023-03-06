"""
    This file holds the logic for interacting with the OpenAI API.
"""

import openai

from core.settings import Settings

settings = Settings()

# Set up OpenAI API
openai.api_key = settings.OPEN_AI_API_KEY


# Define function to generate response with OpenAI API
def generate_response(message):
    prompt = f"User: {message}\nAI:"
    response = openai.ChatCompletion.create(
        engine=settings.OPEN_AI_ENGINE,
        prompt=prompt,
        max_tokens=100,
        n=1,
        stop=None,
        temperature=0.5,
    )
    return response.choices[0].text.strip()
