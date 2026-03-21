"""APIKeyManager — CRUD operations for API keys."""

import hashlib
import logging
import secrets
from uuid import UUID

from sqlalchemy import select

from src.shared.models.api_key import ApiKey
from src.shared.models.api_key_repo_access import ApiKeyRepoAccess
from src.shared.services.auth_middleware import AUTH_KEY_PREFIX

logger = logging.getLogger(__name__)


class APIKeyManager:
    """Service for API key lifecycle management (create, revoke, rotate, list)."""

    def __init__(self, session_factory, redis_client) -> None:
        self._session_factory = session_factory
        self._redis = redis_client

    async def create_key(
        self,
        name: str,
        role: str,
        repo_ids: list[UUID] | None = None,
    ) -> tuple[str, ApiKey]:
        """Generate a new API key, store its hash, and return (plaintext, ApiKey)."""
        if not name or not name.strip():
            raise ValueError("name must not be empty")
        if role not in ("read", "admin"):
            raise ValueError("role must be 'read' or 'admin'")

        plaintext = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(plaintext.encode()).hexdigest()

        api_key = ApiKey(
            key_hash=key_hash,
            name=name,
            role=role,
            is_active=True,
        )

        async with self._session_factory() as session:
            session.add(api_key)

            if repo_ids:
                for repo_id in repo_ids:
                    access = ApiKeyRepoAccess(
                        api_key_id=api_key.id,
                        repo_id=repo_id,
                    )
                    session.add(access)

            await session.commit()

        return plaintext, api_key

    async def revoke_key(self, key_id: UUID) -> None:
        """Deactivate an API key and invalidate its cache."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(ApiKey).where(ApiKey.id == key_id)
            )
            api_key = result.scalar_one_or_none()

            if api_key is None:
                raise KeyError(f"API key {key_id} not found")

            api_key.is_active = False
            await session.commit()

        # Invalidate Redis cache
        try:
            await self._redis._client.delete(f"{AUTH_KEY_PREFIX}{api_key.key_hash}")
        except Exception:
            logger.warning("Redis unavailable during cache invalidation on revoke")

    async def rotate_key(self, key_id: UUID) -> tuple[str, ApiKey]:
        """Revoke old key and create a new one with the same name/role/repos."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(ApiKey).where(ApiKey.id == key_id)
            )
            old_key = result.scalar_one_or_none()

            if old_key is None:
                raise KeyError(f"API key {key_id} not found")
            if not old_key.is_active:
                raise ValueError("Cannot rotate an inactive key")

            # Get repo associations
            repos_result = await session.execute(
                select(ApiKeyRepoAccess.repo_id).where(
                    ApiKeyRepoAccess.api_key_id == key_id
                )
            )
            repo_ids = repos_result.scalars().all()

            # Deactivate old key
            old_key.is_active = False
            await session.commit()

        # Invalidate old key cache
        try:
            await self._redis._client.delete(f"{AUTH_KEY_PREFIX}{old_key.key_hash}")
        except Exception:
            logger.warning("Redis unavailable during cache invalidation on rotate")

        # Create new key with same name/role/repos
        return await self.create_key(
            name=old_key.name,
            role=old_key.role,
            repo_ids=repo_ids if repo_ids else None,
        )

    async def list_keys(self) -> list[ApiKey]:
        """Return all API keys (active and inactive)."""
        async with self._session_factory() as session:
            result = await session.execute(select(ApiKey))
            return list(result.scalars().all())
