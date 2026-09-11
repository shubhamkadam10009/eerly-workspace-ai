import jwt

from app.auth.dependencies import get_current_user_id
from app.core.config import get_settings


def test_auth_rejects_token_using_unconfigured_algorithm():
    settings = get_settings()

    token = jwt.encode(
        {"sub": "user_a"},
        settings.jwt_secret.get_secret_value(),
        algorithm="HS384",
    )

    class Credentials:
        scheme = "Bearer"
        credentials = token

    credentials = Credentials()

    try:
        get_current_user_id(credentials)
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 401
    else:
        raise AssertionError(
            "Authentication accepted a token using an unconfigured algorithm"
        )
