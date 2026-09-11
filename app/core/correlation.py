from __future__ import annotations

from contextvars import ContextVar

correlation_id_context: ContextVar[str | None] = ContextVar(
    "correlation_id",
    default=None,
)
