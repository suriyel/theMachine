# [no integration test] — HTTP layer tested via TestClient with mocked services;
# real service integration tested in Features #13-#16.
# TestClient exercises real ASGI HTTP handling, routing, and serialization.

import os
for _k in ("ALL_PROXY", "all_proxy"):
    os.environ.pop(_k, None)

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.query.api.v1.schemas import HealthResponse, ServiceHealth
from src.query.exceptions import RetrievalError
from src.query.response_models import CodeResult, DocResult, QueryResponse, RulesSection
from src.shared.exceptions import ConflictError, ValidationError
from src.shared.models.api_key import ApiKey


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_api_key(role: str = "admin") -> ApiKey:
    """Create a mock ApiKey with the given role."""
    key = MagicMock(spec=ApiKey)
    key.id = uuid.uuid4()
    key.name = "test-key"
    key.role = role
    key.is_active = True
    key.created_at = None
    key.expires_at = None
    key.key_hash = "fakehash"
    return key


def _make_query_response(query: str = "test", query_type: str = "nl") -> QueryResponse:
    """Build a minimal QueryResponse."""
    return QueryResponse(
        query=query,
        query_type=query_type,
        code_results=[
            CodeResult(
                file_path="src/main.py",
                content="def main(): pass",
                relevance_score=0.95,
            )
        ],
        doc_results=[],
    )


def _mock_session_factory():
    """Create an async context manager mock for session_factory."""
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    result_mock.scalar_one_or_none.return_value = None
    session.execute.return_value = result_mock
    session.commit = AsyncMock()
    session.add = MagicMock()

    @asynccontextmanager
    async def factory():
        yield session

    return factory, session


def _create_test_app(api_key: ApiKey | None = None):
    """Create a test app with mocked services."""
    from src.query.app import create_app
    from src.query.api.v1.deps import get_authenticated_key
    from src.shared.services.auth_middleware import AuthMiddleware

    mock_query_handler = MagicMock()
    mock_query_handler.detect_query_type = MagicMock(return_value="nl")
    mock_query_handler.handle_nl_query = AsyncMock(
        return_value=_make_query_response()
    )
    mock_query_handler.handle_symbol_query = AsyncMock(
        return_value=_make_query_response(query_type="symbol")
    )

    mock_auth_middleware = MagicMock(spec=AuthMiddleware)
    mock_auth_middleware.check_permission = MagicMock(return_value=True)

    mock_api_key_manager = AsyncMock()
    mock_api_key_manager.create_key = AsyncMock()
    mock_api_key_manager.list_keys = AsyncMock(return_value=[])
    mock_api_key_manager.revoke_key = AsyncMock()
    mock_api_key_manager.rotate_key = AsyncMock()

    session_factory, mock_session = _mock_session_factory()

    mock_es = AsyncMock()
    mock_es.health_check = AsyncMock(return_value=True)
    mock_qdrant = AsyncMock()
    mock_qdrant.health_check = AsyncMock(return_value=True)
    mock_redis = AsyncMock()
    mock_redis.health_check = AsyncMock(return_value=True)

    app = create_app(
        query_handler=mock_query_handler,
        auth_middleware=mock_auth_middleware,
        api_key_manager=mock_api_key_manager,
        session_factory=session_factory,
        es_client=mock_es,
        qdrant_client=mock_qdrant,
        redis_client=mock_redis,
    )

    # Override auth dependency
    if api_key is None:
        api_key = _make_api_key("admin")

    app.dependency_overrides[get_authenticated_key] = lambda: api_key

    return app, {
        "query_handler": mock_query_handler,
        "auth_middleware": mock_auth_middleware,
        "api_key_manager": mock_api_key_manager,
        "session_factory": session_factory,
        "session": mock_session,
        "es_client": mock_es,
        "qdrant_client": mock_qdrant,
        "redis_client": mock_redis,
        "api_key": api_key,
    }


# ===========================================================================
# T01: POST /api/v1/query — NL happy path
# ===========================================================================
def test_post_query_nl_success():
    # ST-FUNC-017-001
    app, mocks = _create_test_app()
    client = TestClient(app)

    resp = client.post("/api/v1/query", json={"query": "how to parse JSON", "repo_id": "owner/repo"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["query_type"] == "nl"
    assert len(data["code_results"]) >= 1


# ===========================================================================
# T02: POST /api/v1/query — symbol happy path
# ===========================================================================
def test_post_query_symbol_success():
    app, mocks = _create_test_app()
    mocks["query_handler"].detect_query_type.return_value = "symbol"
    client = TestClient(app)

    resp = client.post("/api/v1/query", json={"query": "parseJSON", "repo_id": "owner/repo"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["query_type"] == "symbol"


# ===========================================================================
# T03: GET /api/v1/repos — happy path
# ===========================================================================
def test_get_repos_success():
    # ST-FUNC-017-002
    app, mocks = _create_test_app()

    # Mock a repo in DB
    mock_repo = MagicMock()
    mock_repo.id = uuid.uuid4()
    mock_repo.name = "owner/repo"
    mock_repo.url = "https://github.com/owner/repo"
    mock_repo.status = "indexed"
    mock_repo.indexed_branch = "main"
    mock_repo.last_indexed_at = None
    mock_repo.created_at = None

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [mock_repo]
    mocks["session"].execute.return_value = result_mock

    client = TestClient(app)
    resp = client.get("/api/v1/repos")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["name"] == "owner/repo"


# ===========================================================================
# T04: GET /api/v1/health — no auth, returns 200
# ===========================================================================
def test_get_health_no_auth():
    # ST-FUNC-017-003
    app, mocks = _create_test_app()
    client = TestClient(app)

    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "code-context-retrieval"
    assert "services" in data


# ===========================================================================
# T05: POST /api/v1/keys — admin creates key
# ===========================================================================
def test_create_key_success():
    # ST-FUNC-017-005
    app, mocks = _create_test_app()
    new_key = _make_api_key("read")
    mocks["api_key_manager"].create_key.return_value = ("ccr_plaintext123", new_key)

    client = TestClient(app)
    resp = client.post("/api/v1/keys", json={"name": "test-key", "role": "read"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["key"] == "ccr_plaintext123"
    assert data["name"] == "test-key"


# ===========================================================================
# T06: GET /api/v1/keys — admin lists keys
# ===========================================================================
def test_list_keys_success():
    # ST-FUNC-017-005
    app, mocks = _create_test_app()
    k = _make_api_key("read")
    mocks["api_key_manager"].list_keys.return_value = [k]

    client = TestClient(app)
    resp = client.get("/api/v1/keys")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1


# ===========================================================================
# T07: POST /api/v1/repos — admin registers repo
# ===========================================================================
def test_register_repo_success():
    # ST-FUNC-017-004
    app, mocks = _create_test_app()

    # Build a mock repo to return from RepoManager.register
    mock_repo = MagicMock()
    mock_repo.id = uuid.uuid4()
    mock_repo.name = "owner/repo"
    mock_repo.url = "https://github.com/owner/repo"
    mock_repo.status = "pending"
    mock_repo.indexed_branch = None
    mock_repo.last_indexed_at = None
    mock_repo.created_at = None

    with patch("src.query.api.v1.endpoints.repos.RepoManager") as MockRM:
        instance = AsyncMock()
        instance.register = AsyncMock(return_value=mock_repo)
        MockRM.return_value = instance

        client = TestClient(app)
        resp = client.post("/api/v1/repos", json={"url": "https://github.com/owner/repo"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending"
    assert data["name"] == "owner/repo"


# ===========================================================================
# T08: POST /api/v1/repos/{id}/reindex — admin triggers reindex
# ===========================================================================
def test_reindex_repo_success():
    app, mocks = _create_test_app()

    repo_id = uuid.uuid4()
    mock_repo = MagicMock()
    mock_repo.id = repo_id
    mock_repo.indexed_branch = "main"
    mock_repo.default_branch = None

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = mock_repo
    mocks["session"].execute.return_value = result_mock

    # Patch IndexJob so we control the id
    job_id = uuid.uuid4()
    with patch("src.query.api.v1.endpoints.repos.IndexJob") as MockJob:
        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.status = "pending"
        MockJob.return_value = mock_job

        client = TestClient(app)
        resp = client.post(f"/api/v1/repos/{repo_id}/reindex")

    assert resp.status_code == 200
    data = resp.json()
    assert data["repo_id"] == str(repo_id)
    assert data["status"] == "pending"
    assert data["job_id"] == str(job_id)


# ===========================================================================
# T09: DELETE /api/v1/keys/{id} — admin revokes key
# ===========================================================================
def test_delete_key_success():
    # ST-FUNC-017-005
    app, mocks = _create_test_app()
    key_id = uuid.uuid4()

    client = TestClient(app)
    resp = client.delete(f"/api/v1/keys/{key_id}")
    assert resp.status_code == 200
    assert resp.json() == {"status": "revoked"}


# ===========================================================================
# T10: POST /api/v1/keys/{id}/rotate — admin rotates key
# ===========================================================================
def test_rotate_key_success():
    # ST-FUNC-017-005
    app, mocks = _create_test_app()
    key_id = uuid.uuid4()
    new_key = _make_api_key("admin")
    mocks["api_key_manager"].rotate_key.return_value = ("new_plaintext", new_key)

    client = TestClient(app)
    resp = client.post(f"/api/v1/keys/{key_id}/rotate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["key"] == "new_plaintext"


# ===========================================================================
# T11: POST /api/v1/query with repo_id
# ===========================================================================
def test_post_query_with_repo_id():
    app, mocks = _create_test_app()
    client = TestClient(app)

    resp = client.post("/api/v1/query", json={"query": "test query", "repo_id": "my-repo"})
    assert resp.status_code == 200
    mocks["query_handler"].handle_nl_query.assert_called_once_with("test query", "my-repo", None)


# ===========================================================================
# T12: POST /api/v1/query with languages
# ===========================================================================
def test_post_query_with_languages():
    app, mocks = _create_test_app()
    client = TestClient(app)

    resp = client.post(
        "/api/v1/query",
        json={"query": "test query", "repo_id": "owner/repo", "languages": ["python", "java"]},
    )
    assert resp.status_code == 200
    mocks["query_handler"].handle_nl_query.assert_called_once_with(
        "test query", "owner/repo", ["python", "java"]
    )


# ===========================================================================
# T13: POST /api/v1/query — missing API key → 401
# ===========================================================================
def test_query_missing_api_key():
    # ST-SEC-017-002
    from src.query.app import create_app
    from src.query.api.v1.deps import get_authenticated_key

    app = create_app()

    # Set up a real-ish auth middleware that raises 401
    mock_auth = MagicMock()
    mock_auth.side_effect = HTTPException(status_code=401, detail="Missing API key")
    app.state.auth_middleware = mock_auth

    # Remove the dependency override so the real dep chain runs
    # We override get_authenticated_key to raise 401
    async def raise_missing():
        raise HTTPException(status_code=401, detail="Missing API key")

    app.dependency_overrides[get_authenticated_key] = raise_missing

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/api/v1/query", json={"query": "test"})
    assert resp.status_code == 401
    assert "Missing API key" in resp.json()["detail"]


# ===========================================================================
# T14: POST /api/v1/query — invalid API key → 401
# ===========================================================================
def test_query_invalid_api_key():
    from src.query.app import create_app
    from src.query.api.v1.deps import get_authenticated_key

    app = create_app()

    async def raise_invalid():
        raise HTTPException(status_code=401, detail="Invalid API key")

    app.dependency_overrides[get_authenticated_key] = raise_invalid

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/api/v1/query", json={"query": "test"})
    assert resp.status_code == 401
    assert "Invalid API key" in resp.json()["detail"]


# ===========================================================================
# T15: POST /api/v1/keys — read-only key → 403
# ===========================================================================
def test_create_key_read_only_forbidden():
    # ST-SEC-017-001
    read_key = _make_api_key("read")
    app, mocks = _create_test_app(api_key=read_key)
    # Use real check_permission from AuthMiddleware
    from src.shared.services.auth_middleware import AuthMiddleware
    real_check = AuthMiddleware.__dict__["check_permission"]
    mocks["auth_middleware"].check_permission = lambda key, action: real_check(mocks["auth_middleware"], key, action)

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/api/v1/keys", json={"name": "test", "role": "read"})
    assert resp.status_code == 403


# ===========================================================================
# T16: POST /api/v1/repos — read-only key → 403
# ===========================================================================
def test_register_repo_read_only_forbidden():
    # ST-SEC-017-001
    read_key = _make_api_key("read")
    app, mocks = _create_test_app(api_key=read_key)
    from src.shared.services.auth_middleware import AuthMiddleware
    real_check = AuthMiddleware.__dict__["check_permission"]
    mocks["auth_middleware"].check_permission = lambda key, action: real_check(mocks["auth_middleware"], key, action)

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/api/v1/repos", json={"url": "https://github.com/o/r"})
    assert resp.status_code == 403


# ===========================================================================
# T17: POST /api/v1/query — empty query → 400
# ===========================================================================
def test_query_empty_body():
    # ST-BNDRY-017-001
    app, mocks = _create_test_app()
    mocks["query_handler"].handle_nl_query.side_effect = ValidationError("query must not be empty")

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/api/v1/query", json={"query": "", "repo_id": "owner/repo"})
    assert resp.status_code == 400
    assert "query must not be empty" in resp.json()["detail"]


# ===========================================================================
# T18: POST /api/v1/query — missing field → 422
# ===========================================================================
def test_query_missing_field():
    # ST-BNDRY-017-001
    app, mocks = _create_test_app()
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.post("/api/v1/query", json={})
    assert resp.status_code == 422


# ===========================================================================
# T19: POST /api/v1/query — RetrievalError → 500
# ===========================================================================
def test_query_retrieval_error():
    app, mocks = _create_test_app()
    mocks["query_handler"].handle_nl_query.side_effect = RetrievalError("all retrieval paths failed")

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/api/v1/query", json={"query": "test", "repo_id": "owner/repo"})
    assert resp.status_code == 500
    assert resp.json()["detail"] == "Retrieval failed"


# ===========================================================================
# T20: POST /api/v1/repos — conflict → 409
# ===========================================================================
def test_register_repo_conflict():
    # ST-BNDRY-017-003
    app, mocks = _create_test_app()

    with patch("src.query.api.v1.endpoints.repos.RepoManager") as MockRM:
        instance = AsyncMock()
        instance.register = AsyncMock(
            side_effect=ConflictError("Repository already registered")
        )
        MockRM.return_value = instance

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/repos", json={"url": "https://github.com/o/r"})

    assert resp.status_code == 409
    assert "already registered" in resp.json()["detail"]


# ===========================================================================
# T21: POST /api/v1/repos/{bad-uuid}/reindex — not found → 404
# ===========================================================================
def test_reindex_repo_not_found():
    # ST-BNDRY-017-002
    app, mocks = _create_test_app()
    bad_id = uuid.uuid4()

    # session returns None for repo lookup
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mocks["session"].execute.return_value = result_mock

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(f"/api/v1/repos/{bad_id}/reindex")
    assert resp.status_code == 404
    assert "Repository not found" in resp.json()["detail"]


# ===========================================================================
# T22: DELETE /api/v1/keys/{bad-uuid} — not found → 404
# ===========================================================================
def test_delete_key_not_found():
    # ST-BNDRY-017-002
    app, mocks = _create_test_app()
    bad_id = uuid.uuid4()
    mocks["api_key_manager"].revoke_key.side_effect = KeyError("not found")

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.delete(f"/api/v1/keys/{bad_id}")
    assert resp.status_code == 404
    assert "API key not found" in resp.json()["detail"]


# ===========================================================================
# T23: POST /api/v1/keys/{id}/rotate — inactive → 400
# ===========================================================================
def test_rotate_inactive_key():
    app, mocks = _create_test_app()
    key_id = uuid.uuid4()
    mocks["api_key_manager"].rotate_key.side_effect = ValueError(
        "Cannot rotate an inactive key"
    )

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(f"/api/v1/keys/{key_id}/rotate")
    assert resp.status_code == 400
    assert "Cannot rotate an inactive key" in resp.json()["detail"]


# ===========================================================================
# T24: POST /api/v1/repos/{id}/reindex — read-only → 403
# ===========================================================================
def test_reindex_read_only_forbidden():
    # ST-SEC-017-001
    read_key = _make_api_key("read")
    app, mocks = _create_test_app(api_key=read_key)
    from src.shared.services.auth_middleware import AuthMiddleware
    real_check = AuthMiddleware.__dict__["check_permission"]
    mocks["auth_middleware"].check_permission = lambda key, action: real_check(mocks["auth_middleware"], key, action)

    repo_id = uuid.uuid4()
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(f"/api/v1/repos/{repo_id}/reindex")
    assert resp.status_code == 403


# ===========================================================================
# T25: POST /api/v1/keys — invalid role → 400
# ===========================================================================
def test_create_key_invalid_role():
    app, mocks = _create_test_app()
    mocks["api_key_manager"].create_key.side_effect = ValueError(
        "role must be 'read' or 'admin'"
    )

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/api/v1/keys", json={"name": "test", "role": "superadmin"})
    assert resp.status_code == 400
    assert "role must be 'read' or 'admin'" in resp.json()["detail"]


# ===========================================================================
# T26: POST /api/v1/keys/{bad-uuid}/rotate — not found → 404
# ===========================================================================
def test_rotate_key_not_found():
    app, mocks = _create_test_app()
    bad_id = uuid.uuid4()
    mocks["api_key_manager"].rotate_key.side_effect = KeyError("not found")

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(f"/api/v1/keys/{bad_id}/rotate")
    assert resp.status_code == 404
    assert "API key not found" in resp.json()["detail"]


# ===========================================================================
# T27: POST /api/v1/query — 501-char query → 400
# ===========================================================================
def test_query_exceeds_500_chars():
    app, mocks = _create_test_app()
    long_query = "a" * 501
    mocks["query_handler"].handle_nl_query.side_effect = ValidationError(
        "query exceeds 500 character limit"
    )

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/api/v1/query", json={"query": long_query, "repo_id": "owner/repo"})
    assert resp.status_code == 400
    assert "query exceeds 500 character limit" in resp.json()["detail"]


# ===========================================================================
# T28: POST /api/v1/query — exactly 500 chars → 200
# ===========================================================================
def test_query_exactly_500_chars():
    app, mocks = _create_test_app()
    query = "a" * 500

    client = TestClient(app)
    resp = client.post("/api/v1/query", json={"query": query, "repo_id": "owner/repo"})
    assert resp.status_code == 200


# ===========================================================================
# T29: POST /api/v1/keys — whitespace name → 400
# ===========================================================================
def test_create_key_whitespace_name():
    app, mocks = _create_test_app()
    mocks["api_key_manager"].create_key.side_effect = ValueError(
        "name must not be empty"
    )

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/api/v1/keys", json={"name": "   ", "role": "read"})
    assert resp.status_code == 400
    assert "name must not be empty" in resp.json()["detail"]


# ===========================================================================
# T30: POST /api/v1/query — empty languages list → 200
# ===========================================================================
def test_query_empty_languages_list():
    app, mocks = _create_test_app()

    client = TestClient(app)
    resp = client.post("/api/v1/query", json={"query": "test", "repo_id": "owner/repo", "languages": []})
    assert resp.status_code == 200


# ===========================================================================
# T31: GET /api/v1/health — ES down → degraded
# ===========================================================================
def test_health_degraded():
    app, mocks = _create_test_app()
    mocks["es_client"].health_check.return_value = False

    client = TestClient(app)
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "degraded"
    assert data["services"]["elasticsearch"] == "down"


# ===========================================================================
# T32: GET /api/v1/health — all up → healthy
# ===========================================================================
def test_health_all_up():
    app, mocks = _create_test_app()

    # pg health check via session_factory — need to make it work
    # The health endpoint tries session_factory() and executes SELECT 1
    # Our mock session_factory already yields a mock session that doesn't raise

    client = TestClient(app)
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["services"]["elasticsearch"] == "up"
    assert data["services"]["qdrant"] == "up"
    assert data["services"]["redis"] == "up"
    assert data["services"]["postgresql"] == "up"


# ===========================================================================
# T33: Rate limit enforced → 429
# ===========================================================================
def test_rate_limit_enforced():
    from src.query.app import create_app
    from src.query.api.v1.deps import get_authenticated_key

    app = create_app()

    async def raise_rate_limited():
        raise HTTPException(status_code=429, detail="Too many failed attempts")

    app.dependency_overrides[get_authenticated_key] = raise_rate_limited

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/api/v1/query", json={"query": "test"})
    assert resp.status_code == 429
    assert "Too many failed attempts" in resp.json()["detail"]


# ===========================================================================
# DEF-001 Regression Tests (R01-R05): lifespan connect/close
# ===========================================================================
# [unit] — mocked clients; verifies lifespan calls connect()/close() and that
# health endpoint reflects accurate status after clients are connected.

def _make_lifespan_client_mocks():
    """Create ES/Qdrant/Redis mocks with explicit connect/close tracking."""
    es = AsyncMock()
    es.connect = AsyncMock()
    es.close = AsyncMock()
    es.health_check = AsyncMock(return_value=True)

    qdrant = AsyncMock()
    qdrant.connect = AsyncMock()
    qdrant.close = AsyncMock()
    qdrant.health_check = AsyncMock(return_value=True)

    redis = AsyncMock()
    redis.connect = AsyncMock()
    redis.close = AsyncMock()
    redis.health_check = AsyncMock(return_value=True)

    return es, qdrant, redis


def test_lifespan_connects_clients_health_reports_healthy():
    # ST-FUNC-017-006
    """R01: lifespan calls connect() on each client; health returns 'healthy'.

    Kills DEF-001: clients never connected so health_check always returned False.
    Without lifespan, connect() is never called so _client stays None and
    health_check() returns False — health endpoint always reports 'degraded'.
    """
    from src.query.app import create_app

    es, qdrant, redis = _make_lifespan_client_mocks()
    session_factory, _ = _mock_session_factory()

    app = create_app(
        es_client=es,
        qdrant_client=qdrant,
        redis_client=redis,
        session_factory=session_factory,
    )

    with TestClient(app) as client:
        # connect() must be called during lifespan startup
        es.connect.assert_called_once()
        qdrant.connect.assert_called_once()
        redis.connect.assert_called_once()

        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy", (
            f"Expected 'healthy' after connect(), got: {data['status']!r}. "
            f"Services: {data.get('services')}"
        )
        assert data["services"]["elasticsearch"] == "up"
        assert data["services"]["qdrant"] == "up"
        assert data["services"]["redis"] == "up"


def test_lifespan_none_client_skipped():
    # ST-BNDRY-017-004
    """R02: None client passed to create_app() skips connect(); no AttributeError.

    Kills bug: AttributeError if lifespan tries to call connect() on None.
    """
    from src.query.app import create_app

    qdrant = AsyncMock()
    qdrant.connect = AsyncMock()
    qdrant.close = AsyncMock()
    qdrant.health_check = AsyncMock(return_value=True)

    redis = AsyncMock()
    redis.connect = AsyncMock()
    redis.close = AsyncMock()
    redis.health_check = AsyncMock(return_value=True)

    session_factory, _ = _mock_session_factory()

    app = create_app(
        es_client=None,  # deliberately None
        qdrant_client=qdrant,
        redis_client=redis,
        session_factory=session_factory,
    )

    # Should not raise; lifespan must guard against None clients
    with TestClient(app) as client:
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        # No ES client → ES is "down"; no AttributeError
        assert data["services"]["elasticsearch"] == "down", (
            f"Expected elasticsearch='down' when es_client=None, got {data['services']['elasticsearch']!r}"
        )
        # Other services still up
        assert data["services"]["qdrant"] == "up"
        assert data["services"]["redis"] == "up"
        assert data["status"] == "degraded"


def test_lifespan_connect_error_propagates():
    # ST-BNDRY-017-005
    """R03: connect() raising an exception propagates out of lifespan (startup fails).

    Kills bug: connect() error silently swallowed, leaving stale None _client.
    """
    from src.query.app import create_app

    es = AsyncMock()
    es.connect = AsyncMock(side_effect=ConnectionError("ES unreachable"))
    es.close = AsyncMock()

    session_factory, _ = _mock_session_factory()

    app = create_app(
        es_client=es,
        session_factory=session_factory,
    )

    with pytest.raises((ConnectionError, Exception)):
        # TestClient.__enter__ triggers lifespan startup; connect() raises
        TestClient(app).__enter__()


def test_lifespan_close_called_on_shutdown():
    # ST-FUNC-017-007
    """R04: close() called on each non-None client when app shuts down.

    Kills bug: lifespan exit path missing — resource leak on shutdown.
    """
    from src.query.app import create_app

    es, qdrant, redis = _make_lifespan_client_mocks()
    session_factory, _ = _mock_session_factory()

    app = create_app(
        es_client=es,
        qdrant_client=qdrant,
        redis_client=redis,
        session_factory=session_factory,
    )

    with TestClient(app):
        pass  # enter and exit lifespan

    # After context manager exits, close() must have been called on each client
    es.close.assert_called_once()
    qdrant.close.assert_called_once()
    redis.close.assert_called_once()


def test_lifespan_degraded_when_service_health_check_fails():
    # ST-FUNC-017-008
    """R05: health returns 'degraded' when a service health_check returns False.

    Kills DEF-001 variant: before fix, _client was None so health_check always
    returned False — this test confirms that after fix, degraded is a real signal
    (not just the permanent state caused by an unconnected client).
    """
    from src.query.app import create_app

    es, qdrant, redis = _make_lifespan_client_mocks()
    # ES reports itself unhealthy (service is up but not healthy)
    es.health_check = AsyncMock(return_value=False)

    session_factory, _ = _mock_session_factory()

    app = create_app(
        es_client=es,
        qdrant_client=qdrant,
        redis_client=redis,
        session_factory=session_factory,
    )

    with TestClient(app) as client:
        # connect() still called (client is not None)
        es.connect.assert_called_once()

        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded", (
            f"Expected 'degraded' when ES health_check returns False, got: {data['status']!r}"
        )
        assert data["services"]["elasticsearch"] == "down"
        assert data["services"]["qdrant"] == "up"
        assert data["services"]["redis"] == "up"


def test_lifespan_close_error_isolated_remaining_clients_still_closed():
    """R06: if es_client.close() raises, qdrant and redis close() still called.

    Kills bug: sequential close() without error isolation — one failure skips rest.
    """
    from src.query.app import create_app

    es, qdrant, redis = _make_lifespan_client_mocks()
    es.close = AsyncMock(side_effect=RuntimeError("ES close failed"))  # ES close raises
    session_factory, _ = _mock_session_factory()

    app = create_app(
        es_client=es,
        qdrant_client=qdrant,
        redis_client=redis,
        session_factory=session_factory,
    )

    # Exit must not raise even when es_client.close() raises
    with TestClient(app):
        pass

    # All three close() were attempted despite ES raising
    es.close.assert_called_once()
    qdrant.close.assert_called_once()
    redis.close.assert_called_once()


# ===========================================================================
# Coverage gap tests — query cache, health exception paths, list_branches,
# ValidationError on register_repo, reindex cache invalidation, deps line 21
# ===========================================================================

def test_post_query_cache_hit():
    """Cache hit: query_cache.get returns a cached response — skips handler."""
    app, mocks = _create_test_app()

    cached_response = _make_query_response("cached")
    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(return_value=cached_response)
    mock_cache.set = AsyncMock()
    app.state.query_cache = mock_cache

    client = TestClient(app)
    resp = client.post("/api/v1/query", json={"query": "cached query", "repo_id": "owner/repo"})
    assert resp.status_code == 200
    # Handler was not called because we hit the cache
    mocks["query_handler"].handle_nl_query.assert_not_called()


def test_post_query_cache_miss_stores_result():
    """Cache miss: query_cache.set called after handler executes."""
    app, mocks = _create_test_app()

    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(return_value=None)
    mock_cache.set = AsyncMock()
    app.state.query_cache = mock_cache

    client = TestClient(app)
    resp = client.post("/api/v1/query", json={"query": "new query", "repo_id": "owner/repo"})
    assert resp.status_code == 200
    mock_cache.set.assert_called_once()


def test_register_repo_validation_error():
    """POST /api/v1/repos — ValidationError from RepoManager → 400."""
    app, mocks = _create_test_app()

    with patch("src.query.api.v1.endpoints.repos.RepoManager") as MockRM:
        instance = AsyncMock()
        instance.register = AsyncMock(side_effect=ValidationError("invalid URL"))
        MockRM.return_value = instance

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/api/v1/repos", json={"url": "not-a-url"})

    assert resp.status_code == 400
    assert "invalid URL" in resp.json()["detail"]


def test_reindex_repo_with_cache_invalidation():
    """POST /api/v1/repos/{id}/reindex — query_cache.invalidate_repo called when cache present."""
    app, mocks = _create_test_app()

    repo_id = uuid.uuid4()
    mock_repo = MagicMock()
    mock_repo.id = repo_id
    mock_repo.name = "owner/repo"
    mock_repo.indexed_branch = "main"
    mock_repo.default_branch = None

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = mock_repo
    mocks["session"].execute.return_value = result_mock

    mock_cache = AsyncMock()
    mock_cache.invalidate_repo = AsyncMock()
    app.state.query_cache = mock_cache

    job_id = uuid.uuid4()
    with patch("src.query.api.v1.endpoints.repos.IndexJob") as MockJob:
        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.status = "pending"
        MockJob.return_value = mock_job

        client = TestClient(app)
        resp = client.post(f"/api/v1/repos/{repo_id}/reindex")

    assert resp.status_code == 200
    mock_cache.invalidate_repo.assert_called_once_with("owner/repo")


def test_list_branches_success():
    """GET /api/v1/repos/{id}/branches — returns branch list."""
    app, mocks = _create_test_app()

    repo_id = uuid.uuid4()
    mock_repo = MagicMock()
    mock_repo.id = repo_id
    mock_repo.clone_path = "/tmp/repo"
    mock_repo.default_branch = "main"

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = mock_repo
    mocks["session"].execute.return_value = result_mock

    with patch("src.query.api.v1.endpoints.repos.GitCloner") as MockGC:
        instance = MagicMock()
        instance.list_remote_branches.return_value = ["main", "dev"]
        MockGC.return_value = instance

        client = TestClient(app)
        resp = client.get(f"/api/v1/repos/{repo_id}/branches")

    assert resp.status_code == 200
    data = resp.json()
    assert data["default_branch"] == "main"
    assert "main" in data["branches"]


def test_list_branches_repo_not_found():
    """GET /api/v1/repos/{id}/branches — repo not found → 404."""
    app, mocks = _create_test_app()

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mocks["session"].execute.return_value = result_mock

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get(f"/api/v1/repos/{uuid.uuid4()}/branches")
    assert resp.status_code == 404


def test_list_branches_not_cloned():
    """GET /api/v1/repos/{id}/branches — clone_path is None → 409."""
    app, mocks = _create_test_app()

    repo_id = uuid.uuid4()
    mock_repo = MagicMock()
    mock_repo.id = repo_id
    mock_repo.clone_path = None

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = mock_repo
    mocks["session"].execute.return_value = result_mock

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get(f"/api/v1/repos/{repo_id}/branches")
    assert resp.status_code == 409
    assert "not been cloned" in resp.json()["detail"]


def test_list_branches_clone_error():
    """GET /api/v1/repos/{id}/branches — GitCloner raises CloneError → 500."""
    from src.shared.exceptions import CloneError

    app, mocks = _create_test_app()

    repo_id = uuid.uuid4()
    mock_repo = MagicMock()
    mock_repo.id = repo_id
    mock_repo.clone_path = "/tmp/repo"
    mock_repo.default_branch = "main"

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = mock_repo
    mocks["session"].execute.return_value = result_mock

    with patch("src.query.api.v1.endpoints.repos.GitCloner") as MockGC:
        instance = MagicMock()
        instance.list_remote_branches.side_effect = CloneError("failed")
        MockGC.return_value = instance

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get(f"/api/v1/repos/{repo_id}/branches")

    assert resp.status_code == 500
    assert "Failed to list branches" in resp.json()["detail"]


def test_health_es_exception():
    """GET /api/v1/health — ES health_check raises exception → es is 'down'."""
    app, mocks = _create_test_app()
    mocks["es_client"].health_check.side_effect = Exception("connection refused")

    client = TestClient(app)
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["services"]["elasticsearch"] == "down"
    assert data["status"] == "degraded"


def test_health_qdrant_exception():
    """GET /api/v1/health — Qdrant health_check raises exception → qdrant is 'down'."""
    app, mocks = _create_test_app()
    mocks["qdrant_client"].health_check.side_effect = Exception("qdrant unreachable")

    client = TestClient(app)
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["services"]["qdrant"] == "down"


def test_health_redis_exception():
    """GET /api/v1/health — Redis health_check raises exception → redis is 'down'."""
    app, mocks = _create_test_app()
    mocks["redis_client"].health_check.side_effect = Exception("redis unreachable")

    client = TestClient(app)
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["services"]["redis"] == "down"


def test_health_pg_exception():
    """GET /api/v1/health — pg session raises → postgresql is 'down'."""
    from contextlib import asynccontextmanager

    app, mocks = _create_test_app()

    @asynccontextmanager
    async def failing_factory():
        raise Exception("pg connection failed")
        yield  # noqa: unreachable

    app.state.session_factory = failing_factory

    client = TestClient(app)
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["services"]["postgresql"] == "down"


def test_lifespan_all_none_clients():
    """app.py lifespan False branches: all clients None → connect/close never called."""
    from src.query.app import create_app

    session_factory, _ = _mock_session_factory()
    app = create_app(
        es_client=None,
        qdrant_client=None,
        redis_client=None,
        session_factory=session_factory,
    )

    with TestClient(app) as client:
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        # All services down since no clients provided
        assert data["services"]["elasticsearch"] == "down"
        assert data["services"]["qdrant"] == "down"
        assert data["services"]["redis"] == "down"


def test_health_qdrant_returns_false():
    """health.py branch: qdrant health_check returns False → qdrant 'down'."""
    app, mocks = _create_test_app()
    mocks["qdrant_client"].health_check.return_value = False

    client = TestClient(app)
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["services"]["qdrant"] == "down"


def test_health_redis_returns_false():
    """health.py branch: redis health_check returns False → redis 'down'."""
    app, mocks = _create_test_app()
    mocks["redis_client"].health_check.return_value = False

    client = TestClient(app)
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["services"]["redis"] == "down"


def test_health_no_clients():
    """health.py False branches: no es/qdrant/redis in app state → all down."""
    from src.query.app import create_app

    session_factory, _ = _mock_session_factory()
    app = create_app(session_factory=session_factory)

    client = TestClient(app)
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["services"]["elasticsearch"] == "down"
    assert data["services"]["qdrant"] == "down"
    assert data["services"]["redis"] == "down"


def test_require_permission_calls_check_with_correct_action():
    """deps.py: require_permission calls check_permission with the actual action string."""
    from src.query.api.v1.deps import require_permission
    from unittest.mock import MagicMock, call

    key = _make_api_key("admin")
    auth = MagicMock()
    auth.check_permission = MagicMock(return_value=True)

    require_permission(key, "query", auth)
    auth.check_permission.assert_called_once_with(key, "query")

    require_permission(key, "list_repos", auth)
    assert auth.check_permission.call_args_list[1] == call(key, "list_repos")


def test_require_permission_forbidden_message():
    """deps.py: require_permission raises 403 with specific detail message."""
    from src.query.api.v1.deps import require_permission
    from fastapi import HTTPException

    key = _make_api_key("read")
    auth = MagicMock()
    auth.check_permission = MagicMock(return_value=False)

    with pytest.raises(HTTPException) as exc_info:
        require_permission(key, "admin_action", auth)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Insufficient permissions"


def test_create_app_stores_query_cache_in_state():
    """app.py: create_app stores the query_cache parameter in app.state."""
    from src.query.app import create_app

    mock_cache = MagicMock()
    app = create_app(query_cache=mock_cache)
    assert app.state.query_cache is mock_cache


def test_create_app_stores_git_cloner_in_state():
    """app.py: create_app stores the git_cloner parameter in app.state."""
    from src.query.app import create_app

    mock_cloner = MagicMock()
    app = create_app(git_cloner=mock_cloner)
    assert app.state.git_cloner is mock_cloner


def test_create_app_title_and_version():
    """app.py: create_app sets the correct title and version in FastAPI."""
    from src.query.app import create_app

    app = create_app()
    assert app.title == "Code Context Retrieval"
    assert app.version == "0.1.0"


def test_post_query_uses_cache_from_app_state():
    """query.py: query endpoint uses query_cache passed to create_app."""
    from src.query.app import create_app
    from src.query.api.v1.deps import get_authenticated_key

    mock_qh = MagicMock()
    mock_qh.detect_query_type = MagicMock(return_value="nl")
    mock_qh.handle_nl_query = AsyncMock(return_value=_make_query_response())

    mock_auth = MagicMock()
    mock_auth.check_permission = MagicMock(return_value=True)

    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(return_value=None)
    mock_cache.set = AsyncMock()

    session_factory, _ = _mock_session_factory()

    app = create_app(
        query_handler=mock_qh,
        auth_middleware=mock_auth,
        session_factory=session_factory,
        query_cache=mock_cache,
    )
    api_key = _make_api_key("admin")
    app.dependency_overrides[get_authenticated_key] = lambda: api_key

    client = TestClient(app)
    resp = client.post("/api/v1/query", json={"query": "test", "repo_id": "owner/repo"})
    assert resp.status_code == 200
    mock_cache.get.assert_called_once()
    mock_cache.set.assert_called_once()


def test_get_authenticated_key_calls_middleware():
    """deps.py line 21: get_authenticated_key calls auth_middleware(request)."""
    from src.query.app import create_app
    from src.query.api.v1.deps import get_auth_middleware
    from src.shared.services.auth_middleware import AuthMiddleware

    # Create app without overriding get_authenticated_key
    mock_query_handler = MagicMock()
    mock_query_handler.detect_query_type = MagicMock(return_value="nl")
    mock_query_handler.handle_nl_query = AsyncMock(return_value=_make_query_response())

    admin_key = _make_api_key("admin")
    mock_auth_middleware = AsyncMock(spec=AuthMiddleware)
    mock_auth_middleware.return_value = admin_key
    mock_auth_middleware.check_permission = MagicMock(return_value=True)

    mock_api_key_manager = AsyncMock()
    mock_api_key_manager.create_key = AsyncMock()
    mock_api_key_manager.list_keys = AsyncMock(return_value=[])

    session_factory, _ = _mock_session_factory()

    app = create_app(
        query_handler=mock_query_handler,
        auth_middleware=mock_auth_middleware,
        api_key_manager=mock_api_key_manager,
        session_factory=session_factory,
    )
    # Do NOT override get_authenticated_key — let the real dep chain run
    # Override get_auth_middleware to return our mock directly
    app.dependency_overrides[get_auth_middleware] = lambda: mock_auth_middleware

    client = TestClient(app)
    resp = client.post("/api/v1/query", json={"query": "test", "repo_id": "owner/repo"})
    assert resp.status_code == 200
    mock_auth_middleware.assert_called_once()


def test_create_app_mounts_static_files_when_dir_exists(tmp_path, monkeypatch):
    """app.py: create_app mounts /static with StaticFiles when static dir exists."""
    import os
    from src.query.app import create_app

    # Create a real temp static dir so os.path.isdir returns True
    static_dir = tmp_path / "static"
    static_dir.mkdir()

    # Patch os.path.dirname to return tmp_path so app.py builds path to our static dir
    original_dirname = os.path.dirname

    def fake_dirname(path):
        if "app.py" in path:
            return str(tmp_path)
        return original_dirname(path)

    monkeypatch.setattr("src.query.app.os.path.dirname", fake_dirname)

    app = create_app()
    # If static files mounted correctly, the route "/static" should be in the routes
    route_paths = [getattr(r, "path", None) for r in app.routes]
    assert "/static" in route_paths


def test_create_app_static_mount_uses_correct_directory(tmp_path, monkeypatch):
    """app.py: create_app mounts StaticFiles with the correct directory path."""
    import os
    from starlette.staticfiles import StaticFiles
    from src.query.app import create_app

    static_dir = tmp_path / "static"
    static_dir.mkdir()

    original_dirname = os.path.dirname

    def fake_dirname(path):
        if "app.py" in path:
            return str(tmp_path)
        return original_dirname(path)

    monkeypatch.setattr("src.query.app.os.path.dirname", fake_dirname)

    app = create_app()

    # Find the mounted static route and verify its directory and name
    for route in app.routes:
        if getattr(route, "path", None) == "/static":
            assert isinstance(route.app, StaticFiles)
            assert route.name == "static"
            break
    else:
        pytest.fail("No /static route found")

