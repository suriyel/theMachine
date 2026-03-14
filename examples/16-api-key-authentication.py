"""Example: API Key Authentication (FR-018)

This example demonstrates how to use the AuthMiddleware for API key authentication.

The AuthMiddleware:
1. Verifies API keys from X-API-Key header
2. Checks key exists in database with ACTIVE status
3. Returns 401 for missing/invalid/revoked keys
"""

import hashlib
import asyncio

from sqlalchemy import select
from src.shared.db.session import get_db
from src.shared.models.api_key import APIKey, KeyStatus
from src.query.auth import AuthMiddleware


async def create_test_api_key(db, key_name: str, key_value: str) -> APIKey:
    """Create a test API key in the database."""
    key_hash = hashlib.sha256(key_value.encode()).hexdigest()

    api_key = APIKey(
        key_hash=key_hash,
        name=key_name,
        status=KeyStatus.ACTIVE
    )

    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return api_key


async def example_auth_flow():
    """Demonstrate the authentication flow."""
    # Note: In a real application, the database session would be injected
    # by FastAPI's dependency injection system via get_db()

    print("=== API Key Authentication Example ===\n")

    # This is a conceptual example - in practice you'd use FastAPI's
    # dependency injection. See how to integrate with FastAPI below.

    # 1. Verify valid key
    print("1. Valid API key flow:")
    print("   - Client sends: X-API-Key: my-secret-key")
    print("   - AuthMiddleware.hash(key) -> lookup in DB")
    print("   - If found with ACTIVE status -> allow request")
    print()

    # 2. Invalid key
    print("2. Invalid API key flow:")
    print("   - Client sends: X-API-Key: wrong-key")
    print("   - AuthMiddleware.hash(key) -> not found in DB")
    print("   - Returns: 401 Unauthorized, 'Invalid API key.'")
    print()

    # 3. Missing key
    print("3. Missing API key flow:")
    print("   - Client sends: (no X-API-Key header)")
    print("   - AuthMiddleware checks header -> None")
    print("   - Returns: 401 Unauthorized, 'Missing API key. Provide X-API-Key header.'")
    print()

    # 4. Revoked key
    print("4. Revoked API key flow:")
    print("   - Client sends: X-API-Key: revoked-key")
    print("   - AuthMiddleware.hash(key) -> found but status=REVOKED")
    print("   - Query filters by status=ACTIVE -> returns None")
    print("   - Returns: 401 Unauthorized, 'Invalid API key.'")
    print()

    print("=== Integration with FastAPI ===")
    print("""
# In your FastAPI endpoint:

from fastapi import Depends, Request
from src.query.auth import AuthMiddleware
from src.shared.db.session import get_db

async def query_endpoint(request: Request, db = Depends(get_db)):
    auth = AuthMiddleware(db)
    api_key = await auth.require_auth(request)

    # api_key is the authenticated APIKey record
    # Proceed with query processing...
""")


if __name__ == "__main__":
    asyncio.run(example_auth_flow())
