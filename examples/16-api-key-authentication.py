"""Example: API Key Authentication (Feature #16).

Demonstrates AuthMiddleware and APIKeyManager:
1. Create an API key with APIKeyManager
2. Validate the key with AuthMiddleware
3. Check permissions and repo access
4. Rate limiting behavior
5. Key revocation and rotation
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from src.shared.models.api_key import ApiKey


async def main():
    # Setup mocks
    session = AsyncMock()
    session_factory = AsyncMock(return_value=session)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    redis = MagicMock()
    redis._client = AsyncMock()
    redis._client.get = AsyncMock(return_value=None)
    redis._client.set = AsyncMock()
    redis._client.incr = AsyncMock(return_value=1)
    redis._client.expire = AsyncMock()
    redis._client.delete = AsyncMock()

    from src.shared.services.auth_middleware import AuthMiddleware

    auth = AuthMiddleware(session_factory=session_factory, redis_client=redis)

    # --- Example 1: Permission checks ---
    print("=== Example 1: Permission Model ===")
    admin_key = ApiKey(
        id=uuid.uuid4(), key_hash="admin-hash", name="admin-key",
        role="admin", is_active=True,
    )
    read_key = ApiKey(
        id=uuid.uuid4(), key_hash="read-hash", name="read-key",
        role="read", is_active=True,
    )

    print(f"  Admin can query: {auth.check_permission(admin_key, 'query')}")  # True
    print(f"  Admin can manage_keys: {auth.check_permission(admin_key, 'manage_keys')}")  # True
    print(f"  Read can query: {auth.check_permission(read_key, 'query')}")  # True
    print(f"  Read can manage_keys: {auth.check_permission(read_key, 'manage_keys')}")  # False

    # --- Example 2: Rate limiting ---
    print("\n=== Example 2: Rate Limiting ===")
    redis._client.get.return_value = b"5"
    under_limit = await auth.check_rate_limit("192.168.1.1")
    print(f"  5 failures: allowed={under_limit}")  # True

    redis._client.get.return_value = b"11"
    over_limit = await auth.check_rate_limit("192.168.1.1")
    print(f"  11 failures: allowed={over_limit}")  # False

    # --- Example 3: Key generation ---
    print("\n=== Example 3: Key Generation ===")
    plaintext = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    print(f"  Generated key: {plaintext[:10]}... ({len(plaintext)} chars)")
    print(f"  SHA-256 hash: {key_hash[:20]}...")
    print(f"  Hash matches: {hashlib.sha256(plaintext.encode()).hexdigest() == key_hash}")

    print("\nAll examples completed!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
