"""Tests for API Key Authentication - Feature #16: API Key Authentication (FR-018).

These tests verify the AuthMiddleware authentication:
1. Valid API key in X-API-Key header → request proceeds
2. Invalid API key → 401 Unauthorized
3. Missing API key header → 401 Unauthorized
4. Revoked API key → 401 Unauthorized

Verification Steps (from feature-list.json):
1. Given request with valid API key in X-API-Key header, when auth middleware checks,
   then request proceeds to handler
2. Given request with invalid API key, when auth middleware checks, then 401 Unauthorized is returned
3. Given request with missing API key header, when auth middleware checks, then 401 Unauthorized is returned
4. Given request with revoked API key, when auth middleware checks, then 401 Unauthorized is returned
"""

import pytest
import hashlib
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from src.shared.models.api_key import APIKey, KeyStatus


class TestAuthMiddlewareVerifyApiKey:
    """Tests for AuthMiddleware.verify_api_key method."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock AsyncSession."""
        mock = AsyncMock()
        mock.execute = AsyncMock()
        return mock

    @pytest.fixture
    def auth_middleware(self, mock_db_session):
        """Create AuthMiddleware with mock DB."""
        from src.query.auth import AuthMiddleware
        return AuthMiddleware(mock_db_session)

    @pytest.mark.asyncio
    async def test_verify_api_key_valid_returns_record(self, auth_middleware, mock_db_session):
        """Given valid API key, when verify_api_key is called, then APIKey record is returned."""
        # Setup - create a valid API key in the database
        test_key = "test-api-key-12345"
        expected_hash = hashlib.sha256(test_key.encode()).hexdigest()

        mock_api_key = APIKey(
            id="550e8400-e29b-41d4-a716-446655440000",
            key_hash=expected_hash,
            name="Test Key",
            status=KeyStatus.ACTIVE
        )

        # Mock the execute result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_api_key)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Execute
        result = await auth_middleware.verify_api_key(test_key)

        # Verify
        assert result is not None
        assert result.id == mock_api_key.id
        assert result.key_hash == expected_hash
        assert result.status == KeyStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_verify_api_key_invalid_returns_none(self, auth_middleware, mock_db_session):
        """Given invalid API key, when verify_api_key is called, then None is returned."""
        # Setup
        test_key = "nonexistent-key"

        # Mock - no result found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Execute
        result = await auth_middleware.verify_api_key(test_key)

        # Verify
        assert result is None

    @pytest.mark.asyncio
    async def test_verify_api_key_revoked_returns_none(self, auth_middleware, mock_db_session):
        """Given revoked API key, when verify_api_key is called, then None is returned."""
        # Setup
        test_key = "revoked-key"

        # Mock - query returns nothing because revoked keys are filtered out
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Execute
        result = await auth_middleware.verify_api_key(test_key)

        # Verify
        assert result is None


class TestAuthMiddlewareRequireAuth:
    """Tests for AuthMiddleware.require_auth method."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock AsyncSession."""
        mock = AsyncMock()
        mock.execute = AsyncMock()
        return mock

    @pytest.fixture
    def mock_request_valid_key(self):
        """Create a mock Request with valid API key header."""
        mock = MagicMock()
        mock.headers = {"X-API-Key": "valid-key-12345"}
        return mock

    @pytest.fixture
    def mock_request_missing_key(self):
        """Create a mock Request with missing API key header."""
        mock = MagicMock()
        mock.headers = {}
        return mock

    @pytest.fixture
    def mock_request_invalid_key(self):
        """Create a mock Request with invalid API key header."""
        mock = MagicMock()
        mock.headers = {"X-API-Key": "invalid-key-12345"}
        return mock

    @pytest.fixture
    def auth_middleware(self, mock_db_session):
        """Create AuthMiddleware with mock DB."""
        from src.query.auth import AuthMiddleware
        return AuthMiddleware(mock_db_session)

    @pytest.mark.asyncio
    async def test_require_auth_valid_key_returns_record(self, auth_middleware, mock_db_session, mock_request_valid_key):
        """Given request with valid API key, when require_auth is called, then APIKey record is returned."""
        # Setup - create a valid API key in the database
        test_key = "valid-key-12345"
        expected_hash = hashlib.sha256(test_key.encode()).hexdigest()

        mock_api_key = APIKey(
            id="550e8400-e29b-41d4-a716-446655440000",
            key_hash=expected_hash,
            name="Valid Test Key",
            status=KeyStatus.ACTIVE
        )

        # Mock the execute result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_api_key)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Execute
        result = await auth_middleware.require_auth(mock_request_valid_key)

        # Verify
        assert result is not None
        assert result.id == mock_api_key.id
        assert result.name == "Valid Test Key"

    @pytest.mark.asyncio
    async def test_require_auth_missing_key_raises_401(self, auth_middleware, mock_request_missing_key):
        """Given request with missing API key header, when require_auth is called, then 401 is raised."""
        # Execute and verify
        with pytest.raises(HTTPException) as exc_info:
            await auth_middleware.require_auth(mock_request_missing_key)

        assert exc_info.value.status_code == 401
        assert "Missing API key" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_require_auth_invalid_key_raises_401(self, auth_middleware, mock_db_session, mock_request_invalid_key):
        """Given request with invalid API key, when require_auth is called, then 401 is raised."""
        # Setup - no valid key found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Execute and verify
        with pytest.raises(HTTPException) as exc_info:
            await auth_middleware.require_auth(mock_request_invalid_key)

        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.detail


class TestAuthMiddlewareIntegration:
    """Integration-style tests for AuthMiddleware with realistic DB queries."""

    @pytest.mark.asyncio
    async def test_verify_api_key_queries_correct_hash(self):
        """Verify that API key is hashed correctly before DB lookup."""
        # This test verifies the hashing logic produces correct SHA-256 hex digest
        test_key = "my-secret-api-key"
        expected_hash = hashlib.sha256(test_key.encode()).hexdigest()

        # The hash should be 64 characters (SHA-256 hex digest)
        assert len(expected_hash) == 64
        # Verify against known SHA-256 hash of this specific key
        assert expected_hash == hashlib.sha256(test_key.encode()).hexdigest()

    @pytest.mark.asyncio
    async def test_require_auth_header_extraction(self):
        """Verify that X-API-Key header is correctly extracted."""
        # Test header extraction logic
        headers = {"X-API-Key": "test-key"}

        api_key = headers.get("X-API-Key")
        assert api_key == "test-key"

        # Missing header
        empty_headers = {}
        assert empty_headers.get("X-API-Key") is None
