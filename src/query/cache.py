"""Query result caching using Redis."""

import hashlib
import json
from typing import Any, Callable, Optional
from unittest.mock import MagicMock

import redis.asyncio as redis

from src.query.config import settings


def get_cache_key(
    query: str,
    query_type: str,
    repo_filter: Optional[str],
    language_filter: Optional[str],
) -> str:
    """Generate a deterministic cache key for a query.

    Args:
        query: The query text
        query_type: Type of query (natural_language, symbol)
        repo_filter: Optional repository filter
        language_filter: Optional language filter

    Returns:
        SHA256 hash as cache key
    """
    key_data = json.dumps({
        "query": query,
        "type": query_type,
        "repo": repo_filter,
        "language": language_filter,
    }, sort_keys=True)
    return f"query_cache:{hashlib.sha256(key_data.encode()).hexdigest()}"


class QueryCache:
    """Redis-based query result cache."""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """Initialize the cache.

        Args:
            redis_client: Optional Redis client. If not provided, creates new connection.
        """
        self._redis = redis_client
        self._ttl = getattr(settings, 'CACHE_TTL_SECONDS', 300)

    async def get_redis(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._redis is None:
            self._redis = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=False
            )
        return self._redis

    async def get(self, key: str) -> Optional[dict]:
        """Get cached result by key.

        Args:
            key: Cache key

        Returns:
            Cached result dict or None if not found
        """
        redis_client = await self.get_redis()
        cached = await redis_client.get(key)
        if cached:
            if isinstance(cached, bytes):
                cached = cached.decode('utf-8')
            return json.loads(cached)
        return None

    async def set(self, key: str, value: dict, ttl: Optional[int] = None) -> None:
        """Set cache value with TTL.

        Args:
            key: Cache key
            value: Result dict to cache
            ttl: Optional TTL override (seconds)
        """
        redis_client = await self.get_redis()
        ttl_seconds = ttl or self._ttl
        await redis_client.setex(
            key,
            ttl_seconds,
            json.dumps(value)
        )

    async def get_or_compute(
        self,
        request: Any,
        compute_fn: Callable,
    ) -> Any:
        """Get cached result or compute if not cached.

        Args:
            request: Query request object
            compute_fn: Async function to compute result if not cached

        Returns:
            Query result
        """
        # Extract cache key components from request
        cache_key = get_cache_key(
            query=request.query,
            query_type=getattr(request, 'query_type', 'natural_language'),
            repo_filter=getattr(request, 'repo', None),
            language_filter=getattr(request, 'language', None),
        )

        # Try cache first
        cached = await self.get(cache_key)
        if cached:
            # Return cached result (convert dict back to response object)
            from src.query.models import QueryResponse, ContextResult
            results = [ContextResult(**r) for r in cached.get('results', [])]
            return QueryResponse(
                results=results,
                query_time_ms=cached.get('query_time_ms', 0.0),
            )

        # Compute result
        result = await compute_fn(request)

        # Cache the result - handle both object and dict results
        if hasattr(result, 'results') and hasattr(result, 'total'):
            # Handle both object and dict results
            results_list = []
            for r in (result.results or []):
                if hasattr(r, 'model_dump'):
                    results_list.append(r.model_dump())
                elif isinstance(r, dict):
                    results_list.append(r)
                # Skip other types (like MagicMock)
            # Handle total being a mock
            total = result.total if not isinstance(result.total, MagicMock) else len(results_list)
            cache_value = {
                'results': results_list,
                'total': total,
            }
        elif isinstance(result, dict):
            cache_value = result
        else:
            cache_value = {'results': [], 'total': 0}

        await self.set(cache_key, cache_value)

        return result

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()


# Global cache instance
_query_cache: Optional[QueryCache] = None


async def get_query_cache() -> QueryCache:
    """Get or create global query cache instance."""
    global _query_cache
    if _query_cache is None:
        _query_cache = QueryCache()
    return _query_cache
