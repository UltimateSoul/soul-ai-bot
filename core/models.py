import typing as t

from pydantic import BaseModel

from core.constants import ChatModel, DEFAULT_MAX_TOKENS, DEFAULT_MODEL_TEMPERATURE, MODEL_PRICING
from core.exceptions import TooManyTokensException


class GPT_3_5_Turbo(BaseModel):
    total_tokens: int = 0

    def calculate_price(self):
        token_coefficient = self.total_tokens / 1000
        return token_coefficient * MODEL_PRICING[ChatModel.CHAT_GPT_3_5_TURBO_0301]['price_per_1k_tokens']

    def __add__(self, other):
        self.total_tokens += other.total_tokens
        return self


class GPT_4(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def calculate_price(self):
        prompt_token_coefficient = self.prompt_tokens / 1000
        completion_token_coefficient = self.completion_tokens / 1000
        prompt_8k_price = MODEL_PRICING[ChatModel.CHAT_GPT_4_8K]['prompt']
        completion_8k_price = MODEL_PRICING[ChatModel.CHAT_GPT_4_8K]['completion']
        prompt_32k_price = MODEL_PRICING[ChatModel.CHAT_GPT_4_32_K]['prompt']
        completion_32k_price = MODEL_PRICING[ChatModel.CHAT_GPT_4_32_K]['completion']
        if self.total_tokens < 8001:
            return prompt_token_coefficient * prompt_8k_price + completion_token_coefficient * completion_8k_price
        elif 8000 < self.total_tokens < 32001:
            return prompt_token_coefficient * prompt_32k_price + completion_token_coefficient * completion_32k_price
        else:
            raise TooManyTokensException('Too many tokens')

    def __add__(self, other):
        self.prompt_tokens += other.prompt_tokens
        self.completion_tokens += other.completion_tokens
        self.total_tokens += other.total_tokens
        return self


class ModelTokenUsage(BaseModel):
    gpt_3_5_turbo: GPT_3_5_Turbo = GPT_3_5_Turbo()
    gpt_3_5_turbo_0301: GPT_3_5_Turbo = GPT_3_5_Turbo()
    gpt_4: GPT_4 = GPT_4()


class UserAccount(BaseModel):
    user_id: int
    is_admin: bool = False
    current_balance: int = 200  # the default balance in cents
    model_token_usage: ModelTokenUsage


class Message(BaseModel):
    role: str = "system"
    content: str


class OpenAIConfig(BaseModel):
    current_model: ChatModel = ChatModel.CHAT_GPT_3_5_TURBO_0301
    max_tokens: int = DEFAULT_MAX_TOKENS
    temperature: float = DEFAULT_MODEL_TEMPERATURE


class Chat(BaseModel):
    chat_id: int
    open_ai_config: OpenAIConfig = OpenAIConfig()
    system_message: Message
    messages: t.List[Message]


pydantic_model_per_gpt_model = {
    ChatModel.CHAT_GPT_3_5_TURBO: GPT_3_5_Turbo,
    ChatModel.CHAT_GPT_3_5_TURBO_0301: GPT_3_5_Turbo,
    ChatModel.CHAT_GPT_4: GPT_4,
}
