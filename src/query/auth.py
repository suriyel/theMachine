"""API Key Authentication Middleware."""

import hashlib
from typing import Optional

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.models.api_key import APIKey, KeyStatus


class AuthMiddleware:
    """Middleware for API key authentication.

    Verifies API keys from request headers against the database.
    """

    def __init__(self, db: AsyncSession):
        """Initialize with database session.

        Args:
            db: AsyncSession for database access
        """
        self._db = db

    async def verify_api_key(self, key: str) -> Optional[APIKey]:
        """Verify API key exists and is active.

        Args:
            key: Plaintext API key from request header

        Returns:
            APIKey record if valid and active, None otherwise
        """
        # Hash the incoming key using SHA-256
        key_hash = hashlib.sha256(key.encode()).hexdigest()

        # Query database for matching hash with ACTIVE status
        stmt = select(APIKey).where(
            APIKey.key_hash == key_hash,
            APIKey.status == KeyStatus.ACTIVE
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def require_auth(self, request: Request) -> APIKey:
        """Verify request has valid API key.

        Args:
            request: FastAPI Request object

        Returns:
            APIKey record for valid requests

        Raises:
            HTTPException: 401 if key missing, invalid, or revoked
        """
        # Extract API key from header
        api_key = request.headers.get("X-API-Key")

        if not api_key:
            raise HTTPException(
                status_code=401,
                detail="Missing API key. Provide X-API-Key header."
            )

        # Verify key
        key_record = await self.verify_api_key(api_key)

        if key_record is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key."
            )

        return key_record
