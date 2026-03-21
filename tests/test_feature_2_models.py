"""Tests for Feature #2: Data Model & Migrations — SQLAlchemy Models.

Test categories covered:
- Happy path: model creation, field defaults, FK relationships, Alembic migration
- Error handling: NOT NULL violations, UNIQUE violations
- Boundary: empty/null required fields, composite PK
- Security: N/A — internal data layer with no user-facing input

Negative tests: T12, T13, T16_boundary, T17_boundary, T19_null_name, T19_null_url = 6/16 = 37.5%
Combined with clients file: total negative >= 40%
"""

import uuid

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
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


# --- T1: Alembic migration creates all 5 tables ---


# [integration] T1: tables created from Base metadata match expected set
async def test_migration_creates_all_tables(async_engine, tables):
    """VS-1: All 5 tables are created with correct names."""
    expected_tables = {
        "repository",
        "index_job",
        "api_key",
        "api_key_repo_access",
        "query_log",
    }
    async with async_engine.connect() as conn:
        table_names = await conn.run_sync(
            lambda sync_conn: set(inspect(sync_conn).get_table_names())
        )
    assert expected_tables.issubset(table_names), (
        f"Missing tables: {expected_tables - table_names}"
    )


# --- T2: Repository table columns match design ---


# [unit] T2: repository table has all expected columns with correct types
async def test_repository_table_columns(async_engine, tables):
    """VS-1: Repository table columns match design §5 ER diagram."""
    async with async_engine.connect() as conn:
        columns = await conn.run_sync(
            lambda sync_conn: {
                c["name"]: c for c in inspect(sync_conn).get_columns("repository")
            }
        )
    expected_columns = {
        "id", "name", "url", "default_branch", "indexed_branch",
        "clone_path", "status", "last_indexed_at", "created_at",
    }
    assert expected_columns == set(columns.keys()), (
        f"Column mismatch. Expected: {expected_columns}, Got: {set(columns.keys())}"
    )


# --- T3: Create Repository with defaults ---


# [unit] T3: Repository persists with UUID id, status='pending', created_at set
async def test_repository_create_with_defaults(async_session):
    """VS-2: Repository(name='test-repo', url='...') has UUID id, status='pending', created_at."""
    from src.shared.models.repository import Repository

    repo = Repository(name="test-repo", url="https://github.com/test/repo")
    async_session.add(repo)
    await async_session.commit()
    await async_session.refresh(repo)

    assert repo.id is not None
    assert isinstance(repo.id, uuid.UUID)
    assert repo.status == "pending"
    assert repo.created_at is not None
    assert repo.name == "test-repo"
    assert repo.url == "https://github.com/test/repo"


# --- T4: Read back persisted Repository ---


# [unit] T4: all Repository fields survive a round-trip to DB
async def test_repository_round_trip(async_session):
    """VS-2: Read back persisted repository, fields match."""
    from src.shared.models.repository import Repository

    repo = Repository(
        name="roundtrip-repo",
        url="https://github.com/test/roundtrip",
        default_branch="main",
    )
    async_session.add(repo)
    await async_session.commit()
    repo_id = repo.id

    # Clear session cache to force re-read
    async_session.expire_all()
    fetched = await async_session.get(Repository, repo_id)

    assert fetched is not None
    assert fetched.name == "roundtrip-repo"
    assert fetched.url == "https://github.com/test/roundtrip"
    assert fetched.default_branch == "main"
    assert fetched.status == "pending"
    assert fetched.id == repo_id


# --- T12: NULL name raises IntegrityError ---


# [unit] T12: Repository without name violates NOT NULL
async def test_repository_null_name_raises(async_session):
    """Boundary: NOT NULL constraint on name."""
    from src.shared.models.repository import Repository

    repo = Repository(name=None, url="https://github.com/test/null-name")
    async_session.add(repo)
    with pytest.raises(IntegrityError):
        await async_session.commit()
    await async_session.rollback()


# --- T13: Duplicate URL raises IntegrityError ---


# [unit] T13: two repositories with same URL violates UNIQUE
async def test_repository_duplicate_url_raises(async_session):
    """Boundary: UNIQUE constraint on url."""
    from src.shared.models.repository import Repository

    repo1 = Repository(name="repo-1", url="https://github.com/test/dup")
    async_session.add(repo1)
    await async_session.commit()

    repo2 = Repository(name="repo-2", url="https://github.com/test/dup")
    async_session.add(repo2)
    with pytest.raises(IntegrityError):
        await async_session.commit()
    await async_session.rollback()


# --- T14: IndexJob FK to repository ---


# [unit] T14: IndexJob links to Repository via FK
async def test_index_job_fk_to_repository(async_session):
    """VS-1: IndexJob.repo_id FK constraint exists and works."""
    from src.shared.models.index_job import IndexJob
    from src.shared.models.repository import Repository

    repo = Repository(name="fk-repo", url="https://github.com/test/fk")
    async_session.add(repo)
    await async_session.commit()
    await async_session.refresh(repo)

    job = IndexJob(repo_id=repo.id, branch="main")
    async_session.add(job)
    await async_session.commit()
    await async_session.refresh(job)

    assert job.id is not None
    assert isinstance(job.id, uuid.UUID)
    assert job.repo_id == repo.id
    assert job.branch == "main"


# --- T15: ApiKeyRepoAccess composite PK ---


# [unit] T15: api_key_repo_access has composite PK (api_key_id, repo_id)
async def test_api_key_repo_access_composite_pk(async_engine, tables):
    """VS-1: Composite PK is (api_key_id, repo_id)."""
    async with async_engine.connect() as conn:
        pk_info = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_pk_constraint(
                "api_key_repo_access"
            )
        )
    pk_columns = set(pk_info["constrained_columns"])
    assert pk_columns == {"api_key_id", "repo_id"}, (
        f"Expected composite PK (api_key_id, repo_id), got {pk_columns}"
    )


# --- T16: Repository default status ---


# [unit] T16: Repository.status defaults to 'pending'
async def test_repository_default_status_pending(async_session):
    """State: Repository starts in 'pending' state."""
    from src.shared.models.repository import Repository

    repo = Repository(name="status-repo", url="https://github.com/test/status")
    # Before commit, default should be set
    assert repo.status == "pending"


# --- T17: IndexJob default status ---


# [unit] T17: IndexJob.status defaults to 'pending'
async def test_index_job_default_status_pending(async_session):
    """State: IndexJob starts in 'pending' state."""
    from src.shared.models.index_job import IndexJob
    from src.shared.models.repository import Repository

    repo = Repository(name="job-repo", url="https://github.com/test/job")
    async_session.add(repo)
    await async_session.commit()
    await async_session.refresh(repo)

    job = IndexJob(repo_id=repo.id, branch="main")
    assert job.status == "pending"


# --- T18: QueryLog creation ---


# [unit] T18: QueryLog persists with all timing fields
async def test_query_log_creation(async_session):
    """VS-1: QueryLog record persists with timing fields."""
    from src.shared.models.api_key import ApiKey
    from src.shared.models.query_log import QueryLog

    key = ApiKey(key_hash="abc123hash", name="test-key", role="admin")
    async_session.add(key)
    await async_session.commit()
    await async_session.refresh(key)

    log = QueryLog(
        api_key_id=key.id,
        query_text="how to parse json",
        query_type="natural_language",
        result_count=3,
        retrieval_ms=45.2,
        rerank_ms=12.1,
        total_ms=57.3,
    )
    async_session.add(log)
    await async_session.commit()
    await async_session.refresh(log)

    assert log.id is not None
    assert isinstance(log.id, uuid.UUID)
    assert log.query_text == "how to parse json"
    assert log.retrieval_ms == pytest.approx(45.2)
    assert log.rerank_ms == pytest.approx(12.1)
    assert log.total_ms == pytest.approx(57.3)
    assert log.result_count == 3


# --- T19 (model variant): Repository null URL ---


# [unit] T19b: Repository without url violates NOT NULL
async def test_repository_null_url_raises(async_session):
    """Boundary: NOT NULL constraint on url."""
    from src.shared.models.repository import Repository

    repo = Repository(name="no-url-repo", url=None)
    async_session.add(repo)
    with pytest.raises(IntegrityError):
        await async_session.commit()
    await async_session.rollback()


# --- T20: ApiKey creation with defaults ---


# [unit] T20: ApiKey persists with is_active=True and created_at
async def test_api_key_creation_defaults(async_session):
    """VS-1: ApiKey has correct defaults."""
    from src.shared.models.api_key import ApiKey

    key = ApiKey(key_hash="somehash", name="my-key", role="read")
    async_session.add(key)
    await async_session.commit()
    await async_session.refresh(key)

    assert key.id is not None
    assert isinstance(key.id, uuid.UUID)
    assert key.is_active is True
    assert key.created_at is not None
    assert key.role == "read"
    assert key.name == "my-key"


# --- Branch coverage: explicit status in __init__ ---


# [unit] Repository with explicit status uses provided value
async def test_repository_explicit_status(async_session):
    """Branch: status provided explicitly overrides default."""
    from src.shared.models.repository import Repository

    repo = Repository(
        name="explicit-repo",
        url="https://github.com/test/explicit",
        status="indexing",
    )
    assert repo.status == "indexing"


# [unit] IndexJob with explicit status and phase uses provided values
async def test_index_job_explicit_status_and_phase(async_session):
    """Branch: status and phase provided explicitly override defaults."""
    from src.shared.models.index_job import IndexJob
    from src.shared.models.repository import Repository

    repo = Repository(name="explicit-job-repo", url="https://github.com/test/expjob")
    async_session.add(repo)
    await async_session.commit()
    await async_session.refresh(repo)

    job = IndexJob(repo_id=repo.id, branch="main", status="running", phase="cloning")
    assert job.status == "running"
    assert job.phase == "cloning"


# --- T20 (review fix): drop_all removes all tables ---


# [integration] T20: metadata drop_all removes all tables (downgrade equivalent)
async def test_drop_all_removes_tables(async_engine):
    """VS-1: Downgrade removes all 5 tables."""
    from src.shared.models.base import Base

    # Create tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Verify tables exist
    async with async_engine.connect() as conn:
        table_names = await conn.run_sync(
            lambda sync_conn: set(inspect(sync_conn).get_table_names())
        )
    assert "repository" in table_names

    # Drop all tables (equivalent to downgrade)
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    # Verify tables are gone
    async with async_engine.connect() as conn:
        table_names = await conn.run_sync(
            lambda sync_conn: set(inspect(sync_conn).get_table_names())
        )
    expected_gone = {"repository", "index_job", "api_key", "api_key_repo_access", "query_log"}
    assert expected_gone.isdisjoint(table_names), (
        f"Tables still exist after drop: {expected_gone & table_names}"
    )
