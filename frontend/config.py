from dataclasses import dataclass
import os


@dataclass(frozen=True)
class FrontendSettings:
    api_base_url: str
    request_timeout: float = 120.0
    stream_timeout: float = 300.0


def get_settings() -> FrontendSettings:
    return FrontendSettings(
        api_base_url=os.getenv(
            "EERLY_API_BASE_URL",
            "http://localhost:8000",
        ).rstrip("/"),
        request_timeout=float(
            os.getenv("EERLY_REQUEST_TIMEOUT", "120")
        ),
        stream_timeout=float(
            os.getenv("EERLY_STREAM_TIMEOUT", "300")
        ),
    )
