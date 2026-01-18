"""Application configuration using pydantic-settings pattern."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "TPM Admin Agent"
    app_version: str = "0.1.0"
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")

    # Database (Turso)
    turso_database_url: str | None = Field(default=None)
    turso_auth_token: str | None = Field(default=None)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
