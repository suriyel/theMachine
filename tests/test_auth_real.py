"""Real integration tests for API Key Authentication (Feature #16).

These tests run against real PostgreSQL and Redis instances.
No mocks on primary dependencies.

External dependencies tested:
- PostgreSQL: API key CRUD (create, lookup by hash, revoke, rotate, list)
- Redis: rate limit counters (INCR/EXPIRE/GET), auth key caching (SET/GET/DELETE)

Requires:
- DATABASE_URL env var pointing to a live PostgreSQL with api_key table
- REDIS_URL env var pointing to a live Redis instance
"""

from __future__ import annotations

import os

# Clear SOCKS proxy before any aiohttp/redis imports.
# See env-guide.md "Proxy Configuration" section.
for _k in ("ALL_PROXY", "all_proxy"):
    os.environ.pop(_k, None)
os.environ.setdefault("NO_PROXY", "localhost,127.0.0.1")
os.environ.setdefault("no_proxy", "localhost,127.0.0.1")

import asyncio
import hashlib
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import pytest
import redis.asyncio as aioredis
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.shared.clients.redis import RedisClient
from src.shared.models.api_key import ApiKey
from src.shared.models.api_key_repo_access import ApiKeyRepoAccess
from src.shared.services.api_key_manager import APIKeyManager
from src.shared.services.auth_middleware import AuthMiddleware

# Skip all tests if services are not available
DATABASE_URL = os.environ.get("DATABASE_URL", "")
REDIS_URL = os.environ.get("REDIS_URL", "")

pytestmark = [
    pytest.mark.real,
    pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL not set"),
    pytest.mark.skipif(not REDIS_URL, reason="REDIS_URL not set"),
]


# ---------------------------------------------------------------------------
# Fixtures — real DB + Redis
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _set_no_proxy_for_localhost(monkeypatch):
    """Ensure localhost bypasses proxy for real tests."""
    monkeypatch.setenv("NO_PROXY", "localhost,127.0.0.1")
    monkeypatch.setenv("no_proxy", "localhost,127.0.0.1")


@pytest.fixture
async def engine():
    eng = create_async_engine(DATABASE_URL, echo=False)
    yield eng
    await eng.dispose()


@pytest.fixture
def session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def db_session(session_factory):
    """Yield a session and rollback after each test for isolation."""
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def redis_client():
    """Provide a real RedisClient connected to the test Redis instance."""
    client = RedisClient(REDIS_URL)
    await client.connect()
    yield client
    # Clean up test keys
    if client._client:
        keys = await client._client.keys("rate_limit:test_*")
        keys += await client._client.keys("auth_key:test_*")
        if keys:
            await client._client.delete(*keys)
        await client.close()


@pytest.fixture
def auth_middleware(session_factory, redis_client):
    return AuthMiddleware(session_factory=session_factory, redis_client=redis_client)


@pytest.fixture
def api_key_manager(session_factory, redis_client):
    return APIKeyManager(session_factory=session_factory, redis_client=redis_client)


@pytest.fixture
async def cleanup_keys(session_factory):
    """Track and clean up any ApiKey rows created during tests."""
    created_ids: list[uuid.UUID] = []
    yield created_ids
    async with session_factory() as session:
        if created_ids:
            await session.execute(
                delete(ApiKeyRepoAccess).where(
                    ApiKeyRepoAccess.api_key_id.in_(created_ids)
                )
            )
            await session.execute(
                delete(ApiKey).where(ApiKey.id.in_(created_ids))
            )
            await session.commit()


# ===========================================================================
# PostgreSQL real tests — APIKeyManager CRUD
# ===========================================================================


# [integration] RT-01: create_key stores SHA-256 hash in real PostgreSQL
@pytest.mark.asyncio
async def test_create_key_stores_hash_in_real_db(
    api_key_manager, db_session, cleanup_keys
):
    """VS-4: create_key generates key, stores SHA-256 hash in PostgreSQL."""
    plaintext, api_key = await api_key_manager.create_key(
        name="real-test-key", role="read"
    )
    cleanup_keys.append(api_key.id)

    # Verify plaintext properties
    assert len(plaintext) == 43  # secrets.token_urlsafe(32) length
    assert api_key.name == "real-test-key"
    assert api_key.role == "read"
    assert api_key.is_active is True

    # Verify hash matches
    expected_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    assert api_key.key_hash == expected_hash

    # Verify actually persisted in DB
    from sqlalchemy import select

    result = await db_session.execute(
        select(ApiKey).where(ApiKey.id == api_key.id)
    )
    db_key = result.scalar_one_or_none()
    assert db_key is not None
    assert db_key.key_hash == expected_hash
    assert db_key.name == "real-test-key"


# [integration] RT-02: revoke_key sets is_active=False in real DB
@pytest.mark.asyncio
async def test_revoke_key_persists_in_real_db(
    api_key_manager, db_session, cleanup_keys
):
    """Revoke persists is_active=False to real PostgreSQL."""
    plaintext, api_key = await api_key_manager.create_key(
        name="revoke-test", role="admin"
    )
    cleanup_keys.append(api_key.id)

    await api_key_manager.revoke_key(api_key.id)

    # Verify in real DB
    from sqlalchemy import select

    result = await db_session.execute(
        select(ApiKey).where(ApiKey.id == api_key.id)
    )
    db_key = result.scalar_one_or_none()
    assert db_key is not None
    assert db_key.is_active is False


# [integration] RT-03: rotate_key creates new key and deactivates old in real DB
@pytest.mark.asyncio
async def test_rotate_key_in_real_db(
    api_key_manager, db_session, cleanup_keys
):
    """Rotate deactivates old, creates new with same name/role in real DB."""
    plaintext_old, old_key = await api_key_manager.create_key(
        name="rotate-test", role="read"
    )
    cleanup_keys.append(old_key.id)

    new_plaintext, new_key = await api_key_manager.rotate_key(old_key.id)
    cleanup_keys.append(new_key.id)

    # Old key deactivated
    from sqlalchemy import select

    result = await db_session.execute(
        select(ApiKey).where(ApiKey.id == old_key.id)
    )
    db_old = result.scalar_one()
    assert db_old.is_active is False

    # New key active with same name/role
    result = await db_session.execute(
        select(ApiKey).where(ApiKey.id == new_key.id)
    )
    db_new = result.scalar_one()
    assert db_new.is_active is True
    assert db_new.name == "rotate-test"
    assert db_new.role == "read"
    assert new_plaintext != plaintext_old


# [integration] RT-04: list_keys returns all from real DB
@pytest.mark.asyncio
async def test_list_keys_from_real_db(api_key_manager, cleanup_keys):
    """list_keys returns real DB rows."""
    _, k1 = await api_key_manager.create_key(name="list-test-1", role="read")
    _, k2 = await api_key_manager.create_key(name="list-test-2", role="admin")
    cleanup_keys.extend([k1.id, k2.id])

    keys = await api_key_manager.list_keys()
    key_names = {k.name for k in keys}
    assert "list-test-1" in key_names
    assert "list-test-2" in key_names


# ===========================================================================
# Redis real tests — rate limiting and caching
# ===========================================================================


# [integration] RT-05: rate limit counter increments in real Redis
@pytest.mark.asyncio
async def test_rate_limit_increments_in_real_redis(auth_middleware, redis_client):
    """Rate limit INCR/EXPIRE on real Redis."""
    test_ip = f"test_{uuid.uuid4().hex[:8]}"

    # Initially under limit
    result = await auth_middleware.check_rate_limit(test_ip)
    assert result is True

    # Increment failures
    for _ in range(11):
        await auth_middleware._increment_rate_limit(test_ip)

    # Now over limit
    result = await auth_middleware.check_rate_limit(test_ip)
    assert result is False

    # Verify actual Redis value
    count = await redis_client._client.get(f"rate_limit:{test_ip}")
    assert int(count) == 11

    # Cleanup
    await redis_client._client.delete(f"rate_limit:{test_ip}")


# [integration] RT-06: auth key cache SET/GET/DELETE in real Redis
@pytest.mark.asyncio
async def test_auth_key_cache_in_real_redis(auth_middleware, redis_client):
    """Cache write and read on real Redis."""
    test_hash = f"test_{uuid.uuid4().hex[:8]}"
    cache_key = f"auth_key:{test_hash}"

    # Cache miss
    cached = await redis_client._client.get(cache_key)
    assert cached is None

    # Simulate cache write
    import json

    test_data = json.dumps({"id": str(uuid.uuid4()), "name": "cached-key", "role": "read"})
    await redis_client._client.set(cache_key, test_data, ex=300)

    # Cache hit
    cached = await redis_client._client.get(cache_key)
    assert cached is not None
    parsed = json.loads(cached)
    assert parsed["name"] == "cached-key"

    # Invalidate
    await redis_client._client.delete(cache_key)
    cached = await redis_client._client.get(cache_key)
    assert cached is None


# ===========================================================================
# End-to-end real test — validate_api_key with real DB + Redis
# ===========================================================================


# [integration] RT-07: validate_api_key with real DB lookup and Redis caching
@pytest.mark.asyncio
async def test_validate_api_key_end_to_end(
    api_key_manager, auth_middleware, redis_client, cleanup_keys
):
    """VS-1 + VS-2 end-to-end: create key, validate it, reject invalid key."""
    from fastapi import HTTPException

    # Create a real key
    plaintext, api_key = await api_key_manager.create_key(
        name="e2e-test", role="admin"
    )
    cleanup_keys.append(api_key.id)

    # Validate the real key — hits DB, caches in Redis
    test_ip = f"test_{uuid.uuid4().hex[:8]}"
    validated = await auth_middleware.validate_api_key(plaintext, test_ip)
    assert validated.name == "e2e-test"
    assert validated.role == "admin"
    assert validated.is_active is True

    # Verify it was cached in Redis
    key_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    cached = await redis_client._client.get(f"auth_key:{key_hash}")
    assert cached is not None

    # Invalid key should raise 401
    with pytest.raises(HTTPException) as exc_info:
        await auth_middleware.validate_api_key("bogus-key-12345", test_ip)
    assert exc_info.value.status_code == 401

    # Cleanup Redis
    await redis_client._client.delete(f"auth_key:{key_hash}")
    await redis_client._client.delete(f"rate_limit:{test_ip}")
