# [no integration test] — Auth middleware uses mocked DB/Redis; real integration tested in Feature #17 (REST endpoints)
"""Tests for Feature #16 — API Key Authentication (T01–T34)."""

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.shared.models.api_key import ApiKey
from src.shared.models.api_key_repo_access import ApiKeyRepoAccess


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_api_key(
    *,
    key_hash: str = "abc123",
    name: str = "test-key",
    role: str = "admin",
    is_active: bool = True,
    expires_at: datetime | None = None,
    key_id: uuid.UUID | None = None,
) -> ApiKey:
    """Build an ApiKey instance with defaults using SA constructor."""
    ak = ApiKey(
        key_hash=key_hash,
        name=name,
        role=role,
        is_active=is_active,
        expires_at=expires_at,
    )
    # id has default=uuid.uuid4 but doesn't auto-generate outside session;
    # force-set it for test purposes.
    ak.id = key_id or uuid.uuid4()
    ak.created_at = datetime.now(timezone.utc)
    return ak


def _hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def _cached_json(ak: ApiKey) -> str:
    """Serialize an ApiKey the same way the middleware does."""
    data = {
        "id": str(ak.id),
        "key_hash": ak.key_hash,
        "name": ak.name,
        "role": ak.role,
        "is_active": ak.is_active,
        "created_at": ak.created_at.isoformat() if ak.created_at else None,
        "expires_at": ak.expires_at.isoformat() if ak.expires_at else None,
    }
    return json.dumps(data)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def redis_client():
    rc = MagicMock()
    rc._client = AsyncMock()
    rc._client.get = AsyncMock(return_value=None)
    rc._client.set = AsyncMock()
    rc._client.incr = AsyncMock(return_value=1)
    rc._client.expire = AsyncMock()
    rc._client.delete = AsyncMock()
    return rc


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def session_factory(mock_session):
    """Returns an async context-manager factory that yields mock_session."""
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _factory():
        yield mock_session

    return _factory


@pytest.fixture
def middleware(session_factory, redis_client):
    from src.shared.services.auth_middleware import AuthMiddleware
    return AuthMiddleware(session_factory=session_factory, redis_client=redis_client)


@pytest.fixture
def manager(session_factory, redis_client):
    from src.shared.services.api_key_manager import APIKeyManager
    return APIKeyManager(session_factory=session_factory, redis_client=redis_client)


def _mock_request(api_key: str | None = None, client_ip: str = "127.0.0.1"):
    req = MagicMock()
    if api_key is not None:
        req.headers = {"x-api-key": api_key}
    else:
        req.headers = {}
    req.client = MagicMock()
    req.client.host = client_ip
    req.state = MagicMock()
    return req


# ---------------------------------------------------------------------------
# AuthMiddleware tests
# ---------------------------------------------------------------------------

# [unit] — T01: happy path, valid API key
@pytest.mark.asyncio
async def test_valid_api_key_returns_api_key(middleware, redis_client, mock_session):
    """T01: Valid key in X-API-Key header → returns ApiKey, sets request.state.api_key."""
    plaintext = "test-key-plaintext-value-abcdefgh12345"
    key_hash = _hash(plaintext)
    ak = _make_api_key(key_hash=key_hash, role="admin")

    # Redis cache miss, DB returns the key
    redis_client._client.get = AsyncMock(return_value=None)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=ak)
    mock_session.execute = AsyncMock(return_value=result_mock)

    req = _mock_request(api_key=plaintext)
    result = await middleware(req)

    assert result.key_hash == key_hash
    assert req.state.api_key == result


# [unit] — T02: happy path, admin key permission check
@pytest.mark.asyncio
async def test_admin_check_permission_query(middleware):
    """T02: Admin key + action='query' → check_permission True."""
    ak = _make_api_key(role="admin")
    assert middleware.check_permission(ak, "query") is True


# [unit] — T03: happy path, read key with repo access
@pytest.mark.asyncio
async def test_read_key_query_with_repo_access(middleware, mock_session):
    """T03: Read key with repo in scoped list → permission True & repo access True."""
    ak = _make_api_key(role="read")
    repo_id = uuid.uuid4()

    assert middleware.check_permission(ak, "query") is True

    # Mock DB returning a matching ApiKeyRepoAccess row
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=MagicMock())
    mock_session.execute = AsyncMock(return_value=result_mock)

    assert await middleware.check_repo_access(ak, repo_id) is True


# [unit] — T04: happy path, create_key returns plaintext and model
@pytest.mark.asyncio
async def test_create_key_returns_plaintext_and_model(manager, mock_session):
    """T04: create_key returns (plaintext, ApiKey) with len(plaintext)==43 and correct hash."""
    plaintext, api_key = await manager.create_key("test", "read")

    assert len(plaintext) == 43
    assert api_key.key_hash == _hash(plaintext)
    mock_session.commit.assert_awaited_once()


# [unit] — T05: happy path, list_keys returns all
@pytest.mark.asyncio
async def test_list_keys_returns_all(manager, mock_session):
    """T05: list_keys with 3 keys in DB → returns list of 3."""
    keys = [_make_api_key(name=f"key-{i}") for i in range(3)]
    result_mock = MagicMock()
    result_mock.all = MagicMock(return_value=keys)
    scalars_mock = MagicMock(return_value=result_mock)
    exec_result = MagicMock()
    exec_result.scalars = scalars_mock
    mock_session.execute = AsyncMock(return_value=exec_result)

    result = await manager.list_keys()
    assert len(result) == 3


# [unit] — T06: happy path, revoke_key sets inactive
@pytest.mark.asyncio
async def test_revoke_key_sets_inactive(manager, mock_session, redis_client):
    """T06: revoke_key(key_id) → is_active set to False."""
    ak = _make_api_key(is_active=True)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=ak)
    mock_session.execute = AsyncMock(return_value=result_mock)

    await manager.revoke_key(ak.id)

    assert ak.is_active is False
    mock_session.commit.assert_awaited_once()


# [unit] — T07: happy path, rotate_key deactivates old, creates new
@pytest.mark.asyncio
async def test_rotate_key_deactivates_old_creates_new(manager, mock_session, redis_client):
    """T07: rotate_key → old key deactivated, new key has same name/role."""
    old_ak = _make_api_key(name="my-key", role="read", is_active=True)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=old_ak)
    mock_session.execute = AsyncMock(return_value=result_mock)

    # For rotate, we need: lookup old key, then create new one
    # The repo_ids query returns empty list (scalars().all())
    repos_result = MagicMock()
    repos_result.all = MagicMock(return_value=[])
    repos_scalars = MagicMock(return_value=repos_result)
    repos_exec = MagicMock()
    repos_exec.scalars = repos_scalars

    # First execute: lookup old key; Second execute: lookup repos
    mock_session.execute = AsyncMock(side_effect=[result_mock, repos_exec])

    new_plaintext, new_ak = await manager.rotate_key(old_ak.id)

    assert old_ak.is_active is False
    assert new_ak.name == "my-key"
    assert new_ak.role == "read"
    assert len(new_plaintext) == 43


# [unit] — T08: happy path, validate_api_key uses Redis cache
@pytest.mark.asyncio
async def test_validate_uses_redis_cache(middleware, redis_client, mock_session):
    """T08: Key cached in Redis → returns ApiKey without DB hit."""
    plaintext = "cached-key-plaintext-1234567890abcdef"
    key_hash = _hash(plaintext)
    ak = _make_api_key(key_hash=key_hash)

    # validate_api_key only calls redis.get once (for the auth_key cache)
    redis_client._client.get = AsyncMock(return_value=_cached_json(ak).encode())

    result = await middleware.validate_api_key(plaintext, "127.0.0.1")

    assert result.key_hash == key_hash
    mock_session.execute.assert_not_awaited()


# [unit] — T09: error, missing X-API-Key header
@pytest.mark.asyncio
async def test_missing_header_raises_401(middleware):
    """T09: No X-API-Key header → HTTPException(401)."""
    from fastapi import HTTPException

    req = _mock_request(api_key=None)
    with pytest.raises(HTTPException) as exc_info:
        await middleware(req)
    assert exc_info.value.status_code == 401
    assert "Missing API key" in str(exc_info.value.detail)


# [unit] — T10: error, invalid API key
@pytest.mark.asyncio
async def test_invalid_key_raises_401(middleware, redis_client, mock_session):
    """T10: Key not in DB → HTTPException(401) 'Invalid API key'."""
    from fastapi import HTTPException

    redis_client._client.get = AsyncMock(return_value=None)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=None)
    mock_session.execute = AsyncMock(return_value=result_mock)

    req = _mock_request(api_key="nonexistent-key-12345678901234567")
    with pytest.raises(HTTPException) as exc_info:
        await middleware(req)
    assert exc_info.value.status_code == 401
    assert "Invalid API key" in str(exc_info.value.detail)


# [unit] — T11: error, expired API key
@pytest.mark.asyncio
async def test_expired_key_raises_401(middleware, redis_client, mock_session):
    """T11: Expired key → HTTPException(401) 'API key has expired'."""
    from fastapi import HTTPException

    plaintext = "expired-key-plaintext-1234567890abcde"
    key_hash = _hash(plaintext)
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    ak = _make_api_key(key_hash=key_hash, expires_at=past)

    redis_client._client.get = AsyncMock(return_value=None)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=ak)
    mock_session.execute = AsyncMock(return_value=result_mock)

    req = _mock_request(api_key=plaintext)
    with pytest.raises(HTTPException) as exc_info:
        await middleware(req)
    assert exc_info.value.status_code == 401
    assert "expired" in str(exc_info.value.detail).lower()


# [unit] — T12: error, inactive API key
@pytest.mark.asyncio
async def test_inactive_key_raises_401(middleware, redis_client, mock_session):
    """T12: Inactive key → HTTPException(401) 'API key is inactive'."""
    from fastapi import HTTPException

    plaintext = "inactive-key-plaintext-123456789012345"
    key_hash = _hash(plaintext)
    ak = _make_api_key(key_hash=key_hash, is_active=False)

    redis_client._client.get = AsyncMock(return_value=None)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=ak)
    mock_session.execute = AsyncMock(return_value=result_mock)

    req = _mock_request(api_key=plaintext)
    with pytest.raises(HTTPException) as exc_info:
        await middleware(req)
    assert exc_info.value.status_code == 401
    assert "inactive" in str(exc_info.value.detail).lower()


# [unit] — T13: error, rate limit exceeded
# Security: Rate limiting tested via T13, T22, T23
@pytest.mark.asyncio
async def test_rate_limit_exceeded_raises_429(middleware, redis_client):
    """T13: 11+ failed attempts → HTTPException(429)."""
    from fastapi import HTTPException

    # Redis returns fail count of 11
    redis_client._client.get = AsyncMock(return_value=b"11")

    req = _mock_request(api_key="some-key-1234567890123456789012345")
    with pytest.raises(HTTPException) as exc_info:
        await middleware(req)
    assert exc_info.value.status_code == 429


# [unit] — T14: error, revoke non-existent key
@pytest.mark.asyncio
async def test_revoke_nonexistent_raises_key_error(manager, mock_session):
    """T14: revoke_key with unknown key_id → KeyError."""
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=None)
    mock_session.execute = AsyncMock(return_value=result_mock)

    with pytest.raises(KeyError):
        await manager.revoke_key(uuid.uuid4())


# [unit] — T15: error, rotate non-existent key
@pytest.mark.asyncio
async def test_rotate_nonexistent_raises_key_error(manager, mock_session):
    """T15: rotate_key with unknown key_id → KeyError."""
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=None)
    mock_session.execute = AsyncMock(return_value=result_mock)

    with pytest.raises(KeyError):
        await manager.rotate_key(uuid.uuid4())


# [unit] — T16: error, rotate inactive key
@pytest.mark.asyncio
async def test_rotate_inactive_raises_value_error(manager, mock_session):
    """T16: rotate_key on inactive key → ValueError."""
    ak = _make_api_key(is_active=False)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=ak)
    mock_session.execute = AsyncMock(return_value=result_mock)

    with pytest.raises(ValueError):
        await manager.rotate_key(ak.id)


# [unit] — T17: error, create_key with empty name
@pytest.mark.asyncio
async def test_create_empty_name_raises_value_error(manager):
    """T17: create_key('', 'read') → ValueError."""
    with pytest.raises(ValueError, match="name must not be empty"):
        await manager.create_key("", "read")


# [unit] — T18: error, create_key with invalid role
@pytest.mark.asyncio
async def test_create_invalid_role_raises_value_error(manager):
    """T18: create_key('test', 'superadmin') → ValueError."""
    with pytest.raises(ValueError, match="role must be"):
        await manager.create_key("test", "superadmin")


# [unit] — T19: error, read key cannot manage_keys
@pytest.mark.asyncio
async def test_read_key_cannot_manage_keys(middleware):
    """T19: check_permission(read_key, 'manage_keys') → False."""
    ak = _make_api_key(role="read")
    assert middleware.check_permission(ak, "manage_keys") is False


# [unit] — T20: error, read key cannot register_repo
@pytest.mark.asyncio
async def test_read_key_cannot_register_repo(middleware):
    """T20: check_permission(read_key, 'register_repo') → False."""
    ak = _make_api_key(role="read")
    assert middleware.check_permission(ak, "register_repo") is False


# [unit] — T21: error, read key no access to unscoped repo
@pytest.mark.asyncio
async def test_read_key_no_access_to_unscoped_repo(middleware, mock_session):
    """T21: check_repo_access(read_key, unscoped_repo) → False."""
    ak = _make_api_key(role="read")
    repo_id = uuid.uuid4()

    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=None)
    mock_session.execute = AsyncMock(return_value=result_mock)

    assert await middleware.check_repo_access(ak, repo_id) is False


# [unit] — T22: boundary, rate limit at exactly 10 → allowed
@pytest.mark.asyncio
async def test_rate_limit_at_10_allowed(middleware, redis_client):
    """T22: fail_count==10 → allowed (limit is >10)."""
    redis_client._client.get = AsyncMock(return_value=b"10")
    assert await middleware.check_rate_limit("127.0.0.1") is True


# [unit] — T23: boundary, rate limit at 11 → blocked
@pytest.mark.asyncio
async def test_rate_limit_at_11_blocked(middleware, redis_client):
    """T23: fail_count==11 → blocked."""
    redis_client._client.get = AsyncMock(return_value=b"11")
    assert await middleware.check_rate_limit("127.0.0.1") is False


# [unit] — T24: boundary, expires_at == utcnow() → expired
@pytest.mark.asyncio
async def test_expires_at_now_is_expired(middleware, redis_client, mock_session):
    """T24: expires_at exactly now → treated as expired."""
    from fastapi import HTTPException

    now = datetime.now(timezone.utc)
    plaintext = "expiring-now-key-12345678901234567890"
    key_hash = _hash(plaintext)
    ak = _make_api_key(key_hash=key_hash, expires_at=now)

    redis_client._client.get = AsyncMock(return_value=None)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=ak)
    mock_session.execute = AsyncMock(return_value=result_mock)

    with pytest.raises(HTTPException) as exc_info:
        await middleware.validate_api_key(plaintext, "127.0.0.1")
    assert exc_info.value.status_code == 401


# [unit] — T25: boundary, expires_at is None → valid forever
@pytest.mark.asyncio
async def test_no_expiry_is_valid_forever(middleware, redis_client, mock_session):
    """T25: expires_at=None → key valid forever."""
    plaintext = "forever-key-plaintext-12345678901234567"
    key_hash = _hash(plaintext)
    ak = _make_api_key(key_hash=key_hash, expires_at=None)

    redis_client._client.get = AsyncMock(return_value=None)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=ak)
    mock_session.execute = AsyncMock(return_value=result_mock)

    result = await middleware.validate_api_key(plaintext, "127.0.0.1")
    assert result.key_hash == key_hash


# [unit] — T26: boundary, create_key with empty repo_ids list
@pytest.mark.asyncio
async def test_create_key_empty_repo_ids_list(manager, mock_session):
    """T26: create_key('x', 'read', []) → key created, no repo access rows."""
    plaintext, ak = await manager.create_key("x", "read", repo_ids=[])
    assert len(plaintext) == 43
    # session.add called once for ApiKey only (no repo access rows)
    assert mock_session.add.call_count == 1


# [unit] — T27: boundary, 1-char name
@pytest.mark.asyncio
async def test_create_key_single_char_name(manager, mock_session):
    """T27: create_key('x', 'read') → valid."""
    plaintext, ak = await manager.create_key("x", "read")
    assert ak.name == "x"


# [unit] — T28: state, revoked key rejected on validate
@pytest.mark.asyncio
async def test_revoked_key_rejected_on_validate(middleware, redis_client, mock_session):
    """T28: Create → Revoke → Validate → 401."""
    from fastapi import HTTPException

    plaintext = "revoked-key-plaintext-123456789012345"
    key_hash = _hash(plaintext)
    ak = _make_api_key(key_hash=key_hash, is_active=False)

    redis_client._client.get = AsyncMock(return_value=None)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=ak)
    mock_session.execute = AsyncMock(return_value=result_mock)

    with pytest.raises(HTTPException) as exc_info:
        await middleware.validate_api_key(plaintext, "127.0.0.1")
    assert exc_info.value.status_code == 401


# [unit] — T29: state, rotated old key rejected
@pytest.mark.asyncio
async def test_rotated_old_key_rejected(middleware, redis_client, mock_session):
    """T29: After rotate, old key → 401 (is_active=False)."""
    from fastapi import HTTPException

    old_plaintext = "old-rotated-key-plaintext-1234567890123"
    old_hash = _hash(old_plaintext)
    old_ak = _make_api_key(key_hash=old_hash, is_active=False)

    redis_client._client.get = AsyncMock(return_value=None)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=old_ak)
    mock_session.execute = AsyncMock(return_value=result_mock)

    with pytest.raises(HTTPException) as exc_info:
        await middleware.validate_api_key(old_plaintext, "127.0.0.1")
    assert exc_info.value.status_code == 401


# [unit] — T30: error, Redis down → falls back to DB
@pytest.mark.asyncio
async def test_redis_down_falls_back_to_db(middleware, redis_client, mock_session):
    """T30: Redis raises exception during validate → DB fallback works."""
    plaintext = "redis-down-key-plaintext-12345678901234"
    key_hash = _hash(plaintext)
    ak = _make_api_key(key_hash=key_hash)

    # Redis raises on both get calls (rate_limit and auth_key)
    redis_client._client.get = AsyncMock(side_effect=Exception("Redis down"))
    redis_client._client.set = AsyncMock(side_effect=Exception("Redis down"))

    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=ak)
    mock_session.execute = AsyncMock(return_value=result_mock)

    result = await middleware.validate_api_key(plaintext, "127.0.0.1")
    assert result.key_hash == key_hash


# [unit] — T31: error, Redis down during rate limit → fail open
@pytest.mark.asyncio
async def test_redis_down_rate_limit_fails_open(middleware, redis_client):
    """T31: Redis exception during check_rate_limit → returns True (allow)."""
    redis_client._client.get = AsyncMock(side_effect=Exception("Redis down"))
    result = await middleware.check_rate_limit("127.0.0.1")
    assert result is True


# [unit] — T32: happy path, create_key with repo_ids
@pytest.mark.asyncio
async def test_create_key_with_repo_ids(manager, mock_session):
    """T32: create_key with repo_ids → ApiKeyRepoAccess rows created."""
    repo_id = uuid.uuid4()
    plaintext, ak = await manager.create_key("test", "read", repo_ids=[repo_id])

    # session.add called twice: once for ApiKey, once for ApiKeyRepoAccess
    assert mock_session.add.call_count == 2


# [unit] — T33: happy path, admin bypasses repo scoping
@pytest.mark.asyncio
async def test_admin_bypasses_repo_scoping(middleware):
    """T33: Admin key → check_repo_access returns True for any repo."""
    ak = _make_api_key(role="admin")
    repo_id = uuid.uuid4()
    assert await middleware.check_repo_access(ak, repo_id) is True


# [unit] — T34: happy path, revoke invalidates cache
@pytest.mark.asyncio
async def test_revoke_invalidates_cache(manager, mock_session, redis_client):
    """T34: revoke_key → Redis cache entry deleted."""
    ak = _make_api_key(key_hash="somehash", is_active=True)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=ak)
    mock_session.execute = AsyncMock(return_value=result_mock)

    await manager.revoke_key(ak.id)

    redis_client._client.delete.assert_awaited_once_with("auth_key:somehash")
