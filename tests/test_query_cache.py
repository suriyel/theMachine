"""Tests for Feature #25 — Query Cache (L1 in-memory + L2 Redis)."""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.query.query_cache import QueryCache
from src.query.response_models import CodeResult, QueryResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(query: str = "test query", repo: str | None = "repo-1") -> QueryResponse:
    """Build a minimal QueryResponse for testing."""
    return QueryResponse(
        query=query,
        query_type="nl",
        repo=repo,
        code_results=[
            CodeResult(
                file_path="src/main.py",
                content="def main(): pass",
                relevance_score=0.95,
            )
        ],
    )


def _fake_redis_client() -> AsyncMock:
    """Return an AsyncMock that behaves like RedisClient._client."""
    client = AsyncMock()
    client.get = AsyncMock(return_value=None)
    client.setex = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=True)
    client.smembers = AsyncMock(return_value=set())
    client.sadd = AsyncMock(return_value=True)
    return client


def _redis_client_wrapper(inner: AsyncMock) -> MagicMock:
    """Wrap inner mock to mimic RedisClient with _client attribute."""
    wrapper = MagicMock()
    wrapper._client = inner
    return wrapper


# ---------------------------------------------------------------------------
# T1: Happy path — set then get returns same response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_then_get_returns_cached_response():
    """T1: After set(), get() with same params returns identical response."""
    inner = _fake_redis_client()
    redis_client = _redis_client_wrapper(inner)
    cache = QueryCache(redis_client=redis_client, default_ttl=300)

    resp = _make_response()
    await cache.set("find auth", "repo-1", ["python"], resp)
    result = await cache.get("find auth", "repo-1", ["python"])

    assert result is not None
    assert result.query == resp.query
    assert len(result.code_results) == len(resp.code_results)


# ---------------------------------------------------------------------------
# T2: Happy path — cache miss returns None
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cache_miss_returns_none():
    """T2: get() on empty cache returns None."""
    cache = QueryCache(redis_client=None, default_ttl=300)
    result = await cache.get("unknown query", "repo-1", ["python"])
    assert result is None


# ---------------------------------------------------------------------------
# T3: Happy path — same params produce same cache key
# ---------------------------------------------------------------------------


def test_same_params_produce_same_key():
    """T3: _make_key is deterministic for identical inputs."""
    cache = QueryCache(redis_client=None)
    key1 = cache._make_key("find auth", "repo-1", ["python", "java"])
    key2 = cache._make_key("find auth", "repo-1", ["python", "java"])
    assert key1 == key2


# ---------------------------------------------------------------------------
# T4: Happy path — invalidate_repo clears entries for that repo
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalidate_repo_clears_entries():
    """T4: invalidate_repo removes L1 entries for the given repo."""
    cache = QueryCache(redis_client=None, default_ttl=300)

    resp1 = _make_response(repo="repo-1")
    resp2 = _make_response(repo="repo-2")

    await cache.set("query-a", "repo-1", None, resp1)
    await cache.set("query-b", "repo-2", None, resp2)

    await cache.invalidate_repo("repo-1")

    assert await cache.get("query-a", "repo-1", None) is None
    assert await cache.get("query-b", "repo-2", None) is not None


# ---------------------------------------------------------------------------
# T5: Error — Redis unavailable on get returns None
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_redis_unavailable_on_get_returns_none():
    """T5: When Redis raises on get, cache degrades gracefully to None."""
    inner = _fake_redis_client()
    inner.get = AsyncMock(side_effect=ConnectionError("Redis down"))
    redis_client = _redis_client_wrapper(inner)

    cache = QueryCache(redis_client=redis_client, default_ttl=300)
    result = await cache.get("query", "repo-1", ["python"])
    assert result is None  # No exception raised


# ---------------------------------------------------------------------------
# T6: Error — Redis unavailable on set — no exception
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_redis_unavailable_on_set_no_exception():
    """T6: When Redis raises on set, no exception propagates."""
    inner = _fake_redis_client()
    inner.setex = AsyncMock(side_effect=ConnectionError("Redis down"))
    inner.sadd = AsyncMock(side_effect=ConnectionError("Redis down"))
    redis_client = _redis_client_wrapper(inner)

    cache = QueryCache(redis_client=redis_client, default_ttl=300)
    resp = _make_response()
    # Should not raise
    await cache.set("query", "repo-1", ["python"], resp)


# ---------------------------------------------------------------------------
# T7: Boundary — None repo and None languages produce valid key
# ---------------------------------------------------------------------------


def test_none_repo_and_languages_produce_valid_key():
    """T7: _make_key works with None repo and None languages."""
    cache = QueryCache(redis_client=None)
    key = cache._make_key("find auth", None, None)
    assert isinstance(key, str)
    assert key.startswith("qcache:")
    assert len(key) > 10


# ---------------------------------------------------------------------------
# T8: Boundary — TTL expiry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ttl_expiry_returns_none():
    """T8: Expired L1 entries return None on get."""
    cache = QueryCache(redis_client=None, default_ttl=1)

    resp = _make_response()
    await cache.set("query", "repo-1", None, resp, ttl=1)

    # Manually expire the entry by backdating
    key = cache._make_key("query", "repo-1", None)
    if key in cache._l1_cache:
        cache._l1_cache[key] = cache._l1_cache[key]._replace(
            expiry=time.monotonic() - 1
        )

    result = await cache.get("query", "repo-1", None)
    assert result is None


# ---------------------------------------------------------------------------
# T9: Boundary — different query same repo → different entries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_different_query_same_repo_different_entries():
    """T9: Different queries for the same repo produce different cache entries."""
    cache = QueryCache(redis_client=None, default_ttl=300)

    resp_a = _make_response(query="find auth")
    resp_b = _make_response(query="find db")

    await cache.set("find auth", "repo-1", None, resp_a)
    await cache.set("find db", "repo-1", None, resp_b)

    result_a = await cache.get("find auth", "repo-1", None)
    result_b = await cache.get("find db", "repo-1", None)

    assert result_a is not None
    assert result_b is not None
    assert result_a.query == "find auth"
    assert result_b.query == "find db"


# ---------------------------------------------------------------------------
# T10: Integration — L1 returns before Redis is consulted
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_l1_returns_before_redis():
    """T10: When L1 has the entry, Redis.get is never called."""
    inner = _fake_redis_client()
    redis_client = _redis_client_wrapper(inner)
    cache = QueryCache(redis_client=redis_client, default_ttl=300)

    resp = _make_response()
    await cache.set("query", "repo-1", None, resp)

    # Reset the mock to track new calls
    inner.get.reset_mock()

    result = await cache.get("query", "repo-1", None)
    assert result is not None
    inner.get.assert_not_called()


# ---------------------------------------------------------------------------
# T11: L2 Redis hit promotes to L1
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_l2_redis_hit_promotes_to_l1():
    """T11: When L1 misses but Redis has data, response is returned and promoted to L1."""
    resp = _make_response()
    inner = _fake_redis_client()
    # Redis returns serialized response
    inner.get = AsyncMock(return_value=resp.model_dump_json().encode())
    redis_client = _redis_client_wrapper(inner)

    cache = QueryCache(redis_client=redis_client, default_ttl=300)

    result = await cache.get("find auth", "repo-1", ["python"])
    assert result is not None
    assert result.query == resp.query

    # Now L1 should have it — reset Redis mock and verify L1 serves it
    inner.get.reset_mock()
    result2 = await cache.get("find auth", "repo-1", ["python"])
    assert result2 is not None
    inner.get.assert_not_called()


# ---------------------------------------------------------------------------
# T12: LRU eviction when L1 exceeds max size
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_l1_lru_eviction():
    """T12: When L1 exceeds max_size, oldest entries are evicted."""
    cache = QueryCache(redis_client=None, default_ttl=300, l1_max_size=3)

    for i in range(5):
        resp = _make_response(query=f"query-{i}")
        await cache.set(f"query-{i}", "repo-1", None, resp)

    # Only 3 entries should remain (the 3 most recent: 2, 3, 4)
    assert len(cache._l1_cache) == 3
    assert await cache.get("query-0", "repo-1", None) is None
    assert await cache.get("query-1", "repo-1", None) is None
    assert await cache.get("query-4", "repo-1", None) is not None


# ---------------------------------------------------------------------------
# T13: invalidate_repo with Redis members
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalidate_repo_with_redis_members():
    """T13: invalidate_repo deletes Redis keys tracked in the repo set."""
    inner = _fake_redis_client()
    inner.smembers = AsyncMock(return_value={b"qcache:abc123", b"qcache:def456"})
    redis_client = _redis_client_wrapper(inner)

    cache = QueryCache(redis_client=redis_client, default_ttl=300)
    await cache.invalidate_repo("repo-1")

    inner.smembers.assert_called_once()
    inner.delete.assert_called()
