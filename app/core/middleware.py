from __future__ import annotations

import logging
import time
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.correlation import correlation_id_context

logger = logging.getLogger("app.http")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID")

        if not correlation_id:
            correlation_id = str(uuid4())

        request.state.correlation_id = correlation_id

        token = correlation_id_context.set(correlation_id)
        started_at = time.perf_counter()

        logger.info(
            "HTTP request started",
            extra={"correlation_id": correlation_id},
        )

        try:
            response = await call_next(request)

            duration_ms = round(
                (time.perf_counter() - started_at) * 1000,
                2,
            )

            logger.info(
                "HTTP request completed",
                extra={
                    "correlation_id": correlation_id,
                    "http_method": request.method,
                    "http_path": request.url.path,
                    "http_status": response.status_code,
                    "duration_ms": duration_ms,
                },
            )

            response.headers["X-Correlation-ID"] = correlation_id

            return response

        except Exception:
            raise

        finally:
            correlation_id_context.reset(token)
