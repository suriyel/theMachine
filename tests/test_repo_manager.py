"""Tests for Feature #3: Repository Registration — RepoManager service.

Test categories covered:
- Happy path: valid URL registration, normalization, SSH URL, IndexJob creation
- Error handling: invalid URL, empty URL, unsupported scheme, duplicate registration
- Boundary: no path, no host, whitespace-padded URL
- Security: N/A — URL validation is the security boundary; covered by error tests

Negative tests: T4, T5, T6, T7, T8, T10 = 6/12 = 50% >= 40%
"""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


# --- Fixtures ---


@pytest.fixture
async def async_engine():
    """Create an in-memory SQLite async engine for testing."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    yield engine
    await engine.dispose()


@pytest.fixture
async def tables(async_engine):
    """Create all tables from Base metadata."""
    from src.shared.models.base import Base

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def async_session(async_engine, tables):
    """Create an async session for testing."""
    async_session_factory = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_factory() as session:
        yield session


@pytest.fixture
def repo_manager(async_session):
    """Create a RepoManager with the test session."""
    from src.shared.services.repo_manager import RepoManager

    return RepoManager(session=async_session)


# --- T1: Happy path — register valid URL ---


# [unit] T1: register a valid GitHub URL, verify repo and IndexJob created
async def test_register_valid_url(repo_manager, async_session):
    """VS-1: Given a valid Git URL, register creates Repository with status=pending."""
    from src.shared.models import IndexJob, Repository

    repo = await repo_manager.register("https://github.com/pallets/flask")

    assert isinstance(repo.id, uuid.UUID), "repo.id must be a UUID"
    assert repo.name == "pallets/flask"
    assert repo.url == "https://github.com/pallets/flask"
    assert repo.status == "pending"

    # Verify IndexJob was also created
    result = await async_session.execute(
        select(IndexJob).where(IndexJob.repo_id == repo.id)
    )
    job = result.scalar_one()
    assert job.status == "pending"
    assert job.branch == "main"
    assert job.repo_id == repo.id


# --- T2: Happy path — strip .git suffix ---


# [unit] T2: URL with .git suffix is normalized
async def test_register_strips_git_suffix(repo_manager):
    """VS-1: URL normalization strips trailing .git."""
    repo = await repo_manager.register("https://github.com/owner/repo.git")

    assert repo.url == "https://github.com/owner/repo"
    assert repo.name == "owner/repo"


# --- T3: Happy path — normalize case and trailing slash ---


# [unit] T3: mixed case host and trailing slash are normalized
async def test_register_normalizes_case_and_trailing_slash(repo_manager):
    """VS-1: Host is lowercased, trailing slash stripped."""
    repo = await repo_manager.register("https://GitHub.COM/Owner/Repo/")

    assert repo.url == "https://github.com/Owner/Repo"
    # Path segments preserve case (owner/repo names are case-sensitive on some hosts)
    assert repo.name == "Owner/Repo"


# --- T4: Error — invalid URL ---


# [unit] T4: completely invalid URL raises ValidationError
async def test_register_invalid_url_raises_validation_error(repo_manager):
    """VS-2: Invalid URL raises ValidationError, no record created."""
    from src.shared.exceptions import ValidationError

    with pytest.raises(ValidationError):
        await repo_manager.register("not-a-url")


# --- T5: Error — empty URL ---


# [unit] T5: empty string raises ValidationError
async def test_register_empty_url_raises_validation_error(repo_manager):
    """VS-2: Empty URL raises ValidationError."""
    from src.shared.exceptions import ValidationError

    with pytest.raises(ValidationError, match="URL must not be empty"):
        await repo_manager.register("")


# --- T6: Error — unsupported scheme ---


# [unit] T6: ftp:// scheme raises ValidationError
async def test_register_unsupported_scheme_raises_validation_error(repo_manager):
    """VS-2: Unsupported URL scheme raises ValidationError."""
    from src.shared.exceptions import ValidationError

    with pytest.raises(ValidationError, match="[Uu]nsupported"):
        await repo_manager.register("ftp://example.com/repo")


# --- T7: Error — duplicate registration ---


# [unit] T7: registering same URL twice raises ConflictError
async def test_register_duplicate_url_raises_conflict_error(repo_manager):
    """VS-3: Duplicate URL raises ConflictError."""
    from src.shared.exceptions import ConflictError

    await repo_manager.register("https://github.com/pallets/flask")

    with pytest.raises(ConflictError, match="already registered"):
        await repo_manager.register("https://github.com/pallets/flask")


# --- T8: Boundary — no path in URL ---


# [unit] T8: URL with no repository path raises ValidationError
async def test_register_no_path_raises_validation_error(repo_manager):
    """Boundary: URL with no path beyond host raises ValidationError."""
    from src.shared.exceptions import ValidationError

    with pytest.raises(ValidationError, match="no repository path"):
        await repo_manager.register("http://github.com")


# --- T9: Boundary — whitespace padded URL ---


# [unit] T9: leading/trailing whitespace is stripped, registration succeeds
async def test_register_whitespace_stripped(repo_manager):
    """Boundary: Whitespace around URL is stripped."""
    repo = await repo_manager.register("   https://github.com/a/b   ")

    assert repo.url == "https://github.com/a/b"
    assert repo.name == "a/b"


# --- T10: Boundary — no host in URL ---


# [unit] T10: URL with no host raises ValidationError
async def test_register_no_host_raises_validation_error(repo_manager):
    """Boundary: URL with no host raises ValidationError."""
    from src.shared.exceptions import ValidationError

    with pytest.raises(ValidationError, match="no host"):
        await repo_manager.register("http://")


# --- T11: Happy path — SSH shorthand URL ---


# [unit] T11: git@github.com:owner/repo.git is supported
async def test_register_ssh_url(repo_manager):
    """VS-1: SSH shorthand URL is accepted and normalized."""
    repo = await repo_manager.register("git@github.com:owner/repo.git")

    assert "github.com" in repo.url
    assert "owner/repo" in repo.url
    assert repo.name == "owner/repo"
    assert repo.status == "pending"
    # .git suffix should be stripped
    assert not repo.url.endswith(".git")


# --- T12: State — status is pending after register ---


# [unit] T12: verify status field is exactly "pending"
async def test_register_status_is_pending(repo_manager):
    """State: Repository status is 'pending' immediately after registration."""
    repo = await repo_manager.register("https://gitlab.com/group/project")

    assert repo.status == "pending", f"Expected 'pending', got '{repo.status}'"


# --- T7b: Duplicate detection with normalization ---


# [unit] T7b: duplicate detected even with cosmetic URL differences
async def test_register_duplicate_with_normalization(repo_manager):
    """VS-3: Duplicate detection works across normalized forms."""
    from src.shared.exceptions import ConflictError

    await repo_manager.register("https://github.com/pallets/flask.git")

    # Same repo without .git suffix — should be detected as duplicate
    with pytest.raises(ConflictError, match="already registered"):
        await repo_manager.register("https://github.com/pallets/flask")


# --- Real test: database integration ---


# [integration] Real test: verify RepoManager persists to actual test database
@pytest.mark.real
async def test_real_register_persists_to_database(async_session):
    """Real test: RepoManager creates persistent records in the database."""
    from src.shared.models import IndexJob, Repository
    from src.shared.services.repo_manager import RepoManager

    manager = RepoManager(session=async_session)
    repo = await manager.register("https://github.com/psf/requests")

    # Verify repo is in the database via a fresh query
    result = await async_session.execute(
        select(Repository).where(Repository.id == repo.id)
    )
    persisted_repo = result.scalar_one()
    assert persisted_repo.url == "https://github.com/psf/requests"
    assert persisted_repo.name == "psf/requests"
    assert persisted_repo.status == "pending"

    # Verify IndexJob is also persisted
    result = await async_session.execute(
        select(IndexJob).where(IndexJob.repo_id == repo.id)
    )
    persisted_job = result.scalar_one()
    assert persisted_job.branch == "main"
    assert persisted_job.status == "pending"
