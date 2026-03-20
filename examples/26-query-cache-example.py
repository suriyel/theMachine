"""
Example: Query Cache Usage

Demonstrates how to use the Redis query cache for NFR-001 optimization.
"""

from src.query.cache import QueryCache, get_cache_key
from src.query.models import QueryRequest


def example_cache_key_generation():
    """Example: Generate deterministic cache keys."""
    # Same query generates same key
    key1 = get_cache_key("how to configure spring", "natural_language", None, None)
    key2 = get_cache_key("how to configure spring", "natural_language", None, None)
    assert key1 == key2
    print(f"Cache key: {key1}")

    # Different query generates different key
    key3 = get_cache_key("python flask routing", "natural_language", None, None)
    assert key3 != key1
    print(f"Different query key: {key3}")

    # Repo filter affects key
    key4 = get_cache_key("timeout", "natural_language", "spring-framework", None)
    key5 = get_cache_key("timeout", "natural_language", "django", None)
    assert key4 != key5
    print(f"Repo-filtered keys: {key4}, {key5}")


async def example_cache_usage():
    """Example: Using the cache in a query handler."""
    import asyncio
    from unittest.mock import AsyncMock

    # Create mock Redis client
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None  # Cache miss

    # Create cache instance
    cache = QueryCache(mock_redis)

    # Create a query request
    request = QueryRequest(
        query="how to use WebClient timeout",
        query_type="natural_language"
    )

    # Define a handler that computes the result
    async def compute_result(req):
        # In real code, this would call the full retrieval pipeline
        return {"results": [{"content": "computed result"}], "total": 1}

    # Use cache to get or compute
    result = await cache.get_or_compute(request, compute_result)
    print(f"Result: {result}")

    # Simulate cache hit on second call
    mock_redis.get.return_value = b'{"results": [{"content": "cached"}], "total": 1}'
    result2 = await cache.get_or_compute(request, compute_result)
    print(f"Cached result: {result2}")


if __name__ == "__main__":
    example_cache_key_generation()
    print("Cache key generation example complete!")

    # Run async example
    asyncio.run(example_cache_usage())
    print("Cache usage example complete!")
