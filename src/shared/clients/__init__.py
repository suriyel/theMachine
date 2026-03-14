"""External service clients management."""

import time
from typing import Optional

from elasticsearch import AsyncElasticsearch
from qdrant_client import AsyncQdrantClient
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.query.config import settings

# Global client instances
_qdrant_client: Optional[AsyncQdrantClient] = None
_es_client: Optional[AsyncElasticsearch] = None
_redis_client: Optional[Redis] = None


async def check_postgres_connection() -> dict:
    """Check PostgreSQL connection and return status.

    Returns:
        dict with keys: status, version, latency_ms

    Raises:
        ConnectionError: If connection fails
    """
    try:
        start_time = time.monotonic()
        engine = create_async_engine(settings.DATABASE_URL, echo=False)

        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version_row = result.fetchone()
            version = version_row[0] if version_row else "unknown"

        await engine.dispose()
        latency_ms = (time.monotonic() - start_time) * 1000

        return {
            "status": "ok",
            "version": version,
            "latency_ms": latency_ms,
        }
    except Exception as e:
        raise ConnectionError(f"PostgreSQL connection failed: {e}") from e


async def check_redis_connection() -> dict:
    """Check Redis connection and return status.

    Returns:
        dict with keys: status, ping, latency_ms

    Raises:
        ConnectionError: If connection fails
    """
    try:
        start_time = time.monotonic()
        client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        ping_result = await client.ping()
        latency_ms = (time.monotonic() - start_time) * 1000
        await client.close()

        return {
            "status": "ok",
            "ping": "PONG" if ping_result else "FAILED",
            "latency_ms": latency_ms,
        }
    except Exception as e:
        raise ConnectionError(f"Redis connection failed: {e}") from e


async def check_qdrant_connection() -> dict:
    """Check Qdrant connection and return health status.

    Returns:
        dict with keys: status, version

    Raises:
        ConnectionError: If connection fails
    """
    try:
        client = AsyncQdrantClient(url=settings.QDRANT_URL)
        # Get collections list as a simple health check
        collections = await client.get_collections()
        await client.close()

        return {
            "status": "ok",
            "version": "connected",  # Qdrant client doesn't expose version directly
        }
    except Exception as e:
        raise ConnectionError(f"Qdrant connection failed: {e}") from e


async def check_elasticsearch_connection() -> dict:
    """Check Elasticsearch connection and return cluster health.

    Returns:
        dict with keys: status, cluster_health, cluster_name, version

    Raises:
        ConnectionError: If connection fails
    """
    try:
        client = AsyncElasticsearch(settings.ELASTICSEARCH_URL)

        # Get cluster health
        health = await client.cluster.health()
        info = await client.info()
        await client.close()

        return {
            "status": "ok",
            "cluster_health": health.get("status", "unknown"),
            "cluster_name": health.get("cluster_name", "unknown"),
            "version": info.get("version", {}).get("number", "unknown"),
        }
    except Exception as e:
        raise ConnectionError(f"Elasticsearch connection failed: {e}") from e


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
