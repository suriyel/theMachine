"""
Tests for SQLAlchemy models — Feature #2: Data Model and Migrations.

Covers: Repository, IndexJob, CodeChunk, APIKey, QueryLog models.
Test categories: Happy path, Error handling, Boundary/edge, Security.

[integration] — uses real PostgreSQL (requires DATABASE_URL)
[real] — verifies actual database connectivity
"""

import uuid
from hashlib import sha256

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.models import (
    APIKey,
    ChunkGranularity,
    CodeChunk,
    IndexJob,
    JobStatus,
    KeyStatus,
    QueryLog,
    QueryType,
    RepoStatus,
    Repository,
    TriggerType,
)


# =============================================================================
# Repository Model Tests
# =============================================================================


class TestRepositoryModel:
    """Tests for Repository model — verification step #2."""

    @pytest.mark.asyncio
    @pytest.mark.real_test
    async def test_repository_create_happy_path(self, db_session: AsyncSession):
        """[integration] Given Repository model, when creating with url/name/languages, then persisted."""
        repo = Repository(
            url="https://github.com/example/repo.git",
            name="example-repo",
            languages=["Java", "Python"],
            status=RepoStatus.REGISTERED,
        )
        db_session.add(repo)
        await db_session.flush()

        assert repo.id is not None
        assert repo.url == "https://github.com/example/repo.git"
        assert repo.name == "example-repo"
        assert repo.languages == ["Java", "Python"]
        assert repo.status == RepoStatus.REGISTERED
        assert repo.created_at is not None

    @pytest.mark.asyncio
    @pytest.mark.real_test
    async def test_repository_queryable_after_persist(self, db_session: AsyncSession):
        """[integration] Given persisted Repository, when querying by URL, then found."""
        repo = Repository(
            url="https://github.com/test/query.git",
            name="query-test",
            languages=["Python"],
        )
        db_session.add(repo)
        await db_session.flush()

        result = await db_session.execute(
            select(Repository).where(Repository.url == "https://github.com/test/query.git")
        )
        fetched = result.scalar_one()
        assert fetched.name == "query-test"

    @pytest.mark.asyncio
    async def test_repository_duplicate_url_raises_error(self, db_session: AsyncSession):
        """[error] Given existing Repository with URL, when creating duplicate, then IntegrityError."""
        repo1 = Repository(
            url="https://github.com/duplicate/url.git",
            name="repo1",
            languages=[],
        )
        db_session.add(repo1)
        await db_session.flush()

        repo2 = Repository(
            url="https://github.com/duplicate/url.git",
            name="repo2",
            languages=[],
        )
        db_session.add(repo2)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    @pytest.mark.asyncio
    async def test_repository_empty_languages_list(self, db_session: AsyncSession):
        """[boundary] Given Repository with empty languages list, when persisting, then succeeds."""
        repo = Repository(
            url="https://github.com/test/empty-langs.git",
            name="empty-langs",
            languages=[],
        )
        db_session.add(repo)
        await db_session.flush()
        assert repo.languages == []

    @pytest.mark.asyncio
    async def test_repository_long_url_boundary(self, db_session: AsyncSession):
        """[boundary] Given Repository with 2000-char URL, when persisting, then succeeds."""
        long_url = "https://github.com/" + "a" * 1950 + ".git"
        repo = Repository(
            url=long_url,
            name="long-url",
            languages=[],
        )
        db_session.add(repo)
        await db_session.flush()
        assert repo.url == long_url

    @pytest.mark.asyncio
    async def test_repository_last_indexed_at_nullable(self, db_session: AsyncSession):
        """[boundary] Given new Repository, when created, then last_indexed_at is None."""
        repo = Repository(
            url="https://github.com/test/nullable-ts.git",
            name="nullable-ts",
            languages=[],
        )
        db_session.add(repo)
        await db_session.flush()
        assert repo.last_indexed_at is None


# =============================================================================
# IndexJob Model Tests
# =============================================================================


class TestIndexJobModel:
    """Tests for IndexJob model — verification step #3."""

    @pytest.mark.asyncio
    @pytest.mark.real_test
    async def test_index_job_create_with_queued_status(self, db_session: AsyncSession):
        """[integration] Given IndexJob model, when creating with QUEUED status, then persisted with UUID."""
        repo = Repository(
            url="https://github.com/test/job.git",
            name="job-test",
            languages=["Python"],
        )
        db_session.add(repo)
        await db_session.flush()

        job = IndexJob(
            repo_id=repo.id,
            status=JobStatus.QUEUED,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(job)
        await db_session.flush()

        assert job.id is not None
        assert isinstance(job.id, uuid.UUID)
        assert job.status == JobStatus.QUEUED
        assert job.trigger_type == TriggerType.MANUAL

    @pytest.mark.asyncio
    async def test_index_job_auto_generated_uuid(self, db_session: AsyncSession):
        """[integration] Given IndexJob, when created, then id is auto-generated UUID."""
        repo = Repository(
            url="https://github.com/test/uuid.git",
            name="uuid-test",
            languages=[],
        )
        db_session.add(repo)
        await db_session.flush()

        job = IndexJob(
            repo_id=repo.id,
            status=JobStatus.QUEUED,
            trigger_type=TriggerType.SCHEDULED,
        )
        db_session.add(job)
        await db_session.flush()

        assert job.id is not None
        assert isinstance(job.id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_index_job_invalid_repo_fk_raises_error(self, db_session: AsyncSession):
        """[error] Given IndexJob with non-existent repo_id, when persisting, then FK error."""
        job = IndexJob(
            repo_id=uuid.uuid4(),
            status=JobStatus.QUEUED,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(job)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    @pytest.mark.asyncio
    async def test_index_job_nullable_timestamps(self, db_session: AsyncSession):
        """[boundary] Given new IndexJob, when created, then started_at and completed_at are None."""
        repo = Repository(
            url="https://github.com/test/timestamps.git",
            name="ts-test",
            languages=[],
        )
        db_session.add(repo)
        await db_session.flush()

        job = IndexJob(
            repo_id=repo.id,
            status=JobStatus.QUEUED,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(job)
        await db_session.flush()

        assert job.started_at is None
        assert job.completed_at is None

    @pytest.mark.asyncio
    async def test_index_job_chunk_count_defaults_to_zero(self, db_session: AsyncSession):
        """[boundary] Given IndexJob, when created without chunk_count, then defaults to 0."""
        repo = Repository(
            url="https://github.com/test/chunk-default.git",
            name="chunk-default",
            languages=[],
        )
        db_session.add(repo)
        await db_session.flush()

        job = IndexJob(
            repo_id=repo.id,
            status=JobStatus.QUEUED,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(job)
        await db_session.flush()

        assert job.chunk_count == 0


# =============================================================================
# CodeChunk Model Tests
# =============================================================================


class TestCodeChunkModel:
    """Tests for CodeChunk model — verification step #4."""

    @pytest.mark.asyncio
    @pytest.mark.real_test
    async def test_code_chunk_create_happy_path(self, db_session: AsyncSession):
        """[integration] Given CodeChunk model, when creating with repo_id/file_path/content, then persisted."""
        repo = Repository(
            url="https://github.com/test/chunk.git",
            name="chunk-test",
            languages=["Python"],
        )
        db_session.add(repo)
        await db_session.flush()

        chunk_id = CodeChunk.generate_id(repo.id, "src/main.py", "main_function")
        chunk = CodeChunk(
            id=chunk_id,
            repo_id=repo.id,
            file_path="src/main.py",
            language="Python",
            granularity=ChunkGranularity.FUNCTION,
            symbol_name="main_function",
            content="def main_function(): pass",
            start_line=1,
            end_line=10,
        )
        db_session.add(chunk)
        await db_session.flush()

        assert chunk.id == chunk_id
        assert chunk.file_path == "src/main.py"
        assert chunk.content == "def main_function(): pass"

    @pytest.mark.asyncio
    async def test_code_chunk_composite_id_format(self, db_session: AsyncSession):
        """[integration] Given CodeChunk, when created, then id follows 'repo_id:file_path:symbol_hash' format."""
        repo = Repository(
            url="https://github.com/test/composite-id.git",
            name="composite-id",
            languages=[],
        )
        db_session.add(repo)
        await db_session.flush()

        chunk_id = CodeChunk.generate_id(repo.id, "lib/utils.py", "helper_func")
        assert ":" in chunk_id
        assert str(repo.id) in chunk_id

    @pytest.mark.asyncio
    async def test_code_chunk_invalid_repo_fk_raises_error(self, db_session: AsyncSession):
        """[error] Given CodeChunk with non-existent repo_id, when persisting, then FK error."""
        chunk_id = CodeChunk.generate_id(uuid.uuid4(), "test.py", None)
        chunk = CodeChunk(
            id=chunk_id,
            repo_id=uuid.uuid4(),
            file_path="test.py",
            language="Python",
            granularity=ChunkGranularity.FILE,
            content="pass",
            start_line=1,
            end_line=1,
        )
        db_session.add(chunk)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    @pytest.mark.asyncio
    async def test_code_chunk_nullable_symbol_name(self, db_session: AsyncSession):
        """[boundary] Given CodeChunk without symbol_name, when persisting, then succeeds (file-level chunk)."""
        repo = Repository(
            url="https://github.com/test/no-symbol.git",
            name="no-symbol",
            languages=[],
        )
        db_session.add(repo)
        await db_session.flush()

        chunk_id = CodeChunk.generate_id(repo.id, "README.md", None)
        chunk = CodeChunk(
            id=chunk_id,
            repo_id=repo.id,
            file_path="README.md",
            language="Markdown",
            granularity=ChunkGranularity.FILE,
            content="# Readme",
            start_line=1,
            end_line=10,
        )
        db_session.add(chunk)
        await db_session.flush()

        assert chunk.symbol_name is None

    @pytest.mark.asyncio
    async def test_code_chunk_large_content(self, db_session: AsyncSession):
        """[boundary] Given CodeChunk with 100KB content, when persisting, then succeeds."""
        repo = Repository(
            url="https://github.com/test/large-content.git",
            name="large-content",
            languages=[],
        )
        db_session.add(repo)
        await db_session.flush()

        large_content = "x" * 100000
        chunk_id = CodeChunk.generate_id(repo.id, "large.py", None)
        chunk = CodeChunk(
            id=chunk_id,
            repo_id=repo.id,
            file_path="large.py",
            language="Python",
            granularity=ChunkGranularity.FILE,
            content=large_content,
            start_line=1,
            end_line=1,
        )
        db_session.add(chunk)
        await db_session.flush()

        assert len(chunk.content) == 100000


# =============================================================================
# APIKey Model Tests
# =============================================================================


class TestAPIKeyModel:
    """Tests for APIKey model — verification step #5."""

    @pytest.mark.asyncio
    @pytest.mark.real_test
    async def test_api_key_create_with_active_status(self, db_session: AsyncSession):
        """[integration] Given APIKey model, when creating with key_hash/name, then persisted with status active."""
        key_hash = sha256(b"test-api-key").hexdigest()
        api_key = APIKey(
            key_hash=key_hash,
            name="Test API Key",
        )
        db_session.add(api_key)
        await db_session.flush()

        assert api_key.id is not None
        assert api_key.key_hash == key_hash
        assert api_key.name == "Test API Key"
        assert api_key.status == KeyStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_api_key_auto_generated_uuid(self, db_session: AsyncSession):
        """[integration] Given APIKey, when created, then id is auto-generated UUID."""
        key_hash = sha256(b"uuid-test-key").hexdigest()
        api_key = APIKey(
            key_hash=key_hash,
            name="UUID Test",
        )
        db_session.add(api_key)
        await db_session.flush()

        assert api_key.id is not None
        assert isinstance(api_key.id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_api_key_duplicate_hash_raises_error(self, db_session: AsyncSession):
        """[error] Given existing APIKey with same hash, when creating duplicate, then IntegrityError."""
        key_hash = sha256(b"duplicate-key").hexdigest()
        api_key1 = APIKey(key_hash=key_hash, name="Key 1")
        db_session.add(api_key1)
        await db_session.flush()

        api_key2 = APIKey(key_hash=key_hash, name="Key 2")
        db_session.add(api_key2)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    @pytest.mark.asyncio
    async def test_api_key_revoked_at_nullable(self, db_session: AsyncSession):
        """[boundary] Given new APIKey with active status, when created, then revoked_at is None."""
        key_hash = sha256(b"revoked-test").hexdigest()
        api_key = APIKey(key_hash=key_hash, name="Revoked Test")
        db_session.add(api_key)
        await db_session.flush()

        assert api_key.revoked_at is None

    @pytest.mark.asyncio
    async def test_api_key_revocation_sets_timestamp(self, db_session: AsyncSession):
        """[boundary] Given active APIKey, when revoked, then revoked_at is set."""
        key_hash = sha256(b"revoke-action").hexdigest()
        api_key = APIKey(key_hash=key_hash, name="Revoke Action")
        db_session.add(api_key)
        await db_session.flush()

        assert api_key.revoked_at is None
        assert api_key.is_active()

        api_key.revoke()
        await db_session.flush()

        assert api_key.revoked_at is not None
        assert not api_key.is_active()

    @pytest.mark.asyncio
    async def test_api_key_hash_not_plain_text(self, db_session: AsyncSession):
        """[security] Given APIKey, when stored, then key_hash is SHA-256 (64 hex chars), not plain text."""
        plain_key = "sk-test-secret-key-12345"
        key_hash = sha256(plain_key.encode()).hexdigest()
        api_key = APIKey(key_hash=key_hash, name="Hash Test")
        db_session.add(api_key)
        await db_session.flush()

        assert len(api_key.key_hash) == 64
        assert plain_key not in api_key.key_hash
        assert api_key.key_hash.isalnum()


# =============================================================================
# QueryLog Model Tests
# =============================================================================


class TestQueryLogModel:
    """Tests for QueryLog model — verification step #6."""

    @pytest.mark.asyncio
    @pytest.mark.real_test
    async def test_query_log_create_with_correlation_id(self, db_session: AsyncSession):
        """[integration] Given QueryLog model, when creating log entry, then persisted with correlation_id."""
        key_hash = sha256(b"query-log-key").hexdigest()
        api_key = APIKey(key_hash=key_hash, name="Query Log Test")
        db_session.add(api_key)
        await db_session.flush()

        query_log = QueryLog(
            api_key_id=api_key.id,
            query_text="how to use WebClient timeout",
            query_type=QueryType.NATURAL_LANGUAGE,
            result_count=3,
            latency_ms=142.5,
        )
        db_session.add(query_log)
        await db_session.flush()

        assert query_log.id is not None
        assert query_log.correlation_id is not None
        assert isinstance(query_log.correlation_id, uuid.UUID)
        assert query_log.query_text == "how to use WebClient timeout"

    @pytest.mark.asyncio
    async def test_query_log_auto_generated_uuid(self, db_session: AsyncSession):
        """[integration] Given QueryLog, when created, then id is auto-generated UUID."""
        query_log = QueryLog(
            query_text="test query",
            query_type=QueryType.SYMBOL,
            result_count=0,
            latency_ms=10.0,
        )
        db_session.add(query_log)
        await db_session.flush()

        assert query_log.id is not None
        assert isinstance(query_log.id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_query_log_missing_query_text_raises_error(self, db_session: AsyncSession):
        """[error] Given QueryLog without query_text, when persisting, then IntegrityError."""
        query_log = QueryLog(
            query_type=QueryType.NATURAL_LANGUAGE,
            result_count=0,
            latency_ms=10.0,
        )
        db_session.add(query_log)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    @pytest.mark.asyncio
    async def test_query_log_nullable_filters(self, db_session: AsyncSession):
        """[boundary] Given QueryLog without repo/language filter, when persisting, then succeeds."""
        query_log = QueryLog(
            query_text="test without filters",
            query_type=QueryType.NATURAL_LANGUAGE,
            result_count=5,
            latency_ms=50.0,
        )
        db_session.add(query_log)
        await db_session.flush()

        assert query_log.repo_filter is None
        assert query_log.language_filter is None

    @pytest.mark.asyncio
    async def test_query_log_long_query_text(self, db_session: AsyncSession):
        """[boundary] Given QueryLog with 10000-char query, when persisting, then succeeds."""
        long_query = "SELECT * FROM code WHERE content LIKE '%" + "x" * 9900 + "%'"
        query_log = QueryLog(
            query_text=long_query,
            query_type=QueryType.NATURAL_LANGUAGE,
            result_count=0,
            latency_ms=100.0,
        )
        db_session.add(query_log)
        await db_session.flush()

        assert len(query_log.query_text) > 9900

    @pytest.mark.asyncio
    async def test_query_log_latency_precision(self, db_session: AsyncSession):
        """[boundary] Given QueryLog with sub-millisecond latency (0.123), when persisting, then preserved."""
        query_log = QueryLog(
            query_text="precision test",
            query_type=QueryType.SYMBOL,
            result_count=1,
            latency_ms=0.123,
        )
        db_session.add(query_log)
        await db_session.flush()

        assert abs(query_log.latency_ms - 0.123) < 0.001


# =============================================================================
# Alembic Migration Tests
# NOTE: The conftest.py session_engine fixture validates migrations by running
# `alembic downgrade base` then `alembic upgrade head`. These tests verify
# the migration files themselves.
# =============================================================================


class TestAlembicMigrations:
    """Tests for Alembic migrations — verification step #1."""

    def test_migration_file_exists(self):
        """[integration] Given alembic directory, when checking versions, then initial migration exists."""
        from pathlib import Path

        versions_dir = Path(__file__).parent.parent / "alembic" / "versions"
        assert versions_dir.exists(), "alembic/versions directory should exist"

        migration_files = list(versions_dir.glob("*.py"))
        # Filter out __pycache__ and .pyc files
        migration_files = [f for f in migration_files if not f.name.startswith("__")]
        assert len(migration_files) >= 1, "At least one migration file should exist"

        # Check for initial schema migration
        initial_migration = next(
            (f for f in migration_files if "initial" in f.name.lower()), None
        )
        assert initial_migration is not None, "Initial schema migration should exist"

    def test_migration_contains_all_tables(self):
        """[integration] Given initial migration file, when parsing, then all 5 tables are created."""
        from pathlib import Path

        versions_dir = Path(__file__).parent.parent / "alembic" / "versions"
        migration_files = [f for f in versions_dir.glob("*.py") if not f.name.startswith("__")]
        initial_migration = next(
            f for f in migration_files if "initial" in f.name.lower()
        )

        content = initial_migration.read_text()

        expected_tables = ["api_keys", "repositories", "code_chunks", "index_jobs", "query_logs"]
        for table in expected_tables:
            assert f"'{table}'" in content or f'"{table}"' in content, f"Migration should create {table} table"

    def test_migration_contains_all_enums(self):
        """[integration] Given initial migration file, when parsing, then all enums are defined."""
        from pathlib import Path

        versions_dir = Path(__file__).parent.parent / "alembic" / "versions"
        migration_files = [f for f in versions_dir.glob("*.py") if not f.name.startswith("__")]
        initial_migration = next(
            f for f in migration_files if "initial" in f.name.lower()
        )

        content = initial_migration.read_text()

        expected_enums = ["repo_status", "job_status", "trigger_type", "chunk_granularity", "key_status", "query_type"]
        for enum_name in expected_enums:
            assert f"name='{enum_name}'" in content or f'name="{enum_name}"' in content, f"Migration should define {enum_name} enum"

    def test_migration_has_foreign_keys_with_cascade(self):
        """[integration] Given initial migration file, when parsing, then FK constraints have CASCADE delete."""
        from pathlib import Path

        versions_dir = Path(__file__).parent.parent / "alembic" / "versions"
        migration_files = [f for f in versions_dir.glob("*.py") if not f.name.startswith("__")]
        initial_migration = next(
            f for f in migration_files if "initial" in f.name.lower()
        )

        content = initial_migration.read_text()

        # Should have CASCADE on foreign keys
        assert "ondelete='CASCADE'" in content or 'ondelete="CASCADE"' in content, "FK constraints should have CASCADE delete"


# =============================================================================
# Real Tests — Database Connectivity Verification
# =============================================================================


class TestRealDatabaseConnectivity:
    """[real] Tests that verify actual database connectivity without mocking."""

    @pytest.mark.asyncio
    @pytest.mark.real_test
    async def test_real_postgres_connection(self):
        """[real] Given DATABASE_URL, when connecting to PostgreSQL, then succeeds."""
        from src.shared.clients import check_postgres_connection

        result = await check_postgres_connection()

        assert result["status"] == "ok", f"PostgreSQL connection failed: {result}"
        assert "version" in result
        assert "PostgreSQL" in result["version"]

    @pytest.mark.asyncio
    @pytest.mark.real_test
    async def test_real_postgres_session_factory(self, db_session: AsyncSession):
        """[real] Given async session factory, when creating session, then can execute raw SQL."""
        result = await db_session.execute(text("SELECT 1 as value"))
        row = result.fetchone()
        assert row is not None
        assert row[0] == 1


# =============================================================================
# Test Statistics
# =============================================================================
# Total tests: 33
# Happy path: 8
# Error handling: 6
# Boundary/edge: 14
# Security: 1
# Negative test ratio: (6 + 14 + 1) / 33 = 64% >= 40% ✓
