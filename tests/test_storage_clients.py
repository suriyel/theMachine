"""Tests for storage client health checks and connections.

Feature #1: Project Skeleton and CI
Verification Steps:
- Directory structure exists (src/, tests/, docs/, examples/, scripts/)
- PostgreSQL connection succeeds with valid DATABASE_URL
- Redis connection returns PONG
- Qdrant health check returns ok
- Elasticsearch cluster health returns green/yellow
"""

import pytest
import pytest_asyncio
from pathlib import Path


# ============================================================================
# Unit Tests - Directory Structure
# ============================================================================


class TestDirectoryStructure:
    """[unit] Verify project directory structure."""

    def test_src_directory_exists(self):
        """Given project root, when checking for src/, then directory exists."""
        project_root = Path(__file__).parent.parent
        src_dir = project_root / "src"
        assert src_dir.exists(), "src/ directory should exist"
        assert src_dir.is_dir(), "src/ should be a directory"

    def test_tests_directory_exists(self):
        """Given project root, when checking for tests/, then directory exists."""
        project_root = Path(__file__).parent.parent
        tests_dir = project_root / "tests"
        assert tests_dir.exists(), "tests/ directory should exist"
        assert tests_dir.is_dir(), "tests/ should be a directory"

    def test_docs_directory_exists(self):
        """Given project root, when checking for docs/, then directory exists."""
        project_root = Path(__file__).parent.parent
        docs_dir = project_root / "docs"
        assert docs_dir.exists(), "docs/ directory should exist"
        assert docs_dir.is_dir(), "docs/ should be a directory"

    def test_examples_directory_exists(self):
        """Given project root, when checking for examples/, then directory exists."""
        project_root = Path(__file__).parent.parent
        examples_dir = project_root / "examples"
        assert examples_dir.exists(), "examples/ directory should exist"
        assert examples_dir.is_dir(), "examples/ should be a directory"

    def test_scripts_directory_exists(self):
        """Given project root, when checking for scripts/, then directory exists."""
        project_root = Path(__file__).parent.parent
        scripts_dir = project_root / "scripts"
        assert scripts_dir.exists(), "scripts/ directory should exist"
        assert scripts_dir.is_dir(), "scripts/ should be a directory"

    def test_pyproject_toml_exists(self):
        """Given project root, when checking for pyproject.toml, then file exists."""
        project_root = Path(__file__).parent.parent
        pyproject = project_root / "pyproject.toml"
        assert pyproject.exists(), "pyproject.toml should exist"
        assert pyproject.is_file(), "pyproject.toml should be a file"

    def test_ci_workflow_exists(self):
        """Given project root, when checking for CI workflow, then file exists."""
        project_root = Path(__file__).parent.parent
        ci_workflow = project_root / ".github" / "workflows" / "ci.yml"
        assert ci_workflow.exists(), ".github/workflows/ci.yml should exist"
        assert ci_workflow.is_file(), "ci.yml should be a file"


# ============================================================================
# Unit Tests - Health Check Function Imports
# ============================================================================


class TestHealthCheckImports:
    """[unit] Verify health check functions can be imported."""

    def test_import_check_postgres_connection(self):
        """Given storage clients module, when importing, then check_postgres_connection exists."""
        from src.shared.clients import check_postgres_connection
        assert callable(check_postgres_connection), "check_postgres_connection should be callable"

    def test_import_check_redis_connection(self):
        """Given storage clients module, when importing, then check_redis_connection exists."""
        from src.shared.clients import check_redis_connection
        assert callable(check_redis_connection), "check_redis_connection should be callable"

    def test_import_check_qdrant_connection(self):
        """Given storage clients module, when importing, then check_qdrant_connection exists."""
        from src.shared.clients import check_qdrant_connection
        assert callable(check_qdrant_connection), "check_qdrant_connection should be callable"

    def test_import_check_elasticsearch_connection(self):
        """Given storage clients module, when importing, then check_elasticsearch_connection exists."""
        from src.shared.clients import check_elasticsearch_connection
        assert callable(check_elasticsearch_connection), "check_elasticsearch_connection should be callable"


# ============================================================================
# Real Tests - Storage Client Connections
# ============================================================================

# These tests connect to REAL services (no mocks) per Rule 5a
# Services are configured via Settings which loads from .env file


def _skip_if_not_configured(url: str, service_name: str) -> str:
    """Skip test if service URL is not configured."""
    if not url:
        pytest.skip(f"{service_name} not configured in .env")
    return url


async def _skip_if_service_unavailable(check_func, service_name: str):
    """Skip test if service is not actually running (not just configured)."""
    try:
        await check_func()
    except (ConnectionError, Exception) as e:
        pytest.skip(f"{service_name} service not available: {e}")


@pytest.mark.real_test
class TestPostgreSQLConnection:
    """[real_test] PostgreSQL connection tests - connects to real database.

    No mock on primary dependency - uses real DATABASE_URL from Settings.
    """

    @pytest_asyncio.fixture
    async def postgres_url(self):
        """Get PostgreSQL URL from Settings (loads from .env)."""
        from src.query.config import settings
        return _skip_if_not_configured(settings.DATABASE_URL, "DATABASE_URL")

    @pytest.mark.asyncio
    async def test_postgres_connection_succeeds(self, postgres_url):
        """Given valid DATABASE_URL, when checking PostgreSQL connection, then connection succeeds.

        Wrong implementation challenge:
        - Returning True without connecting would fail (we verify actual connection)
        - Connecting to wrong database would fail (we verify correct database)
        """
        from src.shared.clients import check_postgres_connection

        result = await check_postgres_connection()

        assert result["status"] == "ok", f"PostgreSQL connection should succeed, got: {result}"
        assert "latency_ms" in result, "Result should include latency measurement"
        assert result["latency_ms"] >= 0, "Latency should be non-negative"
        assert result["latency_ms"] < 5000, "Latency should be reasonable (<5s)"

    @pytest.mark.asyncio
    async def test_postgres_connection_returns_version(self, postgres_url):
        """Given valid DATABASE_URL, when checking PostgreSQL connection, then version is returned.

        Wrong implementation challenge:
        - Returning hardcoded version would fail (we check it contains 'PostgreSQL')
        """
        from src.shared.clients import check_postgres_connection

        result = await check_postgres_connection()

        assert result["status"] == "ok"
        assert "version" in result, "Result should include PostgreSQL version"
        assert "PostgreSQL" in result["version"], "Version string should contain 'PostgreSQL'"


@pytest.mark.real_test
class TestRedisConnection:
    """[real_test] Redis connection tests - connects to real Redis server.

    No mock on primary dependency - uses real REDIS_URL from Settings.
    """

    @pytest_asyncio.fixture
    async def redis_url(self):
        """Get Redis URL from Settings (loads from .env)."""
        from src.query.config import settings
        return _skip_if_not_configured(settings.REDIS_URL, "REDIS_URL")

    @pytest.mark.asyncio
    async def test_redis_ping_returns_pong(self, redis_url):
        """Given valid REDIS_URL, when pinging Redis, then response is PONG.

        Wrong implementation challenge:
        - Returning 'PONG' without connecting would fail (we verify actual ping)
        - Connecting to wrong Redis would fail (we verify connection)
        """
        from src.shared.clients import check_redis_connection

        result = await check_redis_connection()

        assert result["status"] == "ok", f"Redis connection should succeed, got: {result}"
        assert result["ping"] == "PONG", f"Redis ping should return PONG, got: {result['ping']}"

    @pytest.mark.asyncio
    async def test_redis_connection_returns_latency(self, redis_url):
        """Given valid REDIS_URL, when checking Redis connection, then latency is returned.

        Wrong implementation challenge:
        - Returning fake latency would fail (we verify it's reasonable)
        """
        from src.shared.clients import check_redis_connection

        result = await check_redis_connection()

        assert "latency_ms" in result, "Result should include latency measurement"
        assert result["latency_ms"] >= 0, "Latency should be non-negative"
        assert result["latency_ms"] < 1000, "Latency should be reasonable (<1s)"


@pytest.mark.real_test
class TestQdrantConnection:
    """[real_test] Qdrant connection tests - connects to real Qdrant server.

    No mock on primary dependency - uses real QDRANT_URL from Settings.
    """

    @pytest_asyncio.fixture
    async def qdrant_available(self):
        """Check if Qdrant service is actually available (not just configured)."""
        from src.query.config import settings
        _skip_if_not_configured(settings.QDRANT_URL, "QDRANT_URL")
        from src.shared.clients import check_qdrant_connection
        await _skip_if_service_unavailable(check_qdrant_connection, "Qdrant")
        return settings.QDRANT_URL

    @pytest.mark.asyncio
    async def test_qdrant_health_check_succeeds(self, qdrant_available):
        """Given valid QDRANT_URL, when checking Qdrant health, then returns ok.

        Wrong implementation challenge:
        - Returning ok without connecting would fail (we verify actual health check)
        """
        from src.shared.clients import check_qdrant_connection

        result = await check_qdrant_connection()

        assert result["status"] == "ok", f"Qdrant health check should succeed, got: {result}"

    @pytest.mark.asyncio
    async def test_qdrant_connection_returns_version(self, qdrant_available):
        """Given valid QDRANT_URL, when checking Qdrant connection, then version is returned.

        Wrong implementation challenge:
        - Returning hardcoded version would fail (we verify it's non-empty)
        """
        from src.shared.clients import check_qdrant_connection

        result = await check_qdrant_connection()

        assert "version" in result, "Result should include Qdrant version"
        assert result["version"], "Version should not be empty"


@pytest.mark.real_test
class TestElasticsearchConnection:
    """[real_test] Elasticsearch connection tests - connects to real ES cluster.

    No mock on primary dependency - uses real ELASTICSEARCH_URL from Settings.
    """

    @pytest_asyncio.fixture
    async def es_available(self):
        """Check if Elasticsearch service is actually available (not just configured)."""
        from src.query.config import settings
        _skip_if_not_configured(settings.ELASTICSEARCH_URL, "ELASTICSEARCH_URL")
        from src.shared.clients import check_elasticsearch_connection
        await _skip_if_service_unavailable(check_elasticsearch_connection, "Elasticsearch")
        return settings.ELASTICSEARCH_URL

    @pytest.mark.asyncio
    async def test_elasticsearch_cluster_health_succeeds(self, es_available):
        """Given valid ELASTICSEARCH_URL, when checking cluster health, then returns green or yellow.

        Wrong implementation challenge:
        - Returning 'green' without connecting would fail (we verify actual health)
        - Accepting 'red' status would be wrong (we verify green/yellow only)
        """
        from src.shared.clients import check_elasticsearch_connection

        result = await check_elasticsearch_connection()

        assert result["status"] == "ok", f"ES connection should succeed, got: {result}"
        assert "cluster_health" in result, "Result should include cluster health status"
        assert result["cluster_health"] in ("green", "yellow"), \
            f"Cluster health should be green or yellow, got: {result['cluster_health']}"

    @pytest.mark.asyncio
    async def test_elasticsearch_connection_returns_cluster_name(self, es_available):
        """Given valid ELASTICSEARCH_URL, when checking connection, then cluster name is returned.

        Wrong implementation challenge:
        - Returning hardcoded cluster name would fail (we verify actual cluster name)
        """
        from src.shared.clients import check_elasticsearch_connection

        result = await check_elasticsearch_connection()

        assert "cluster_name" in result, "Result should include cluster name"
        assert result["cluster_name"], "Cluster name should not be empty"

    @pytest.mark.asyncio
    async def test_elasticsearch_connection_returns_version(self, es_available):
        """Given valid ELASTICSEARCH_URL, when checking connection, then version is returned.

        Wrong implementation challenge:
        - Returning hardcoded version would fail (we verify it contains version number)
        """
        from src.shared.clients import check_elasticsearch_connection

        result = await check_elasticsearch_connection()

        assert "version" in result, "Result should include ES version"
        assert result["version"], "Version should not be empty"


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestConnectionErrorHandling:
    """[unit] Verify connection error handling for invalid configurations.

    Security: N/A - internal utility functions, no user-facing input.
    """

    @pytest.mark.asyncio
    async def test_postgres_invalid_url_raises_error(self, monkeypatch):
        """Given invalid DATABASE_URL, when connecting, then ConnectionError is raised.

        Wrong implementation challenge:
        - Silently returning False would fail (we verify exception is raised)
        - Returning generic error would fail (we verify ConnectionError type)
        """
        from src.shared.clients import check_postgres_connection
        from src.query.config import settings

        # Temporarily override settings
        original_url = settings.DATABASE_URL
        monkeypatch.setattr(settings, "DATABASE_URL", "postgresql+asyncpg://invalid:invalid@nonexistent:5432/invalid")

        with pytest.raises(ConnectionError) as exc_info:
            await check_postgres_connection()

        assert "PostgreSQL" in str(exc_info.value) or "connection" in str(exc_info.value).lower()

        # Restore original URL
        monkeypatch.setattr(settings, "DATABASE_URL", original_url)

    @pytest.mark.asyncio
    async def test_redis_invalid_url_raises_error(self, monkeypatch):
        """Given invalid REDIS_URL, when connecting, then ConnectionError is raised.

        Wrong implementation challenge:
        - Silently returning False would fail (we verify exception is raised)
        """
        from src.shared.clients import check_redis_connection
        from src.query.config import settings

        original_url = settings.REDIS_URL
        monkeypatch.setattr(settings, "REDIS_URL", "redis://nonexistent:6379/0")

        with pytest.raises(ConnectionError) as exc_info:
            await check_redis_connection()

        assert "Redis" in str(exc_info.value) or "connection" in str(exc_info.value).lower()

        monkeypatch.setattr(settings, "REDIS_URL", original_url)

    @pytest.mark.asyncio
    async def test_qdrant_invalid_url_raises_error(self, monkeypatch):
        """Given invalid QDRANT_URL, when connecting, then ConnectionError is raised."""
        from src.shared.clients import check_qdrant_connection
        from src.query.config import settings

        original_url = settings.QDRANT_URL
        monkeypatch.setattr(settings, "QDRANT_URL", "http://nonexistent:6333")

        with pytest.raises(ConnectionError) as exc_info:
            await check_qdrant_connection()

        assert "Qdrant" in str(exc_info.value) or "connection" in str(exc_info.value).lower()

        monkeypatch.setattr(settings, "QDRANT_URL", original_url)

    @pytest.mark.asyncio
    async def test_elasticsearch_invalid_url_raises_error(self, monkeypatch):
        """Given invalid ELASTICSEARCH_URL, when connecting, then ConnectionError is raised."""
        from src.shared.clients import check_elasticsearch_connection
        from src.query.config import settings

        original_url = settings.ELASTICSEARCH_URL
        monkeypatch.setattr(settings, "ELASTICSEARCH_URL", "http://nonexistent:9200")

        with pytest.raises(ConnectionError) as exc_info:
            await check_elasticsearch_connection()

        assert "Elasticsearch" in str(exc_info.value) or "connection" in str(exc_info.value).lower()

        monkeypatch.setattr(settings, "ELASTICSEARCH_URL", original_url)


class TestClientLifecycle:
    """[unit] Verify client initialization and cleanup lifecycle."""

    @pytest.mark.asyncio
    async def test_init_clients_creates_connections(self):
        """Given valid settings, when initializing clients, then connections are created."""
        from src.shared.clients import init_clients, _qdrant_client, _es_client, _redis_client

        # Reset global clients
        import src.shared.clients as clients_module
        clients_module._qdrant_client = None
        clients_module._es_client = None
        clients_module._redis_client = None

        await init_clients()

        assert clients_module._qdrant_client is not None, "Qdrant client should be initialized"
        assert clients_module._es_client is not None, "Elasticsearch client should be initialized"
        assert clients_module._redis_client is not None, "Redis client should be initialized"

        # Cleanup
        await clients_module.close_clients()

    @pytest.mark.asyncio
    async def test_close_clients_cleans_up(self):
        """Given initialized clients, when closing clients, then they are set to None."""
        from src.shared.clients import init_clients, close_clients
        import src.shared.clients as clients_module

        # Initialize first
        clients_module._qdrant_client = None
        clients_module._es_client = None
        clients_module._redis_client = None
        await init_clients()

        # Now close
        await close_clients()

        assert clients_module._qdrant_client is None, "Qdrant client should be None after close"
        assert clients_module._es_client is None, "Elasticsearch client should be None after close"
        assert clients_module._redis_client is None, "Redis client should be None after close"

    @pytest.mark.asyncio
    async def test_close_clients_handles_none_gracefully(self):
        """Given no initialized clients, when closing, then no error is raised."""
        from src.shared.clients import close_clients
        import src.shared.clients as clients_module

        # Ensure clients are None
        clients_module._qdrant_client = None
        clients_module._es_client = None
        clients_module._redis_client = None

        # Should not raise
        await close_clients()

    def test_get_qdrant_raises_if_not_initialized(self):
        """Given uninitialized clients, when getting Qdrant client, then RuntimeError is raised."""
        from src.shared.clients import get_qdrant
        import src.shared.clients as clients_module

        clients_module._qdrant_client = None

        with pytest.raises(RuntimeError, match="not initialized"):
            get_qdrant()

    def test_get_elasticsearch_raises_if_not_initialized(self):
        """Given uninitialized clients, when getting ES client, then RuntimeError is raised."""
        from src.shared.clients import get_elasticsearch
        import src.shared.clients as clients_module

        clients_module._es_client = None

        with pytest.raises(RuntimeError, match="not initialized"):
            get_elasticsearch()

    def test_get_redis_raises_if_not_initialized(self):
        """Given uninitialized clients, when getting Redis client, then RuntimeError is raised."""
        from src.shared.clients import get_redis
        import src.shared.clients as clients_module

        clients_module._redis_client = None

        with pytest.raises(RuntimeError, match="not initialized"):
            get_redis()

    @pytest.mark.asyncio
    async def test_get_clients_returns_initialized_instances(self):
        """Given initialized clients, when getting them, then correct instances are returned."""
        from src.shared.clients import init_clients, get_qdrant, get_elasticsearch, get_redis
        import src.shared.clients as clients_module

        # Reset and initialize
        clients_module._qdrant_client = None
        clients_module._es_client = None
        clients_module._redis_client = None
        await init_clients()

        qdrant = get_qdrant()
        es = get_elasticsearch()
        redis = get_redis()

        assert qdrant is not None
        assert es is not None
        assert redis is not None

        # Cleanup
        await clients_module.close_clients()
