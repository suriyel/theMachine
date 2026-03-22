"""Query Cache — L1 in-memory + L2 Redis two-level cache (Feature #25).

Cache key = SHA-256 of query:repo:languages. TTL = 300s default.
All Redis failures are caught and logged — graceful degradation to L1-only or no-cache.
"""

from __future__ import annotations

import hashlib
import logging
import time
from collections import OrderedDict
from typing import NamedTuple

from src.query.response_models import QueryResponse

log = logging.getLogger(__name__)


class _CacheEntry(NamedTuple):
    """Internal L1 cache entry."""

    response: QueryResponse
    repo: str | None
    expiry: float  # monotonic timestamp


class QueryCache:
    """Two-level query cache: L1 in-memory (OrderedDict LRU) + L2 Redis."""

    def __init__(
        self,
        redis_client=None,
        default_ttl: int = 300,
        l1_max_size: int = 1000,
    ) -> None:
        self._redis = redis_client  # RedisClient instance or None
        self._default_ttl = default_ttl
        self._l1_max_size = l1_max_size
        self._l1_cache: OrderedDict[str, _CacheEntry] = OrderedDict()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get(
        self,
        query: str,
        repo: str | None,
        languages: list[str] | None,
    ) -> QueryResponse | None:
        """Look up a cached response. Returns None on miss or error."""
        key = self._make_key(query, repo, languages)

        # L1 check
        entry = self._l1_cache.get(key)
        if entry is not None:
            if time.monotonic() < entry.expiry:
                self._l1_cache.move_to_end(key)
                return entry.response
            # Expired — remove
            del self._l1_cache[key]

        # L2 check (Redis)
        if self._redis is not None and self._redis._client is not None:
            try:
                raw = await self._redis._client.get(key)
                if raw is not None:
                    response = QueryResponse.model_validate_json(raw)
                    # Promote to L1
                    self._l1_store(key, response, repo, self._default_ttl)
                    return response
            except Exception:
                log.warning("Redis get failed for key %s, degrading to no-cache", key)

        return None

    async def set(
        self,
        query: str,
        repo: str | None,
        languages: list[str] | None,
        response: QueryResponse,
        ttl: int | None = None,
    ) -> None:
        """Store a response in both L1 and L2. No-op on error."""
        key = self._make_key(query, repo, languages)
        ttl = ttl if ttl is not None else self._default_ttl

        # L1 store
        self._l1_store(key, response, repo, ttl)

        # L2 store (Redis)
        if self._redis is not None and self._redis._client is not None:
            try:
                await self._redis._client.setex(key, ttl, response.model_dump_json())
                # Track repo association for invalidation
                if repo is not None:
                    await self._redis._client.sadd(f"qcache:repo:{repo}", key)
            except Exception:
                log.warning("Redis set failed for key %s, L1-only", key)

    async def invalidate_repo(self, repo_id: str) -> None:
        """Invalidate all cache entries for a given repository."""
        # L1: remove matching entries
        keys_to_remove = [
            k for k, v in self._l1_cache.items() if v.repo == repo_id
        ]
        for k in keys_to_remove:
            del self._l1_cache[k]

        # L2: remove via repo tracking set
        if self._redis is not None and self._redis._client is not None:
            try:
                repo_set_key = f"qcache:repo:{repo_id}"
                members = await self._redis._client.smembers(repo_set_key)
                if members:
                    await self._redis._client.delete(*members)
                    await self._redis._client.delete(repo_set_key)
            except Exception:
                log.warning("Redis invalidate_repo failed for %s", repo_id)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _make_key(
        self,
        query: str,
        repo: str | None,
        languages: list[str] | None,
    ) -> str:
        """Generate deterministic SHA-256 cache key."""
        langs_str = ",".join(sorted(languages)) if languages else ""
        raw = f"{query}:{repo or ''}:{langs_str}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return f"qcache:{digest}"

    def _l1_store(
        self,
        key: str,
        response: QueryResponse,
        repo: str | None,
        ttl: int,
    ) -> None:
        """Store entry in L1, evicting LRU if over capacity."""
        expiry = time.monotonic() + ttl
        self._l1_cache[key] = _CacheEntry(
            response=response, repo=repo, expiry=expiry
        )
        self._l1_cache.move_to_end(key)

        # Evict oldest if over capacity
        while len(self._l1_cache) > self._l1_max_size:
            self._l1_cache.popitem(last=False)
