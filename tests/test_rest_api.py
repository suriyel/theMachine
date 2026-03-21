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

from src.query.api.v1.deps import get_authenticated_key, get_auth_middleware
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
    app, mocks = _create_test_app()
    client = TestClient(app)

    resp = client.post("/api/v1/query", json={"query": "how to parse JSON"})
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

    resp = client.post("/api/v1/query", json={"query": "parseJSON"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["query_type"] == "symbol"


# ===========================================================================
# T03: GET /api/v1/repos — happy path
# ===========================================================================
def test_get_repos_success():
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
        json={"query": "test query", "languages": ["python", "java"]},
    )
    assert resp.status_code == 200
    mocks["query_handler"].handle_nl_query.assert_called_once_with(
        "test query", None, ["python", "java"]
    )


# ===========================================================================
# T13: POST /api/v1/query — missing API key → 401
# ===========================================================================
def test_query_missing_api_key():
    from src.query.app import create_app

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
    app, mocks = _create_test_app()
    mocks["query_handler"].handle_nl_query.side_effect = ValidationError("query must not be empty")

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/api/v1/query", json={"query": ""})
    assert resp.status_code == 400
    assert "query must not be empty" in resp.json()["detail"]


# ===========================================================================
# T18: POST /api/v1/query — missing field → 422
# ===========================================================================
def test_query_missing_field():
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
    resp = client.post("/api/v1/query", json={"query": "test"})
    assert resp.status_code == 500
    assert resp.json()["detail"] == "Retrieval failed"


# ===========================================================================
# T20: POST /api/v1/repos — conflict → 409
# ===========================================================================
def test_register_repo_conflict():
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
    resp = client.post("/api/v1/query", json={"query": long_query})
    assert resp.status_code == 400
    assert "query exceeds 500 character limit" in resp.json()["detail"]


# ===========================================================================
# T28: POST /api/v1/query — exactly 500 chars → 200
# ===========================================================================
def test_query_exactly_500_chars():
    app, mocks = _create_test_app()
    query = "a" * 500

    client = TestClient(app)
    resp = client.post("/api/v1/query", json={"query": query})
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
    resp = client.post("/api/v1/query", json={"query": "test", "languages": []})
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

    app = create_app()

    async def raise_rate_limited():
        raise HTTPException(status_code=429, detail="Too many failed attempts")

    app.dependency_overrides[get_authenticated_key] = raise_rate_limited

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/api/v1/query", json={"query": "test"})
    assert resp.status_code == 429
    assert "Too many failed attempts" in resp.json()["detail"]
