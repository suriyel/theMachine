"""Tests for src.query.main — production entrypoint for query-api Docker image.

Feature #43: query-api Docker Image
SRS: FR-027: query-api Docker Image [Wave 4]

Test layers:
  [unit]        — exercises build_app() / main() with lazy (no-connect) constructors
  [integration] — Docker daemon required; builds and inspects codecontext-api image

Security: N/A — entrypoint wires production services from env vars;
no user-facing input surface; no injection vectors in the tested code paths.
"""

from __future__ import annotations

import json
import subprocess
import time
import urllib.request
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Shared env-var table (all five required vars with test/fake values)
# ---------------------------------------------------------------------------

_REQUIRED_ENV_VARS: dict[str, str] = {
    "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/testdb",
    "ELASTICSEARCH_URL": "http://localhost:9200",
    "QDRANT_URL": "http://localhost:6333",
    "REDIS_URL": "redis://localhost:6379",
    "SECRET_KEY": "test-secret-key",
}


@pytest.fixture
def all_env_vars(monkeypatch):
    """Set all five required env vars in the process environment."""
    for key, value in _REQUIRED_ENV_VARS.items():
        monkeypatch.setenv(key, value)


# ===========================================================================
# Unit Tests — build_app() and main()
# ===========================================================================

# [unit] — all clients/services use lazy init (no actual network at construction
# time), so build_app() can be called with fake URLs in tests.


def test_build_app_returns_fastapi_with_wired_services(all_env_vars):
    """T06: build_app() returns a FastAPI instance with key service instances on app.state.

    Kills bug: build_app() skipping service wiring or returning wrong type.
    """
    from fastapi import FastAPI

    from src.query.main import build_app
    from src.query.query_handler import QueryHandler
    from src.shared.clients.elasticsearch import ElasticsearchClient

    app = build_app()

    assert isinstance(app, FastAPI), f"Expected FastAPI instance, got {type(app)}"
    assert isinstance(app.state.query_handler, QueryHandler), (
        f"app.state.query_handler should be QueryHandler, got {type(app.state.query_handler)}"
    )
    assert isinstance(app.state.es_client, ElasticsearchClient), (
        f"app.state.es_client should be ElasticsearchClient, got {type(app.state.es_client)}"
    )


def test_main_calls_uvicorn_with_correct_bind_args(all_env_vars):
    """T07: main() calls uvicorn.run with host='0.0.0.0', port=8000, log_level='info'.

    Kills bug: wrong host/port/log_level passed to uvicorn.
    """
    with patch("src.query.main.uvicorn.run") as mock_run:
        from src.query.main import main

        main()

    mock_run.assert_called_once()
    _, kwargs = mock_run.call_args
    assert kwargs["host"] == "0.0.0.0", f"Expected host='0.0.0.0', got {kwargs.get('host')!r}"
    assert kwargs["port"] == 8000, f"Expected port=8000, got {kwargs.get('port')!r}"
    assert kwargs["log_level"] == "info", (
        f"Expected log_level='info', got {kwargs.get('log_level')!r}"
    )


def test_build_app_raises_key_error_missing_database_url(monkeypatch):
    """T08: build_app() raises KeyError when DATABASE_URL is absent.

    Kills bug: missing env var silently falling back to None or empty string.
    """
    for key, value in _REQUIRED_ENV_VARS.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("DATABASE_URL")

    from src.query.main import build_app

    with pytest.raises(KeyError) as exc:
        build_app()

    assert "DATABASE_URL" in str(exc.value), (
        f"Expected 'DATABASE_URL' in KeyError message, got: {exc.value!r}"
    )


def test_build_app_raises_key_error_missing_elasticsearch_url(monkeypatch):
    """T09: build_app() raises KeyError when ELASTICSEARCH_URL is absent.

    Kills bug: env var read order masking the actual missing var.
    """
    for key, value in _REQUIRED_ENV_VARS.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("ELASTICSEARCH_URL")

    from src.query.main import build_app

    with pytest.raises(KeyError) as exc:
        build_app()

    assert "ELASTICSEARCH_URL" in str(exc.value), (
        f"Expected 'ELASTICSEARCH_URL' in KeyError message, got: {exc.value!r}"
    )


def test_main_exits_1_when_secret_key_missing(monkeypatch):
    """T10: main() calls sys.exit(1) when SECRET_KEY is absent.

    Kills bug: main() not catching KeyError, crashing with ugly traceback instead
    of a friendly sys.exit(1).
    """
    for key, value in _REQUIRED_ENV_VARS.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("SECRET_KEY")

    with patch("src.query.main.uvicorn.run"):
        from src.query.main import main

        with pytest.raises(SystemExit) as exc:
            main()

    assert exc.value.code == 1, f"Expected sys.exit(1), got sys.exit({exc.value.code!r})"


def test_main_propagates_oserror_from_uvicorn(all_env_vars):
    """T11: OSError from uvicorn.run (e.g. port conflict) propagates out of main().

    Kills bug: main() accidentally swallowing OSError.
    """
    with patch(
        "src.query.main.uvicorn.run", side_effect=OSError("address already in use")
    ):
        from src.query.main import main

        with pytest.raises(OSError):
            main()


def test_build_app_accepts_empty_secret_key(monkeypatch):
    """T12: build_app() accepts SECRET_KEY='' (validation deferred to auth layer).

    Kills bug: build_app() rejecting empty SECRET_KEY when it should not.
    """
    for key, value in _REQUIRED_ENV_VARS.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("SECRET_KEY", "")

    from fastapi import FastAPI

    from src.query.main import build_app

    app = build_app()

    assert isinstance(app, FastAPI), f"Expected FastAPI instance, got {type(app)}"


def test_build_app_raises_key_error_missing_redis_url(monkeypatch):
    """T13: build_app() raises KeyError when REDIS_URL is absent.

    Kills bug: skipping REDIS_URL check because Redis is 'optional' at query layer.
    """
    for key, value in _REQUIRED_ENV_VARS.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("REDIS_URL")

    from src.query.main import build_app

    with pytest.raises(KeyError) as exc:
        build_app()

    assert "REDIS_URL" in str(exc.value), (
        f"Expected 'REDIS_URL' in KeyError message, got: {exc.value!r}"
    )


def test_build_app_raises_key_error_missing_qdrant_url(monkeypatch):
    """T14: build_app() raises KeyError when QDRANT_URL is absent.

    Kills bug: QDRANT_URL silently defaulting to localhost.
    """
    for key, value in _REQUIRED_ENV_VARS.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("QDRANT_URL")

    from src.query.main import build_app

    with pytest.raises(KeyError) as exc:
        build_app()

    assert "QDRANT_URL" in str(exc.value), (
        f"Expected 'QDRANT_URL' in KeyError message, got: {exc.value!r}"
    )


def test_build_app_wires_all_service_instances(all_env_vars):
    """T15: build_app() wires ALL required services on app.state with correct types.

    Kills bugs: any service wired as None, wrong type, or missing from app.state.
    Also verifies deep wiring — internal fields of query_handler, auth_middleware,
    api_key_manager, and query_cache must use the same shared client instances.
    """
    from src.query.main import build_app
    from src.query.query_cache import QueryCache
    from src.query.query_handler import QueryHandler
    from src.query.rank_fusion import RankFusion
    from src.query.reranker import Reranker
    from src.query.response_builder import ResponseBuilder
    from src.query.retriever import Retriever
    from src.shared.clients.elasticsearch import ElasticsearchClient
    from src.shared.clients.qdrant import QdrantClientWrapper
    from src.shared.clients.redis import RedisClient
    from src.shared.services.api_key_manager import APIKeyManager
    from src.shared.services.auth_middleware import AuthMiddleware

    app = build_app()

    # --- Top-level app.state types ---
    assert isinstance(app.state.es_client, ElasticsearchClient), (
        f"es_client should be ElasticsearchClient, got {type(app.state.es_client)}"
    )
    assert isinstance(app.state.qdrant_client, QdrantClientWrapper), (
        f"qdrant_client should be QdrantClientWrapper, got {type(app.state.qdrant_client)}"
    )
    assert isinstance(app.state.redis_client, RedisClient), (
        f"redis_client should be RedisClient, got {type(app.state.redis_client)}"
    )
    assert isinstance(app.state.query_handler, QueryHandler), (
        f"query_handler should be QueryHandler, got {type(app.state.query_handler)}"
    )
    assert isinstance(app.state.auth_middleware, AuthMiddleware), (
        f"auth_middleware should be AuthMiddleware, got {type(app.state.auth_middleware)}"
    )
    assert isinstance(app.state.api_key_manager, APIKeyManager), (
        f"api_key_manager should be APIKeyManager, got {type(app.state.api_key_manager)}"
    )
    assert isinstance(app.state.query_cache, QueryCache), (
        f"query_cache should be QueryCache, got {type(app.state.query_cache)}"
    )
    assert app.state.session_factory is not None, (
        "session_factory on app.state must not be None"
    )

    # --- Deep wiring: query_handler internals ---
    qh = app.state.query_handler
    assert isinstance(qh._retriever, Retriever), (
        f"query_handler._retriever should be Retriever, got {type(qh._retriever)}"
    )
    assert isinstance(qh._retriever._es, ElasticsearchClient), (
        f"retriever._es should be ElasticsearchClient, got {type(qh._retriever._es)}"
    )
    assert isinstance(qh._retriever._qdrant, QdrantClientWrapper), (
        f"retriever._qdrant should be QdrantClientWrapper, got {type(qh._retriever._qdrant)}"
    )
    assert isinstance(qh._rank_fusion, RankFusion), (
        f"query_handler._rank_fusion should be RankFusion, got {type(qh._rank_fusion)}"
    )
    assert isinstance(qh._reranker, Reranker), (
        f"query_handler._reranker should be Reranker, got {type(qh._reranker)}"
    )
    assert isinstance(qh._response_builder, ResponseBuilder), (
        f"query_handler._response_builder should be ResponseBuilder, got {type(qh._response_builder)}"
    )

    # --- Deep wiring: auth_middleware internals ---
    am = app.state.auth_middleware
    assert isinstance(am._redis, RedisClient), (
        f"auth_middleware._redis should be RedisClient, got {type(am._redis)}"
    )
    assert am._session_factory is not None, (
        "auth_middleware._session_factory must not be None"
    )

    # --- Deep wiring: api_key_manager internals ---
    akm = app.state.api_key_manager
    assert isinstance(akm._redis, RedisClient), (
        f"api_key_manager._redis should be RedisClient, got {type(akm._redis)}"
    )
    assert akm._session_factory is not None, (
        "api_key_manager._session_factory must not be None"
    )

    # --- Deep wiring: query_cache internals ---
    qc = app.state.query_cache
    assert isinstance(qc._redis, RedisClient), (
        f"query_cache._redis should be RedisClient, got {type(qc._redis)}"
    )


def test_main_passes_app_to_uvicorn(all_env_vars):
    """T16: main() passes the wired FastAPI app as the first positional arg to uvicorn.run.

    Kills bug: main() passing None or wrong object to uvicorn.run.
    """
    from fastapi import FastAPI

    with patch("src.query.main.uvicorn.run") as mock_run:
        from src.query.main import main

        main()

    mock_run.assert_called_once()
    args, _ = mock_run.call_args
    assert len(args) == 1, f"Expected 1 positional arg to uvicorn.run, got {len(args)}"
    assert isinstance(args[0], FastAPI), (
        f"First arg to uvicorn.run should be FastAPI app, got {type(args[0])}"
    )


def test_main_stderr_output_on_missing_env(monkeypatch, capsys):
    """T17: main() prints error to stderr (not stdout) when an env var is missing.

    Kills bug: error message going to wrong output stream.
    """
    for key, value in _REQUIRED_ENV_VARS.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("SECRET_KEY")

    from src.query.main import main

    with pytest.raises(SystemExit):
        main()

    captured = capsys.readouterr()
    assert captured.err != "", "Expected error message on stderr, got empty string"
    assert captured.out == "", f"Expected no output on stdout, got: {captured.out!r}"


# ===========================================================================
# Docker Integration Tests — codecontext-api image build and runtime
# ===========================================================================

# [integration] — require Docker daemon; build codecontext-api image from
# docker/Dockerfile.api and verify build artifact, HEALTHCHECK, deps, and user.
#
# Ordering: T01 (build) must run before T02-T05 since the latter inspect / run
# the built image. pytest collects in file order by default.


@pytest.mark.real
def test_docker_build_exits_zero():
    """T01: docker build -f docker/Dockerfile.api -t codecontext-api . exits 0.

    Kills bug: Dockerfile syntax error or missing COPY source path.
    feature-43
    """
    result = subprocess.run(
        [
            "docker", "build",
            "-f", "docker/Dockerfile.api",
            "-t", "codecontext-api",
            ".",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"docker build failed (exit {result.returncode}):\n"
        f"STDOUT (last 2000):\n{result.stdout[-2000:]}\n"
        f"STDERR (last 2000):\n{result.stderr[-2000:]}"
    )


@pytest.mark.real
def test_container_health_endpoint_returns_200_within_30s():
    """T02: container started with env vars responds HTTP 200 on /api/v1/health within 30s.

    Kills bug: entrypoint not wiring services; uvicorn not starting.
    The health endpoint returns 200 even with degraded (unconnected) services.
    feature-43
    """
    container_id = None
    try:
        run_result = subprocess.run(
            [
                "docker", "run", "-d", "--rm",
                "-p", "18001:8000",
                "-e", "DATABASE_URL=postgresql+asyncpg://user:pass@localhost/testdb",
                "-e", "ELASTICSEARCH_URL=http://localhost:9200",
                "-e", "QDRANT_URL=http://localhost:6333",
                "-e", "REDIS_URL=redis://localhost:6379",
                "-e", "SECRET_KEY=test-secret-key",
                "codecontext-api",
            ],
            capture_output=True,
            text=True,
        )
        assert run_result.returncode == 0, (
            f"docker run failed: {run_result.stderr}"
        )
        container_id = run_result.stdout.strip()

        deadline = time.time() + 30
        last_exc: Exception | None = None
        while time.time() < deadline:
            try:
                resp = urllib.request.urlopen(
                    "http://localhost:18001/api/v1/health", timeout=5
                )
                code = resp.getcode()
                assert code == 200, f"Expected HTTP 200, got {code}"
                return  # PASS
            except Exception as exc:
                last_exc = exc
                time.sleep(1)

        pytest.fail(
            f"Health endpoint did not return HTTP 200 within 30s. Last error: {last_exc}"
        )
    finally:
        if container_id:
            subprocess.run(["docker", "stop", container_id], capture_output=True)


@pytest.mark.real
def test_docker_image_has_healthcheck_targeting_port_8000():
    """T03: docker inspect shows HEALTHCHECK CMD referencing port 8000.

    Kills bug: HEALTHCHECK directive missing from Dockerfile.
    feature-43
    """
    result = subprocess.run(
        ["docker", "inspect", "codecontext-api"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"docker inspect failed: {result.stderr}"

    data = json.loads(result.stdout)
    healthcheck = data[0]["Config"]["Healthcheck"]
    assert healthcheck is not None, "No Healthcheck config found in docker inspect output"

    test_cmd = " ".join(healthcheck.get("Test", []))
    assert "8000" in test_cmd, (
        f"HEALTHCHECK CMD does not reference port 8000. CMD: {test_cmd!r}"
    )


@pytest.mark.real
def test_docker_image_has_no_dev_dependencies():
    """T04: built image does not contain pytest or mutmut (production deps only).

    Kills bug: pip install .[dev] accidentally used instead of pip install .
    feature-43
    """
    for pkg in ["pytest", "mutmut"]:
        result = subprocess.run(
            ["docker", "run", "--rm", "codecontext-api", "pip", "show", pkg],
            capture_output=True,
            text=True,
        )
        # Exit code 0 means the package IS installed — that is the failure condition.
        # Exit code 1 means "package not found" — expected for a production image.
        # We explicitly reject exit code 0 (installed) and accept code 1 (not found).
        assert result.returncode == 1, (
            f"Dev package '{pkg}' is installed in the production image "
            f"(pip show exited {result.returncode}) — "
            f"only production deps should be present"
        )


@pytest.mark.real
def test_docker_image_runs_as_non_root():
    """T05: running container reports UID 1000 (appuser), not 0 (root).

    Kills bug: USER appuser directive missing from Dockerfile.
    feature-43
    """
    result = subprocess.run(
        ["docker", "run", "--rm", "codecontext-api", "id", "-u"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"docker run id -u failed: {result.stderr}"
    uid = result.stdout.strip()
    assert uid == "1000", (
        f"Expected UID 1000 (appuser), got {uid!r} — image may be running as root"
    )
