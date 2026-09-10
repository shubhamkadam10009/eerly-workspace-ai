from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from typing import Any

import httpx

from frontend.config import get_settings


class APIClientError(Exception):
    """Raised when the Eerly API returns an error."""


class EerlyAPIClient:
    """Thin HTTP client for the Eerly Workspace AI backend."""

    def __init__(self, token: str) -> None:
        if not token or not token.strip():
            raise ValueError("Authentication token is required.")

        self.token = token.strip()
        self.settings = get_settings()

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }

    def run_agent(
        self,
        request: str,
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        """Start a Workspace Consultant execution."""

        payload: dict[str, Any] = {
            "request": request,
        }

        if thread_id:
            payload["thread_id"] = thread_id

        url = f"{self.settings.api_base_url}/agent/run"

        try:
            response = httpx.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=self.settings.request_timeout,
            )
        except httpx.HTTPError as exc:
            raise APIClientError(
                f"Unable to reach the API: {exc}"
            ) from exc

        return self._parse_response(response)

    def resume_agent(
        self,
        thread_id: str,
        decision: str,
        edited_output: str | None = None,
        feedback: str | None = None,
    ) -> dict[str, Any]:
        """Resume an interrupted Workspace Consultant execution."""

        approval_decision: dict[str, Any] = {
            "decision": decision,
        }

        if edited_output is not None:
            approval_decision["edited_output"] = edited_output

        if feedback is not None:
            approval_decision["feedback"] = feedback

        payload = {
            "thread_id": thread_id,
            "decision": approval_decision,
        }

        url = f"{self.settings.api_base_url}/agent/resume"

        try:
            response = httpx.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=self.settings.request_timeout,
            )
        except httpx.HTTPError as exc:
            raise APIClientError(
                f"Unable to reach the API: {exc}"
            ) from exc

        return self._parse_response(response)

    def stream_events(
        self,
        thread_id: str,
        on_connected: Callable[[], None] | None = None,
        stop_events: set[str] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """
        Stream agent progress events using Server-Sent Events.

        `on_connected` is called after the HTTP streaming connection has
        successfully opened. This lets the caller establish the SSE
        subscription before starting the agent execution.

        `stop_events` allows the caller to close the stream at a logical
        boundary such as approval_required or completed.
        """

        if not thread_id or not thread_id.strip():
            raise ValueError("thread_id is required.")

        url = (
            f"{self.settings.api_base_url}"
            f"/agent/stream/{thread_id}"
        )

        stop_events = stop_events or {
            "completed",
            "rejected",
            "failed",
        }

        try:
            with httpx.stream(
                "GET",
                url,
                headers={
                    **self.headers,
                    "Accept": "text/event-stream",
                },
                timeout=self.settings.stream_timeout,
            ) as response:

                if response.status_code >= 400:
                    body = response.read().decode(
                        "utf-8",
                        errors="replace",
                    )

                    raise APIClientError(
                        self._format_http_error(
                            response.status_code,
                            body,
                        )
                    )

                connection_notified = False

                event_name: str | None = None
                event_data: str | None = None

                for line in response.iter_lines():
                    if not connection_notified:
                        connection_notified = True

                        if on_connected is not None:
                            on_connected()

                    if not line:
                        if event_data is not None:
                            event = self._parse_sse_event(
                                event_name,
                                event_data,
                            )

                            yield event

                            if event.get("event") in stop_events:
                                return

                        event_name = None
                        event_data = None
                        continue

                    if line.startswith(":"):
                        continue

                    if line.startswith("event:"):
                        event_name = line[
                            len("event:"):
                        ].strip()

                    elif line.startswith("data:"):
                        value = line[
                            len("data:"):
                        ].strip()

                        if event_data is None:
                            event_data = value
                        else:
                            event_data += "\n" + value

        except httpx.HTTPError as exc:
            raise APIClientError(
                f"Unable to stream agent events: {exc}"
            ) from exc

    @staticmethod
    def _parse_sse_event(
        event_name: str | None,
        event_data: str,
    ) -> dict[str, Any]:
        try:
            payload = json.loads(event_data)
        except json.JSONDecodeError as exc:
            raise APIClientError(
                "API returned invalid SSE event data."
            ) from exc

        if event_name:
            payload.setdefault("event", event_name)

        return payload

    @staticmethod
    def _parse_response(
        response: httpx.Response,
    ) -> dict[str, Any]:
        if response.status_code >= 400:
            raise APIClientError(
                EerlyAPIClient._format_http_error(
                    response.status_code,
                    response.text,
                )
            )

        try:
            return response.json()
        except ValueError as exc:
            raise APIClientError(
                "API returned an invalid JSON response."
            ) from exc

    @staticmethod
    def _format_http_error(
        status_code: int,
        body: str,
    ) -> str:
        try:
            payload = json.loads(body)
            detail = payload.get("detail")

            if detail:
                return (
                    f"API request failed "
                    f"({status_code}): {detail}"
                )

        except json.JSONDecodeError:
            pass

        return f"API request failed ({status_code})."
