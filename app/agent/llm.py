from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel

from app.llm.factory import get_chat_model


@lru_cache
def get_llm() -> BaseChatModel:
    """Create and cache the application's configured chat model."""
    return get_chat_model()
