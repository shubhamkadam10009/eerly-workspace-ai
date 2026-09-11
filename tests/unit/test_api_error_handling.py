import jwt
from fastapi.testclient import TestClient

from app.agent.service import run_agent
from app.core.config import get_settings
from app.core.errors import ClientInputError
from app.main import app


def _auth_headers(correlation_id: str = "error-test") -> dict[str, str]:
    settings = get_settings()

    token = jwt.encode(
        {"sub": "user_a"},
        settings.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )

    return {
        "Authorization": f"Bearer {token}",
        "X-Correlation-ID": correlation_id,
    }


def test_client_input_error_returns_structured_400(monkeypatch):
    def raise_client_error(*args, **kwargs):
        raise ClientInputError("The requested operation is invalid.")

    monkeypatch.setattr(
        "app.api.agent.run_agent",
        raise_client_error,
    )

    client = TestClient(app)

    response = client.post(
        "/agent/run",
        json={"request": "Create a report."},
        headers=_auth_headers("client-error-001"),
    )

    assert response.status_code == 400

    body = response.json()

    assert body["error"] == "invalid_request"
    assert body["message"] == "The requested operation is invalid."
    assert body["correlation_id"] == "client-error-001"
    assert response.headers["X-Correlation-ID"] == "client-error-001"


def test_unexpected_error_returns_generic_500(monkeypatch):
    def raise_unexpected_error(*args, **kwargs):
        raise RuntimeError("database password=SUPER_SECRET internal failure")

    monkeypatch.setattr(
        "app.api.agent.run_agent",
        raise_unexpected_error,
    )

    client = TestClient(
        app,
        raise_server_exceptions=False,
    )

    response = client.post(
        "/agent/run",
        json={"request": "Create a report."},
        headers=_auth_headers("server-error-001"),
    )

    assert response.status_code == 500

    body = response.json()

    assert body["error"] == "internal_server_error"
    assert body["message"] == (
        "An unexpected error occurred while processing the request."
    )
    assert body["correlation_id"] == "server-error-001"

    assert "SUPER_SECRET" not in response.text
    assert "database password" not in response.text
    assert response.headers["X-Correlation-ID"] == "server-error-001"
