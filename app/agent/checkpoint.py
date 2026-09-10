import os
from functools import lru_cache

os.environ.setdefault("LANGGRAPH_STRICT_MSGPACK", "true")

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver

from app.core.config import get_settings


@lru_cache
def get_checkpointer() -> PostgresSaver:
    """Create and initialize the PostgreSQL-backed LangGraph checkpointer."""

    settings = get_settings()

    conninfo = (
        settings.database_url
        .replace("postgresql+psycopg://", "postgresql://")
        .replace("postgresql+psycopg2://", "postgresql://")
    )

    pool = ConnectionPool(
        conninfo=conninfo,
        min_size=1,
        max_size=5,
        open=True,
        kwargs={
            "autocommit": True,
            "row_factory": dict_row,
        },
    )

    pool.wait(timeout=10)

    checkpointer = PostgresSaver(pool)
    checkpointer.setup()

    return checkpointer


def verify_checkpoint_storage() -> str:
    """Initialize checkpoint storage and return its implementation name."""

    checkpointer = get_checkpointer()
    return type(checkpointer).__name__