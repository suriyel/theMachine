"""Tests for Feature #2: Data Model & Migrations — Storage Client Wrappers.

Test categories covered:
- Happy path: import, method existence, async interface
- Error handling: empty URL raises ValueError
- Boundary: None URL raises ValueError
- Security: N/A — internal infrastructure wrappers

Negative tests: T9, T10, T11, T19a, T19b, T19c = 6/12 = 50%
"""

import asyncio
import inspect as std_inspect

import pytest


# --- T5: All three clients importable ---


# [unit] T5: ElasticsearchClient, QdrantClientWrapper, RedisClient importable
def test_all_clients_importable():
    """VS-3: All three client classes are importable from src.shared.clients."""
    from src.shared.clients import (
        ElasticsearchClient,
        QdrantClientWrapper,
        RedisClient,
    )

    assert ElasticsearchClient is not None
    assert QdrantClientWrapper is not None
    assert RedisClient is not None


# --- T6: ElasticsearchClient has required async methods ---


# [unit] T6: ElasticsearchClient has connect, health_check, close as coroutines
def test_elasticsearch_client_methods():
    """VS-3: ElasticsearchClient has connect, health_check, close methods."""
    from src.shared.clients import ElasticsearchClient

    client = ElasticsearchClient(url="http://localhost:9200")

    for method_name in ("connect", "health_check", "close"):
        method = getattr(client, method_name, None)
        assert method is not None, f"Missing method: {method_name}"
        assert asyncio.iscoroutinefunction(method), (
            f"{method_name} must be a coroutine function"
        )


# --- T7: QdrantClientWrapper has required async methods ---


# [unit] T7: QdrantClientWrapper has connect, health_check, close as coroutines
def test_qdrant_client_methods():
    """VS-3: QdrantClientWrapper has connect, health_check, close methods."""
    from src.shared.clients import QdrantClientWrapper

    client = QdrantClientWrapper(url="http://localhost:6333")

    for method_name in ("connect", "health_check", "close"):
        method = getattr(client, method_name, None)
        assert method is not None, f"Missing method: {method_name}"
        assert asyncio.iscoroutinefunction(method), (
            f"{method_name} must be a coroutine function"
        )


# --- T8: RedisClient has required async methods ---


# [unit] T8: RedisClient has connect, health_check, close as coroutines
def test_redis_client_methods():
    """VS-3: RedisClient has connect, health_check, close methods."""
    from src.shared.clients import RedisClient

    client = RedisClient(url="redis://localhost:6379/0")

    for method_name in ("connect", "health_check", "close"):
        method = getattr(client, method_name, None)
        assert method is not None, f"Missing method: {method_name}"
        assert asyncio.iscoroutinefunction(method), (
            f"{method_name} must be a coroutine function"
        )


# --- T9: ElasticsearchClient empty URL ---


# [unit] T9: ElasticsearchClient('') raises ValueError
def test_elasticsearch_client_empty_url_raises():
    """Error: empty URL must raise ValueError."""
    from src.shared.clients import ElasticsearchClient

    with pytest.raises(ValueError, match="url must not be empty"):
        ElasticsearchClient(url="")


# --- T10: QdrantClientWrapper empty URL ---


# [unit] T10: QdrantClientWrapper('') raises ValueError
def test_qdrant_client_empty_url_raises():
    """Error: empty URL must raise ValueError."""
    from src.shared.clients import QdrantClientWrapper

    with pytest.raises(ValueError, match="url must not be empty"):
        QdrantClientWrapper(url="")


# --- T11: RedisClient empty URL ---


# [unit] T11: RedisClient('') raises ValueError
def test_redis_client_empty_url_raises():
    """Error: empty URL must raise ValueError."""
    from src.shared.clients import RedisClient

    with pytest.raises(ValueError, match="url must not be empty"):
        RedisClient(url="")


# --- T19: None URL raises ValueError for all clients ---


# [unit] T19a: ElasticsearchClient(None) raises ValueError
def test_elasticsearch_client_none_url_raises():
    """Boundary: None URL must raise ValueError."""
    from src.shared.clients import ElasticsearchClient

    with pytest.raises(ValueError, match="url must not be empty"):
        ElasticsearchClient(url=None)


# [unit] T19b: QdrantClientWrapper(None) raises ValueError
def test_qdrant_client_none_url_raises():
    """Boundary: None URL must raise ValueError."""
    from src.shared.clients import QdrantClientWrapper

    with pytest.raises(ValueError, match="url must not be empty"):
        QdrantClientWrapper(url=None)


# [unit] T19c: RedisClient(None) raises ValueError
def test_redis_client_none_url_raises():
    """Boundary: None URL must raise ValueError."""
    from src.shared.clients import RedisClient

    with pytest.raises(ValueError, match="url must not be empty"):
        RedisClient(url=None)


# --- Client async method behavior tests ---


# [unit] health_check returns False when not connected (no client)
async def test_elasticsearch_health_check_without_connect():
    """Error: health_check before connect returns False."""
    from src.shared.clients import ElasticsearchClient

    client = ElasticsearchClient(url="http://localhost:9200")
    result = await client.health_check()
    assert result is False


async def test_qdrant_health_check_without_connect():
    """Error: health_check before connect returns False."""
    from src.shared.clients import QdrantClientWrapper

    client = QdrantClientWrapper(url="http://localhost:6333")
    result = await client.health_check()
    assert result is False


async def test_redis_health_check_without_connect():
    """Error: health_check before connect returns False."""
    from src.shared.clients import RedisClient

    client = RedisClient(url="redis://localhost:6379/0")
    result = await client.health_check()
    assert result is False


# [unit] close when not connected is a no-op (no error)
async def test_elasticsearch_close_without_connect():
    """Boundary: close before connect does not raise."""
    from src.shared.clients import ElasticsearchClient

    client = ElasticsearchClient(url="http://localhost:9200")
    await client.close()  # should not raise
    assert client._client is None


async def test_qdrant_close_without_connect():
    """Boundary: close before connect does not raise."""
    from src.shared.clients import QdrantClientWrapper

    client = QdrantClientWrapper(url="http://localhost:6333")
    await client.close()  # should not raise
    assert client._client is None


async def test_redis_close_without_connect():
    """Boundary: close before connect does not raise."""
    from src.shared.clients import RedisClient

    client = RedisClient(url="redis://localhost:6379/0")
    await client.close()  # should not raise
    assert client._client is None


# [unit] connect sets internal client (not None)
async def test_elasticsearch_connect_sets_client():
    """Happy path: connect initializes internal client."""
    from src.shared.clients import ElasticsearchClient

    client = ElasticsearchClient(url="http://localhost:9200")
    await client.connect()
    assert client._client is not None
    await client.close()


async def test_qdrant_connect_sets_client():
    """Happy path: connect initializes internal client."""
    from src.shared.clients import QdrantClientWrapper

    client = QdrantClientWrapper(url="http://localhost:6333")
    await client.connect()
    assert client._client is not None
    await client.close()


async def test_redis_connect_sets_client():
    """Happy path: connect initializes internal client."""
    from src.shared.clients import RedisClient

    client = RedisClient(url="redis://localhost:6379/0")
    await client.connect()
    assert client._client is not None
    await client.close()


# [unit] close after connect resets client to None
async def test_elasticsearch_close_resets_client():
    """Happy path: close after connect sets _client to None."""
    from src.shared.clients import ElasticsearchClient

    client = ElasticsearchClient(url="http://localhost:9200")
    await client.connect()
    assert client._client is not None
    await client.close()
    assert client._client is None


async def test_qdrant_close_resets_client():
    """Happy path: close after connect sets _client to None."""
    from src.shared.clients import QdrantClientWrapper

    client = QdrantClientWrapper(url="http://localhost:6333")
    await client.connect()
    assert client._client is not None
    await client.close()
    assert client._client is None


async def test_redis_close_resets_client():
    """Happy path: close after connect sets _client to None."""
    from src.shared.clients import RedisClient

    client = RedisClient(url="redis://localhost:6379/0")
    await client.connect()
    assert client._client is not None
    await client.close()
    assert client._client is None


# [unit] health_check returns False when connected but service unreachable
async def test_elasticsearch_health_check_unreachable():
    """Error: health_check returns False when ES is not running."""
    from src.shared.clients import ElasticsearchClient

    client = ElasticsearchClient(url="http://localhost:19999")
    await client.connect()
    result = await client.health_check()
    assert result is False
    await client.close()


async def test_qdrant_health_check_unreachable():
    """Error: health_check returns False when Qdrant is not running."""
    from src.shared.clients import QdrantClientWrapper

    client = QdrantClientWrapper(url="http://localhost:19999")
    await client.connect()
    result = await client.health_check()
    assert result is False
    await client.close()


async def test_redis_health_check_unreachable():
    """Error: health_check returns False when Redis is not running."""
    from src.shared.clients import RedisClient

    client = RedisClient(url="redis://localhost:19999/0")
    await client.connect()
    result = await client.health_check()
    assert result is False
    await client.close()
