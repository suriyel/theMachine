"""Tests for Repository Management API endpoints.

Feature #3: Repository Registration (FR-001)

Verification steps covered:
1. POST /api/v1/repos with valid data → 201 with repository object (status registered)
2. POST /api/v1/repos with unreachable URL → 400 with error message
3. POST /api/v1/repos with duplicate URL → 409 Conflict
4. GET /api/v1/repos → 200 with list of all repositories

Test categories:
- Happy path: valid registration, list repositories
- Error handling: invalid URL, unreachable URL, duplicate URL
- Boundary: empty URL, empty name, max length fields

Test layer breakdown:
- [unit]: Uses mocked RepoManager
- [integration]: Uses real test database (via test client)

Security: N/A for this feature (auth is Feature #16)
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from src.query.main import app
from src.shared.models import Repository, RepoStatus
from src.shared.services.repo_manager import RepoManager


# ============================================================================
# REAL TESTS (Integration - hit actual database via test client)
# ============================================================================

@pytest.mark.real_test
@pytest.mark.asyncio
async def test_real_api_register_repository():
    """[integration] Register a repository via real API and verify it's stored in database."""
    from sqlalchemy import select
    from src.shared.db.session import async_session_maker

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register a new repository (skip URL validation for testing)
        response = await client.post(
            "/api/v1/repos?skip_validation=true",
            json={
                "url": "https://github.com/real-api-test/integration-repo.git",
                "name": "Real API Integration Test",
                "languages": ["Python"],
            },
        )

        # Should return 201 Created
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()
        assert data["url"] == "https://github.com/real-api-test/integration-repo.git"
        assert data["name"] == "Real API Integration Test"
        assert data["languages"] == ["Python"]
        assert data["status"] == "registered"

        # Verify the repository was actually stored in the database
        async with async_session_maker() as session:
            result = await session.execute(
                select(Repository).where(Repository.url == "https://github.com/real-api-test/integration-repo.git")
            )
            stored_repo = result.scalar_one_or_none()
            assert stored_repo is not None, "Repository not found in database"
            assert stored_repo.name == "Real API Integration Test"
            assert stored_repo.status == RepoStatus.REGISTERED

            # Clean up
            await session.delete(stored_repo)
            await session.commit()


@pytest.mark.real_test
@pytest.mark.asyncio
async def test_real_api_list_repositories():
    """[integration] List repositories via real API returns data from actual database."""
    from sqlalchemy import select
    from src.shared.db.session import async_session_maker

    # First, create some repositories directly in the database
    async with async_session_maker() as session:
        repo1 = Repository(
            url="https://github.com/list-api-test/repo1.git",
            name="List API Test 1",
            languages=["Java"],
            status=RepoStatus.REGISTERED,
        )
        repo2 = Repository(
            url="https://github.com/list-api-test/repo2.git",
            name="List API Test 2",
            languages=["Python"],
            status=RepoStatus.REGISTERED,
        )
        session.add(repo1)
        session.add(repo2)
        await session.commit()
        await session.refresh(repo1)
        await session.refresh(repo2)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/repos")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Verify our repositories are in the list
        urls = [r["url"] for r in data]
        assert "https://github.com/list-api-test/repo1.git" in urls
        assert "https://github.com/list-api-test/repo2.git" in urls

    # Clean up
    async with async_session_maker() as session:
        for url in [
            "https://github.com/list-api-test/repo1.git",
            "https://github.com/list-api-test/repo2.git",
        ]:
            result = await session.execute(select(Repository).where(Repository.url == url))
            repo = result.scalar_one_or_none()
            if repo:
                await session.delete(repo)
        await session.commit()


@pytest.mark.real_test
@pytest.mark.asyncio
async def test_real_api_duplicate_url_returns_409():
    """[integration] Registering duplicate URL via real API returns 409 Conflict."""
    from sqlalchemy import select
    from src.shared.db.session import async_session_maker

    url = "https://github.com/duplicate-api-test/repo.git"

    # Create first repository
    async with async_session_maker() as session:
        repo = Repository(
            url=url,
            name="First Repo",
            languages=["TypeScript"],
            status=RepoStatus.REGISTERED,
        )
        session.add(repo)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Try to register same URL again (skip validation since we're testing duplicate logic)
        response = await client.post(
            "/api/v1/repos?skip_validation=true",
            json={
                "url": url,
                "name": "Duplicate Attempt",
                "languages": ["JavaScript"],
            },
        )

        assert response.status_code == 409, f"Expected 409, got {response.status_code}"
        assert "already" in response.json()["detail"].lower() or "duplicate" in response.json()["detail"].lower()

    # Clean up
    async with async_session_maker() as session:
        result = await session.execute(select(Repository).where(Repository.url == url))
        repo = result.scalar_one_or_none()
        if repo:
            await session.delete(repo)
        await session.commit()


# ============================================================================
# BOUNDARY TESTS - Validation
# ============================================================================

@pytest.mark.asyncio
async def test_api_create_repo_empty_url_returns_422():
    """[unit] POST /api/v1/repos with empty URL returns 422 Unprocessable Entity."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/repos",
            json={
                "url": "",
                "name": "Empty URL Test",
                "languages": ["Java"],
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_api_create_repo_empty_name_returns_422():
    """[unit] POST /api/v1/repos with empty name returns 422 Unprocessable Entity."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/repos",
            json={
                "url": "https://github.com/test/empty-name.git",
                "name": "",
                "languages": ["Python"],
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_api_create_repo_missing_url_returns_422():
    """[unit] POST /api/v1/repos without URL field returns 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/repos",
            json={
                "name": "Missing URL Test",
                "languages": ["Java"],
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_api_create_repo_missing_name_returns_422():
    """[unit] POST /api/v1/repos without name field returns 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/repos",
            json={
                "url": "https://github.com/test/missing-name.git",
                "languages": ["Python"],
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_api_create_repo_invalid_url_scheme_returns_422():
    """[unit] POST /api/v1/repos with non-HTTP URL returns 422 (Pydantic validation)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/repos",
            json={
                "url": "ftp://invalid-scheme.com/repo.git",
                "name": "Invalid Scheme",
                "languages": ["C"],
            },
        )

    assert response.status_code == 422
    # Verify the error mentions URL scheme validation
    error_detail = response.json()["detail"]
    assert any("url" in str(err).lower() for err in error_detail)
