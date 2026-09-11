from __future__ import annotations

from pydantic import BaseModel


class ClientInputError(Exception):
    """Raised when the authenticated client provides invalid input."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class APIErrorResponse(BaseModel):
    """Standard error response returned by the API."""

    error: str
    message: str
    correlation_id: str
