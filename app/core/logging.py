from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from app.core.correlation import correlation_id_context


class CorrelationIdFilter(logging.Filter):
    """Add the current correlation ID to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_context.get()
        return True


class JsonFormatter(logging.Formatter):
    """Format application log records as structured JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        correlation_id = getattr(record, "correlation_id", None)
        if correlation_id:
            payload["correlation_id"] = correlation_id

        user_id = getattr(record, "user_id", None)
        if user_id:
            payload["user_id"] = user_id

        thread_id = getattr(record, "thread_id", None)
        if thread_id:
            payload["thread_id"] = thread_id

        http_method = getattr(record, "http_method", None)
        if http_method:
            payload["http_method"] = http_method

        http_path = getattr(record, "http_path", None)
        if http_path:
            payload["http_path"] = http_path

        http_status = getattr(record, "http_status", None)
        if http_status is not None:
            payload["http_status"] = http_status

        duration_ms = getattr(record, "duration_ms", None)
        if duration_ms is not None:
            payload["duration_ms"] = duration_ms

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Configure application-wide structured logging."""

    root_logger = logging.getLogger()

    root_logger.setLevel(level.upper())

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(CorrelationIdFilter())

    root_logger.handlers.clear()
    root_logger.addHandler(handler)
