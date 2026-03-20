"""Query Service configuration."""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Service
    SERVICE_NAME: str = "code-context-retrieval"
    SERVICE_PORT: int = 8000

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 300  # 5 minutes cache TTL

    # Qdrant
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "code_chunks"

    # Elasticsearch
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    ES_INDEX_PREFIX: str = "ccr"

    # ML Models
    EMBEDDING_MODEL: str = "BAAI/bge-code-v1"
    RERANKER_MODEL: str = "BAAI/bge-reranker-v2-m3"
    EMBEDDING_DIMENSION: int = 768

    # Retrieval
    SEMANTIC_THRESHOLD: float = 0.6
    TOP_K_RESULTS: int = 3
    RRF_K: int = 60

    # Security
    API_KEY_SECRET: str = "change-me-in-production"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # Ignore extra env vars not defined in model
    }


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
