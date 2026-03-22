#!/usr/bin/env python3
"""Example: Query Cache (Feature #25).

Demonstrates the L1 in-memory cache with set/get/invalidate operations.
Redis is not required — QueryCache degrades gracefully without it.
"""

import asyncio

from src.query.query_cache import QueryCache
from src.query.response_models import QueryResponse


async def main():
    # Create cache without Redis (L1 only)
    cache = QueryCache(redis_client=None, default_ttl=300)

    # Build a sample response
    response = QueryResponse(
        query="how to parse JSON in Python",
        query_type="nl",
        code_results=[],
        doc_results=[],
    )

    # Cache miss
    result = await cache.get("how to parse JSON in Python", "my-repo", ["python"])
    print(f"Before set: {result}")  # None

    # Store in cache
    await cache.set("how to parse JSON in Python", "my-repo", ["python"], response)
    print("Stored in cache.")

    # Cache hit
    result = await cache.get("how to parse JSON in Python", "my-repo", ["python"])
    print(f"After set: query={result.query}, type={result.query_type}, degraded={result.degraded}")

    # Invalidate repo
    await cache.invalidate_repo("my-repo")
    result = await cache.get("how to parse JSON in Python", "my-repo", ["python"])
    print(f"After invalidate: {result}")  # None


if __name__ == "__main__":
    asyncio.run(main())
