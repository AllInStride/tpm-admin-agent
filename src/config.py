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

    # Anthropic (LLM for RAID extraction)
    anthropic_api_key: str | None = Field(default=None)
    anthropic_model: str = Field(default="claude-sonnet-4-5")
    extraction_confidence_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score to include extracted items",
    )

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
