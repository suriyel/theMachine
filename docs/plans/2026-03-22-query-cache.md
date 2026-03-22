# Feature #25 — Query Cache: Detailed Design

**Date**: 2026-03-22
**Feature**: FR-019 (Query Cache)
**Status**: In Progress

---

## 1. Overview

Implement a two-level query cache (L1 in-memory + L2 Redis) to avoid re-executing the full retrieval pipeline for repeated queries. Cache key is a SHA-256 hash of the query parameters. TTL = 300s. Cache invalidation occurs on repository reindex.

---

## 2. Interface Contract

### 2.1 Module

`src/query/query_cache.py` — `QueryCache` class

### 2.2 Constructor

```python
QueryCache(redis_client: RedisClient | None = None, default_ttl: int = 300, l1_max_size: int = 1000)
```

- `redis_client`: Optional async Redis client. When `None`, L2 is disabled (graceful degradation).
- `default_ttl`: Time-to-live in seconds for cache entries (default 300).
- `l1_max_size`: Maximum entries in L1 in-memory cache before LRU eviction.

### 2.3 Methods

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `get` | `async get(query: str, repo: str \| None, languages: list[str] \| None) -> QueryResponse \| None` | Cached response or `None` | Checks L1 first, then L2. Returns `None` on miss or error. |
| `set` | `async set(query: str, repo: str \| None, languages: list[str] \| None, response: QueryResponse, ttl: int \| None = None) -> None` | `None` | Stores in both L1 and L2. No-op on error. |
| `invalidate_repo` | `async invalidate_repo(repo_id: str) -> None` | `None` | Removes all L1 entries for the given repo. Deletes matching Redis keys via scan. No-op on error. |
| `_make_key` | `_make_key(query: str, repo: str \| None, languages: list[str] \| None) -> str` | `str` | SHA-256 of `{query}:{repo}:{sorted_languages}`. Deterministic. |

---

## 3. Algorithm Pseudocode

### 3.1 Cache Key Generation (`_make_key`)

```
def _make_key(query, repo, languages):
    langs_str = ",".join(sorted(languages)) if languages else ""
    raw = f"{query}:{repo or ''}:{langs_str}"
    return "qcache:" + sha256(raw.encode()).hexdigest()
```

### 3.2 Cache Get

```
async def get(query, repo, languages):
    key = _make_key(query, repo, languages)

    # L1 check
    if key in _l1_cache and not expired:
        move key to end (LRU)
        return _l1_cache[key].response

    # L2 check (Redis)
    try:
        raw = await redis.get(key)
        if raw:
            response = QueryResponse.model_validate_json(raw)
            store in L1
            return response
    except Exception:
        log warning, return None

    return None
```

### 3.3 Cache Set

```
async def set(query, repo, languages, response, ttl=None):
    key = _make_key(query, repo, languages)
    ttl = ttl or default_ttl

    # L1 store
    _l1_cache[key] = CacheEntry(response, repo, expiry=now+ttl)
    evict LRU if over max_size

    # L2 store (Redis)
    try:
        await redis.setex(key, ttl, response.model_dump_json())
    except Exception:
        log warning, continue
```

### 3.4 Invalidate Repo

```
async def invalidate_repo(repo_id):
    # L1: remove entries matching repo
    keys_to_remove = [k for k, v in _l1_cache.items() if v.repo == repo_id]
    for k in keys_to_remove:
        del _l1_cache[k]

    # L2: scan and delete (best-effort)
    # Store repo association in Redis set "qcache:repo:{repo_id}"
    try:
        members = await redis.smembers(f"qcache:repo:{repo_id}")
        if members:
            await redis.delete(*members)
            await redis.delete(f"qcache:repo:{repo_id}")
    except Exception:
        log warning
```

---

## 4. L1 In-Memory Cache Design

- `OrderedDict` for LRU eviction (move_to_end on access, popitem(last=False) on overflow)
- Each entry stores: `response`, `repo_id`, `expiry_time`
- Bounded to `l1_max_size` entries (default 1000)
- TTL checked on read (lazy expiry)

---

## 5. Graceful Degradation

All Redis operations wrapped in `try/except Exception`:
- On failure: log warning, return `None` (get) or no-op (set/invalidate)
- L1 cache continues to work even when Redis is down
- No exceptions propagated to caller

---

## 6. Test Inventory

| ID | Type | Description |
|----|------|-------------|
| T1 | Happy path | set then get returns same response |
| T2 | Happy path | cache miss returns None |
| T3 | Happy path | same query+repo+lang produces same cache key |
| T4 | Happy path | invalidate_repo clears entries for that repo |
| T5 | Error | Redis unavailable on get returns None (no exception) |
| T6 | Error | Redis unavailable on set — no exception |
| T7 | Boundary | None repo and None languages produce valid key |
| T8 | Boundary | TTL expiry — expired entry returns None |
| T9 | Boundary | different query same repo — different cache entries |
| T10 | Integration | L1 in-memory cache returns before Redis |
