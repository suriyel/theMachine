"""AuthMiddleware — FastAPI dependency for API key authentication."""

import hashlib
import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy import select

from src.shared.models.api_key import ApiKey
from src.shared.models.api_key_repo_access import ApiKeyRepoAccess

logger = logging.getLogger(__name__)

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {"query", "list_repos", "register_repo", "reindex", "manage_keys", "metrics"},
    "read": {"query", "list_repos"},
}

RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX_FAILURES = 10
CACHE_TTL = 300
RATE_LIMIT_PREFIX = "rate_limit:"
AUTH_KEY_PREFIX = "auth_key:"


class AuthMiddleware:
    """FastAPI dependency that validates API keys and enforces auth policies."""

    def __init__(self, session_factory, redis_client) -> None:
        self._session_factory = session_factory
        self._redis = redis_client

    async def __call__(self, request: Request) -> ApiKey:
        """Extract X-API-Key header, validate, and return ApiKey."""
        api_key_header = request.headers.get("x-api-key")
        if not api_key_header:
            raise HTTPException(status_code=401, detail="Missing API key")

        client_ip = request.client.host

        # Check rate limit
        allowed = await self.check_rate_limit(client_ip)
        if not allowed:
            raise HTTPException(status_code=429, detail="Too many failed attempts")

        api_key = await self.validate_api_key(api_key_header, client_ip)
        request.state.api_key = api_key
        return api_key

    async def validate_api_key(self, key: str, client_ip: str) -> ApiKey:
        """Hash the key, check Redis cache, fall back to DB, validate status."""
        key_hash = hashlib.sha256(key.encode()).hexdigest()

        # Step 1: Check Redis cache
        api_key = None
        cache_hit = False
        try:
            cached = await self._redis._client.get(f"{AUTH_KEY_PREFIX}{key_hash}")
            if cached is not None:
                data = json.loads(cached)
                api_key = ApiKey(
                    key_hash=data["key_hash"],
                    name=data["name"],
                    role=data["role"],
                    is_active=data["is_active"],
                )
                api_key.id = UUID(data["id"])
                api_key.created_at = (
                    datetime.fromisoformat(data["created_at"])
                    if data.get("created_at")
                    else None
                )
                api_key.expires_at = (
                    datetime.fromisoformat(data["expires_at"])
                    if data.get("expires_at")
                    else None
                )
                cache_hit = True
        except Exception:
            logger.warning("Redis unavailable during validate_api_key, falling back to DB")

        # Step 2: Query PostgreSQL on cache miss
        if not cache_hit:
            async with self._session_factory() as session:
                result = await session.execute(
                    select(ApiKey).where(ApiKey.key_hash == key_hash)
                )
                api_key = result.scalar_one_or_none()

            if api_key is None:
                await self._increment_rate_limit(client_ip)
                raise HTTPException(status_code=401, detail="Invalid API key")

            # Step 3: Cache result
            try:
                cache_data = json.dumps({
                    "id": str(api_key.id),
                    "key_hash": api_key.key_hash,
                    "name": api_key.name,
                    "role": api_key.role,
                    "is_active": api_key.is_active,
                    "created_at": api_key.created_at.isoformat() if api_key.created_at else None,
                    "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
                })
                await self._redis._client.set(
                    f"{AUTH_KEY_PREFIX}{key_hash}", cache_data, ex=CACHE_TTL
                )
            except Exception:
                logger.warning("Redis unavailable during cache write")

        # Step 4: Validate active status
        if not api_key.is_active:
            await self._increment_rate_limit(client_ip)
            raise HTTPException(status_code=401, detail="API key is inactive")

        # Step 5: Validate expiry
        if api_key.expires_at is not None and api_key.expires_at <= datetime.now(timezone.utc):
            await self._increment_rate_limit(client_ip)
            raise HTTPException(status_code=401, detail="API key has expired")

        return api_key

    async def check_rate_limit(self, client_ip: str) -> bool:
        """Return True if under limit, False if rate limited."""
        try:
            count = await self._redis._client.get(f"{RATE_LIMIT_PREFIX}{client_ip}")
            if count is None:
                return True
            if int(count) > RATE_LIMIT_MAX_FAILURES:
                return False
            return True
        except Exception:
            logger.warning("Redis unavailable during check_rate_limit, failing open")
            return True

    async def _increment_rate_limit(self, client_ip: str) -> None:
        """Increment failure counter in Redis with 60s expiry window."""
        try:
            redis_key = f"{RATE_LIMIT_PREFIX}{client_ip}"
            new_count = await self._redis._client.incr(redis_key)
            if new_count == 1:
                await self._redis._client.expire(redis_key, RATE_LIMIT_WINDOW)
        except Exception:
            logger.warning("Redis unavailable during rate limit increment")

    def check_permission(self, api_key: ApiKey, action: str) -> bool:
        """Check if the api_key's role permits the given action."""
        allowed = ROLE_PERMISSIONS.get(api_key.role, set())
        return action in allowed

    async def check_repo_access(self, api_key: ApiKey, repo_id: UUID) -> bool:
        """Admin has access to all repos; read keys check ApiKeyRepoAccess."""
        if api_key.role == "admin":
            return True

        async with self._session_factory() as session:
            result = await session.execute(
                select(ApiKeyRepoAccess).where(
                    ApiKeyRepoAccess.api_key_id == api_key.id,
                    ApiKeyRepoAccess.repo_id == repo_id,
                )
            )
            return result.scalar_one_or_none() is not None

    async def _invalidate_cache(self, key_hash: str) -> None:
        """Delete the cached auth entry for the given key_hash."""
        try:
            await self._redis._client.delete(f"{AUTH_KEY_PREFIX}{key_hash}")
        except Exception:
            logger.warning("Redis unavailable during cache invalidation")
