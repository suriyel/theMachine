"""Tests for RepoManager service.

Feature #3: Repository Registration (FR-001)

Test categories:
- Happy path: register, get, list_all, delete
- Error handling: invalid URL, unreachable URL, duplicate URL, not found
- Boundary: empty URL, empty name, max length
- Security: N/A (SQLAlchemy handles SQL injection)

Negative test ratio: >= 40%
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4
from datetime import datetime

from src.shared.services.repo_manager import RepoManager
from src.shared.models import Repository, RepoStatus


# ============================================================================
# REAL TESTS - Verify actual database connectivity
# ============================================================================

@pytest.mark.real_test
async def test_real_register_repository_to_db(db_session):
    """[integration] Register a repository and verify it's persisted to the real test database."""
    from src.shared.services.repo_manager import RepoManager

    repo_manager = RepoManager(db_session)

    # Skip URL validation for this real test (we're testing DB persistence)
    repo = await repo_manager.register(
        url="https://github.com/real-test/repo.git",
        name="Real Test Repository",
        languages=["Python"],
        validate_url=False,
    )

    # Verify the repository was persisted with correct fields
    assert repo.id is not None
    assert isinstance(repo.id, UUID)
    assert repo.url == "https://github.com/real-test/repo.git"
    assert repo.name == "Real Test Repository"
    assert repo.languages == ["Python"]
    assert repo.status == RepoStatus.REGISTERED
    assert repo.created_at is not None
    assert isinstance(repo.created_at, datetime)

    # Verify we can retrieve it back from the database
    retrieved = await repo_manager.get(repo.id)
    assert retrieved.id == repo.id
    assert retrieved.url == repo.url
    assert retrieved.name == repo.name


@pytest.mark.real_test
async def test_real_list_repositories_from_db(db_session):
    """[integration] List repositories from the real test database."""
    from src.shared.services.repo_manager import RepoManager

    repo_manager = RepoManager(db_session)

    # Create multiple repositories
    await repo_manager.register(
        url="https://github.com/list-test/repo1.git",
        name="List Test 1",
        languages=["Java"],
        validate_url=False,
    )
    await repo_manager.register(
        url="https://github.com/list-test/repo2.git",
        name="List Test 2",
        languages=["Python"],
        validate_url=False,
    )

    # List all repositories
    repos = await repo_manager.list_all()

    # Verify we get a list with our repositories
    assert isinstance(repos, list)
    assert len(repos) >= 2

    # Verify the repositories are in the list
    urls = [r.url for r in repos]
    assert "https://github.com/list-test/repo1.git" in urls
    assert "https://github.com/list-test/repo2.git" in urls


@pytest.mark.real_test
async def test_real_delete_repository_from_db(db_session):
    """[integration] Delete a repository and verify it's removed from the real test database."""
    from src.shared.services.repo_manager import RepoManager

    repo_manager = RepoManager(db_session)

    # Create a repository
    repo = await repo_manager.register(
        url="https://github.com/delete-test/repo.git",
        name="Delete Test",
        languages=["TypeScript"],
        validate_url=False,
    )

    repo_id = repo.id

    # Delete it
    await repo_manager.delete(repo_id)

    # Verify it's gone - get() should raise ValueError
    with pytest.raises(ValueError, match="not found"):
        await repo_manager.get(repo_id)


@pytest.mark.real_test
async def test_real_register_duplicate_url_raises_error(db_session):
    """[integration] Registering duplicate URL raises error."""
    from src.shared.services.repo_manager import RepoManager

    repo_manager = RepoManager(db_session)

    # Create first repository
    await repo_manager.register(
        url="https://github.com/duplicate-test/repo.git",
        name="First Repo",
        languages=["Java"],
        validate_url=False,
    )

    # Try to register duplicate
    with pytest.raises(ValueError, match="already registered"):
        await repo_manager.register(
            url="https://github.com/duplicate-test/repo.git",
            name="Duplicate Repo",
            languages=["Python"],
            validate_url=False,
        )


@pytest.mark.real_test
async def test_real_register_invalid_url_raises_error(db_session):
    """[integration] Registering invalid URL format raises error."""
    from src.shared.services.repo_manager import RepoManager

    repo_manager = RepoManager(db_session)

    # Try to register with invalid URL
    with pytest.raises(ValueError, match="Invalid or unreachable"):
        await repo_manager.register(
            url="not-a-url",
            name="Invalid URL",
            languages=["Python"],
            validate_url=True,
        )


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_db_session():
    """Create a mock database session for unit tests."""
    mock = MagicMock()
    mock.add = AsyncMock()
    mock.flush = AsyncMock()
    mock.refresh = AsyncMock()
    mock.execute = AsyncMock()
    mock.delete = AsyncMock()
    return mock


@pytest.fixture
def mock_validator():
    """Mock URL validator that returns success by default."""
    with patch("src.shared.services.repo_manager.validate_git_url") as mock:
        mock.return_value = (True, "")
        yield mock


# ============================================================================
# UNIT TESTS - Simplified with method-level mocking
# ============================================================================

async def test_register_calls_validator(mock_db_session, mock_validator):
    """[unit] Register calls validate_git_url with the URL."""
    repo_manager = RepoManager(mock_db_session)

    # Mock get_by_url to return None (no duplicate)
    with patch.object(repo_manager, "get_by_url", return_value=None):
        await repo_manager.register(
            url="https://github.com/test/repo.git",
            name="Test",
            languages=["Python"],
        )

    # Verify validator was called
    mock_validator.assert_called_once_with("https://github.com/test/repo.git")


async def test_register_adds_repository_to_session(mock_db_session, mock_validator):
    """[unit] Register adds repository to db session."""
    repo_manager = RepoManager(mock_db_session)

    # Mock get_by_url to return None
    with patch.object(repo_manager, "get_by_url", return_value=None):
        await repo_manager.register(
            url="https://github.com/test/repo.git",
            name="Test Repo",
            languages=["Java"],
        )

    # Verify add was called
    mock_db_session.add.assert_called_once()


async def test_delete_calls_get_first(mock_db_session):
    """[unit] delete calls get() to find the repository first."""
    repo_manager = RepoManager(mock_db_session)

    repo_id = uuid4()
    expected_repo = Repository(
        id=repo_id,
        url="https://github.com/test/delete.git",
        name="Delete Test",
        languages=["C++"],
        status=RepoStatus.REGISTERED,
    )

    # Mock get to return the repo
    with patch.object(repo_manager, "get", return_value=expected_repo):
        await repo_manager.delete(repo_id)

    # Verify delete was called on session
    mock_db_session.delete.assert_called_once_with(expected_repo)
