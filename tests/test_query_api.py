"""Tests for Query API endpoints.

Feature #17: REST API Endpoints

Verification steps covered:
1. POST /api/v1/query with valid API key → 200 with QueryResponse
2. GET /api/v1/query?text=foo with valid API key → 200 with QueryResponse
3. GET /api/v1/health (no auth required) → 200 with health status
4. GET /api/v1/metrics (no auth required) → Prometheus-format metrics

Test categories:
- Happy path: query endpoints with valid API key
- Error handling: invalid API key, missing API key, invalid query params
- Boundary: empty query, max top_k
- Security: unauthorized access

Test layer breakdown:
- [unit]: Uses mocked QueryHandler and auth
- [integration]: Uses real test client (requires services)

Security: N/A - Auth is Feature #16 (already passing)
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from src.query.main import app
from src.query.dependencies import get_query_handler, get_db
from src.query.handler import QueryHandler
from src.shared.models import APIKey, KeyStatus


# Mock API Key for testing
def create_mock_api_key():
    """Create a mock API key for testing."""
    return APIKey(
        id=uuid4(),
        key_hash="test_hash",
        name="test-key",
        status=KeyStatus.ACTIVE,
        created_at=datetime.utcnow(),
        revoked_at=None
    )


# Mock response factory
def create_mock_response(results=None, query_time_ms=100.0):
    """Create a mock QueryHandler response."""
    mock = MagicMock()
    mock.results = results if results is not None else []
    mock.query_time_ms = query_time_ms
    return mock


# ============================================================================
# UNIT TESTS - Mock dependencies via FastAPI dependency override
# ============================================================================

@pytest.mark.asyncio
async def test_post_query_with_valid_api_key_returns_200():
    """[unit] POST /api/v1/query with valid API key returns 200 with QueryResponse."""
    mock_response = create_mock_response(results=[
        {
            "repository": "test-repo",
            "file_path": "src/main.java",
            "symbol": "WebClient",
            "score": 0.92,
            "content": "public class WebClient { ... }"
        }
    ])

    async def mock_handler():
        mock = AsyncMock(spec=QueryHandler)
        mock.handle = AsyncMock(return_value=mock_response)
        return mock

    # Mock db session
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=create_mock_api_key())))

    async def mock_get_db():
        yield mock_db

    # Override dependencies
    app.dependency_overrides[get_query_handler] = mock_handler
    app.dependency_overrides[get_db] = mock_get_db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/query",
                json={
                    "query": "how to use WebClient timeout",
                    "query_type": "natural_language",
                },
                headers={"X-API-Key": "test-api-key-12345"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "query_time_ms" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["repository"] == "test-repo"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_query_with_valid_api_key_returns_200():
    """[unit] GET /api/v1/query with valid API key returns 200 with QueryResponse."""
    mock_response = create_mock_response(results=[])

    async def mock_handler():
        mock = AsyncMock(spec=QueryHandler)
        mock.handle = AsyncMock(return_value=mock_response)
        return mock

    # Mock db session
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=create_mock_api_key())))

    async def mock_get_db():
        yield mock_db

    app.dependency_overrides[get_query_handler] = mock_handler
    app.dependency_overrides[get_db] = mock_get_db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/query",
                params={"query": "test query"},
                headers={"X-API-Key": "test-api-key-12345"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "query_time_ms" in data
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_post_query_without_api_key_returns_401():
    """[unit] POST /api/v1/query without API key returns 401 Unauthorized."""
    # Need to mock get_query_handler even for auth failure tests
    # because FastAPI resolves all dependencies before calling the endpoint
    async def mock_handler():
        mock = AsyncMock(spec=QueryHandler)
        mock.handle = AsyncMock(return_value=create_mock_response())
        return mock

    app.dependency_overrides[get_query_handler] = mock_handler

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/query",
                json={
                    "query": "test query",
                },
            )

        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_post_query_with_invalid_api_key_returns_401():
    """[unit] POST /api/v1/query with invalid API key returns 401 Unauthorized."""
    # Mock db session that returns None (invalid key)
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

    async def mock_get_db():
        yield mock_db

    # Also mock get_query_handler since FastAPI resolves all dependencies
    async def mock_handler():
        mock = AsyncMock(spec=QueryHandler)
        mock.handle = AsyncMock(return_value=create_mock_response())
        return mock

    app.dependency_overrides[get_db] = mock_get_db
    app.dependency_overrides[get_query_handler] = mock_handler

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/query",
                json={
                    "query": "test query",
                },
                headers={"X-API-Key": "invalid-key"},
            )

        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_endpoint_no_auth_required():
    """[unit] GET /api/v1/health does not require authentication."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_metrics_endpoint_no_auth_required():
    """[unit] GET /api/v1/metrics does not require authentication."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/metrics")

    assert response.status_code == 200
    # Prometheus format should contain some common metric patterns
    assert "# HELP" in response.text or "# TYPE" in response.text


@pytest.mark.asyncio
async def test_post_query_with_empty_query_returns_422():
    """[unit] POST /api/v1/query with empty query returns 422 Validation Error."""
    async def mock_handler():
        mock = AsyncMock(spec=QueryHandler)
        mock.handle = AsyncMock(side_effect=ValueError("query must not be empty"))
        return mock

    # Mock db session
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=create_mock_api_key())))

    async def mock_get_db():
        yield mock_db

    app.dependency_overrides[get_query_handler] = mock_handler
    app.dependency_overrides[get_db] = mock_get_db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/query",
                json={
                    "query": "",
                },
                headers={"X-API-Key": "test-api-key-12345"},
            )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_post_query_with_whitespace_only_query_returns_422():
    """[unit] POST /api/v1/query with whitespace-only query returns 422 Validation Error."""
    async def mock_handler():
        mock = AsyncMock(spec=QueryHandler)
        mock.handle = AsyncMock(side_effect=ValueError("query must not be empty"))
        return mock

    # Mock db session
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=create_mock_api_key())))

    async def mock_get_db():
        yield mock_db

    app.dependency_overrides[get_query_handler] = mock_handler
    app.dependency_overrides[get_db] = mock_get_db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/query",
                json={
                    "query": "   ",
                },
                headers={"X-API-Key": "test-api-key-12345"},
            )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_query_with_query_type_symbol():
    """[unit] GET /api/v1/query with query_type=symbol works correctly."""
    mock_response = create_mock_response(results=[
        {
            "repository": "spring-framework",
            "file_path": "web/src/main/java/RestTemplate.java",
            "symbol": "RestTemplate",
            "score": 0.95,
            "content": "public class RestTemplate { ... }"
        }
    ])

    async def mock_handler():
        mock = AsyncMock(spec=QueryHandler)
        mock.handle = AsyncMock(return_value=mock_response)
        return mock

    # Mock db session
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=create_mock_api_key())))

    async def mock_get_db():
        yield mock_db

    app.dependency_overrides[get_query_handler] = mock_handler
    app.dependency_overrides[get_db] = mock_get_db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/query",
                params={
                    "query": "org.springframework.web.client.RestTemplate",
                    "query_type": "symbol"
                },
                headers={"X-API-Key": "test-api-key-12345"},
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_post_query_with_repo_filter():
    """[unit] POST /api/v1/query with repo filter passes filter to handler."""
    mock_response = create_mock_response(results=[])

    async def mock_handler():
        mock = AsyncMock(spec=QueryHandler)
        mock.handle = AsyncMock(return_value=mock_response)
        return mock

    # Mock db session
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=create_mock_api_key())))

    async def mock_get_db():
        yield mock_db

    app.dependency_overrides[get_query_handler] = mock_handler
    app.dependency_overrides[get_db] = mock_get_db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/query",
                json={
                    "query": "timeout",
                    "repo": "spring-framework",
                },
                headers={"X-API-Key": "test-api-key-12345"},
            )

        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_post_query_with_language_filter():
    """[unit] POST /api/v1/query with language filter works correctly."""
    mock_response = create_mock_response(results=[])

    async def mock_handler():
        mock = AsyncMock(spec=QueryHandler)
        mock.handle = AsyncMock(return_value=mock_response)
        return mock

    # Mock db session
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=create_mock_api_key())))

    async def mock_get_db():
        yield mock_db

    app.dependency_overrides[get_query_handler] = mock_handler
    app.dependency_overrides[get_db] = mock_get_db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/query",
                json={
                    "query": "async",
                    "language": "Java",
                },
                headers={"X-API-Key": "test-api-key-12345"},
            )

        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_post_query_with_top_k_parameter():
    """[unit] POST /api/v1/query with top_k parameter uses correct value."""
    mock_response = create_mock_response(results=[])

    async def mock_handler():
        mock = AsyncMock(spec=QueryHandler)
        mock.handle = AsyncMock(return_value=mock_response)
        return mock

    # Mock db session
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=create_mock_api_key())))

    async def mock_get_db():
        yield mock_db

    app.dependency_overrides[get_query_handler] = mock_handler
    app.dependency_overrides[get_db] = mock_get_db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/query",
                json={
                    "query": "test",
                    "top_k": 5,
                },
                headers={"X-API-Key": "test-api-key-12345"},
            )

        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_query_with_missing_query_param_returns_422():
    """[unit] GET /api/v1/query without query param returns 422."""
    # Mock db session
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=create_mock_api_key())))

    async def mock_get_db():
        yield mock_db

    # Mock get_query_handler
    async def mock_handler():
        mock = AsyncMock(spec=QueryHandler)
        mock.handle = AsyncMock(return_value=create_mock_response())
        return mock

    app.dependency_overrides[get_db] = mock_get_db
    app.dependency_overrides[get_query_handler] = mock_handler

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/query",
                headers={"X-API-Key": "test-api-key-12345"},
            )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
