from langchain_openai import ChatOpenAI

from app.config import settings


def get_llm(temperature: float = 0.0) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.openrouter_model,
        openai_api_key=settings.openrouter_api_key,
        openai_api_base=settings.openrouter_base_url,
        temperature=temperature,
        max_retries=3,
    )
