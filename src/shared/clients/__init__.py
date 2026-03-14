"""External service clients management."""

from typing import Optional

from elasticsearch import AsyncElasticsearch
from qdrant_client import AsyncQdrantClient
from redis.asyncio import Redis

from src.query.config import settings

# Global client instances
_qdrant_client: Optional[AsyncQdrantClient] = None
_es_client: Optional[AsyncElasticsearch] = None
_redis_client: Optional[Redis] = None


def get_qdrant() -> AsyncQdrantClient:
    """Get Qdrant client instance."""
    global _qdrant_client
    if _qdrant_client is None:
        raise RuntimeError("Clients not initialized. Call init_clients() first.")
    return _qdrant_client


def get_elasticsearch() -> AsyncElasticsearch:
    """Get Elasticsearch client instance."""
    global _es_client
    if _es_client is None:
        raise RuntimeError("Clients not initialized. Call init_clients() first.")
    return _es_client


def get_redis() -> Redis:
    """Get Redis client instance."""
    global _redis_client
    if _redis_client is None:
        raise RuntimeError("Clients not initialized. Call init_clients() first.")
    return _redis_client


async def init_clients() -> None:
    """Initialize all external service clients."""
    global _qdrant_client, _es_client, _redis_client

    # Qdrant
    _qdrant_client = AsyncQdrantClient(url=settings.QDRANT_URL)

    # Elasticsearch
    _es_client = AsyncElasticsearch(settings.ELASTICSEARCH_URL)

    # Redis
    _redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)


async def close_clients() -> None:
    """Close all external service clients."""
    global _qdrant_client, _es_client, _redis_client

    if _qdrant_client:
        await _qdrant_client.close()
        _qdrant_client = None

    if _es_client:
        await _es_client.close()
        _es_client = None

    if _redis_client:
        await _redis_client.close()
        _redis_client = None
