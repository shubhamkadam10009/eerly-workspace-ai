from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.core.config import get_settings


@lru_cache
def get_llm() -> ChatOpenAI:
    """Create and cache the application's OpenAI chat model."""

    settings = get_settings()

    if settings.openai_api_key is None:
        raise ValueError("OPENAI_API_KEY is not configured")

    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key.get_secret_value(),
        temperature=0,
    )
