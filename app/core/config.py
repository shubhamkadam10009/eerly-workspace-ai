from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"

    llm_provider: str = "gemini"

    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-3.6-flash"

    database_url: str
    log_level: str = "INFO"
    jwt_secret: SecretStr
    workspace_root: Path = Path("/app/workspaces")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
