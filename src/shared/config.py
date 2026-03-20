"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from .env or environment variables."""

    database_url: str

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


def get_settings() -> Settings:
    """Create and return a Settings instance.

    Raises:
        ValidationError: If required environment variables are missing.
    """
    return Settings()
