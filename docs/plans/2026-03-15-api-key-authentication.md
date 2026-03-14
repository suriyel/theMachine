# Feature #16 Implementation Plan — API Key Authentication (FR-018)

**Date**: 2026-03-15
**Feature**: API Key Authentication (FR-018)
**Status**: Implementation Plan

## Overview

Implement authentication middleware that verifies API keys before processing queries. The AuthMiddleware class will:
1. Verify API key hash exists in PostgreSQL
2. Check key status is ACTIVE (not REVOKED)
3. Return 401 Unauthorized for invalid/missing/revoked keys

## Dependencies

- Feature #2: Data Model and Migrations (APIKey model exists)
- Uses: PostgreSQL via AsyncSession

## Implementation Details

### 1. AuthMiddleware Class

**File**: `src/query/auth.py`

```python
class AuthMiddleware:
    """Middleware for API key authentication."""

    def __init__(self, db_session: AsyncSession):
        self._db = db_session

    async def verify_api_key(self, key: str) -> APIKey | None:
        """Verify API key exists and is active.

        Args:
            key: Plaintext API key from request header

        Returns:
            APIKey record if valid, None otherwise
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
```

### 2. Dependencies

- `src/shared/models/api_key.py`: Already exists with APIKey model
- `src/shared/db/session.py`: Already exists with get_db session
- Need `hashlib` (stdlib)

### 3. Configuration

No new configs needed - uses existing DATABASE_URL.

## Verification Steps Coverage

| Step | Implementation |
|------|----------------|
| Valid API key in X-API-Key header → proceed | `require_auth()` returns APIKey record |
| Invalid API key → 401 | `verify_api_key()` returns None → HTTPException(401) |
| Missing API key header → 401 | `require_auth()` checks header exists → HTTPException(401) |
| Revoked API key → 401 | Query filters by `status == KeyStatus.ACTIVE` |

## Test Strategy

1. **Unit tests for AuthMiddleware**:
   - `test_verify_api_key_valid` - valid key returns APIKey
   - `test_verify_api_key_invalid` - invalid key returns None
   - `test_verify_api_key_revoked` - revoked key returns None
   - `test_require_auth_valid` - valid key returns record
   - `test_require_auth_missing` - missing header raises 401
   - `test_require_auth_invalid` - invalid key raises 401

2. **Coverage**: Target 90%+ line coverage

## File List

- `src/query/auth.py` (new) - AuthMiddleware class
- `tests/test_auth.py` (new) - Unit tests
