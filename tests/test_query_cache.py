"""Tests for Redis query cache feature (NFR-001 optimization).

These tests verify query result caching to achieve P95 <= 1000ms latency.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import hashlib
import json

from src.query.cache import QueryCache, get_cache_key


# [unit] — Redis cache logic tests
class TestQueryCache:
    """Unit tests for QueryCache."""

    def test_get_cache_key_deterministic(self):
        """Cache key should be deterministic for same query."""
        query = "how to configure spring webclient timeout"
        key1 = get_cache_key(query, "natural_language", None, None)
        key2 = get_cache_key(query, "natural_language", None, None)
        assert key1 == key2

    def test_get_cache_key_different_queries(self):
        """Different queries should produce different cache keys."""
        key1 = get_cache_key("query one", "natural_language", None, None)
        key2 = get_cache_key("query two", "natural_language", None, None)
        assert key1 != key2

    def test_get_cache_key_with_repo_filter(self):
        """Same query with different repo filter should produce different keys."""
        key1 = get_cache_key("timeout", "natural_language", "repo-a", None)
        key2 = get_cache_key("timeout", "natural_language", "repo-b", None)
        assert key1 != key2

    def test_get_cache_key_with_language_filter(self):
        """Same query with different language filter should produce different keys."""
        key1 = get_cache_key("timeout", "natural_language", None, "Java")
        key2 = get_cache_key("timeout", "natural_language", None, "Python")
        assert key1 != key2


class TestQueryCacheIntegration:
    """Integration tests for Redis query cache (requires Redis)."""

    @pytest.mark.asyncio
    async def test_cache_miss_triggers_handler(self):
        """When cache misses, handler should be called and result cached."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None  # Cache miss

        cache = QueryCache(mock_redis)

        # Mock handler that returns results
        mock_handler = AsyncMock()
        mock_handler.handle.return_value = MagicMock(results=["result1", "result2"])

        # Call cache-aware handler
        from src.query.models import QueryRequest
        request = QueryRequest(query="test query", query_type="natural_language")

        # Patch the cache set to avoid serialization issues
        with patch.object(cache, 'set', new_callable=AsyncMock) as mock_set:
            result = await cache.get_or_compute(request, mock_handler.handle)

        # Handler should have been called on cache miss
        mock_handler.handle.assert_called_once()

        # Cache set should have been called
        mock_set.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_result(self):
        """When cache hits, cached result should be returned without calling handler."""
        mock_redis = AsyncMock()

        # Create a mock cached response with all required fields
        cached_data = {
            "results": [
                {"repository": "test-repo", "file_path": "test.java", "score": 0.95, "content": "cached content"}
            ],
            "total": 1
        }

        mock_redis.get.return_value = json.dumps(cached_data).encode()

        cache = QueryCache(mock_redis)
        mock_handler = AsyncMock()

        from src.query.models import QueryRequest
        request = QueryRequest(query="test query", query_type="natural_language")

        result = await cache.get_or_compute(request, mock_handler.handle)

        # Handler should NOT have been called on cache hit
        mock_handler.handle.assert_not_called()

        # Result should be from cache
        assert result.results[0].content == "cached content"


# [unit] — cache configuration tests
class TestCacheConfiguration:
    """Tests for cache configuration."""

    def test_cache_ttl_from_config(self):
        """Cache TTL should be configurable."""
        from src.query.config import settings
        # Verify TTL is set (default 300 seconds)
        assert hasattr(settings, 'CACHE_TTL_SECONDS')
        assert settings.CACHE_TTL_SECONDS == 300


# [unit] — cache edge cases
class TestQueryCacheEdgeCases:
    """Edge case tests for QueryCache."""

    @pytest.mark.asyncio
    async def test_get_returns_none_on_missing_key(self):
        """When key doesn't exist, get should return None."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None

        cache = QueryCache(mock_redis)
        result = await cache.get("nonexistent_key")

        assert result is None
        mock_redis.get.assert_called_once_with("nonexistent_key")

    @pytest.mark.asyncio
    async def test_set_with_custom_ttl(self):
        """Set should accept custom TTL override."""
        mock_redis = AsyncMock()
        cache = QueryCache(mock_redis)

        await cache.set("key", {"data": "value"}, ttl=600)

        # Check setex was called with custom TTL
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 600  # TTL

    @pytest.mark.asyncio
    async def test_close_closes_redis(self):
        """Close should close Redis connection."""
        mock_redis = AsyncMock()
        cache = QueryCache(mock_redis)

        await cache.close()

        mock_redis.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_compute_with_dict_result(self):
        """Handle dict results properly."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None

        cache = QueryCache(mock_redis)

        # Handler returns a dict
        async def dict_handler(request):
            return {"results": [], "total": 0}

        from src.query.models import QueryRequest
        request = QueryRequest(query="test")

        result = await cache.get_or_compute(request, dict_handler)

        assert isinstance(result, dict)
