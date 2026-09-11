import asyncio
import logging
import sys

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.agent import router as agent_router
from app.api.health import router as health_router
from app.core.config import get_settings
from app.core.correlation import correlation_id_context
from app.core.errors import APIErrorResponse, ClientInputError
from app.core.logging import configure_logging
from app.core.middleware import CorrelationIdMiddleware


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


settings = get_settings()

configure_logging(settings.log_level)

logger = logging.getLogger("app.api")


app = FastAPI(
    title="Eerly Workspace AI",
    version="0.1.0",
)

app.add_middleware(CorrelationIdMiddleware)


def get_request_correlation_id(request: Request) -> str:
    return (
        getattr(request.state, "correlation_id", None)
        or correlation_id_context.get()
        or "unknown"
    )


@app.exception_handler(ClientInputError)
async def client_input_error_handler(
    request: Request,
    exc: ClientInputError,
) -> JSONResponse:
    correlation_id = get_request_correlation_id(request)

    logger.warning(
        "Client input validation failed",
        extra={
            "correlation_id": correlation_id,
            "http_method": request.method,
            "http_path": request.url.path,
        },
    )

    body = APIErrorResponse(
        error="invalid_request",
        message=exc.message,
        correlation_id=correlation_id,
    )

    return JSONResponse(
        status_code=400,
        content=body.model_dump(),
        headers={
            "X-Correlation-ID": correlation_id,
        },
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    correlation_id = get_request_correlation_id(request)

    logger.exception(
        "Unhandled application exception",
        extra={
            "correlation_id": correlation_id,
            "http_method": request.method,
            "http_path": request.url.path,
        },
    )

    body = APIErrorResponse(
        error="internal_server_error",
        message="An unexpected error occurred while processing the request.",
        correlation_id=correlation_id,
    )

    return JSONResponse(
        status_code=500,
        content=body.model_dump(),
        headers={
            "X-Correlation-ID": correlation_id,
        },
    )


app.include_router(health_router)
app.include_router(agent_router)


@app.get("/health")
def health():
    return {"status": "ok"}
