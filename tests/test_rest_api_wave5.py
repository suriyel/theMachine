"""Wave 5 REST API tests — repo_id required enforcement (FR-015, Wave 5).

Tests T09-T24 from the Feature #17 Test Inventory that specifically verify
the Wave 5 behavior: repo_id is a required field (not Optional) in POST /query.

These tests are expected to FAIL before the implementation change
(QueryRequest.repo_id: str | None = None → repo_id: str).
"""

# [unit] — ASGI TestClient with mocked services; no real DB/ES/Qdrant needed
# Security: injection/auth tests in T12-T13 cover auth enforcement

import os
for _k in ("ALL_PROXY", "all_proxy"):
    os.environ.pop(_k, None)

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.query.exceptions import RetrievalError
from src.query.response_models import CodeResult, DocResult, QueryResponse, RulesSection
from src.shared.exceptions import ConflictError, ValidationError
from src.shared.models.api_key import ApiKey


# ---------------------------------------------------------------------------
# Helpers (duplicated here for test independence)
# ---------------------------------------------------------------------------

def _make_api_key(role: str = "admin") -> ApiKey:
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
    from src.query.app import create_app
    from src.query.api.v1.deps import get_authenticated_key
    from src.shared.services.auth_middleware import AuthMiddleware

    mock_query_handler = MagicMock()
    mock_query_handler.detect_query_type = MagicMock(return_value="nl")
    mock_query_handler.handle_nl_query = AsyncMock(return_value=_make_query_response())
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
# Wave 5 T09: POST /api/v1/query without repo_id → 422 (repo_id required)
# Kills bug: repo_id defaults to None instead of being required
# ===========================================================================
def test_query_without_repo_id_returns_422():
    """POST /query with query present but repo_id absent → 422 (Wave 5 required)."""
    # ST-BNDRY-017-006
    app, mocks = _create_test_app()
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.post("/api/v1/query", json={"query": "find auth handler"})

    assert resp.status_code == 422, (
        f"Expected 422 (repo_id required), got {resp.status_code}. "
        f"Response: {resp.json()}"
    )
    data = resp.json()
    # FastAPI returns detail as a list of validation errors
    assert "detail" in data
    # The error must reference repo_id field
    error_locs = [tuple(e.get("loc", [])) for e in data["detail"]]
    assert any("repo_id" in loc for loc in error_locs), (
        f"Expected repo_id in error locations, got: {error_locs}"
    )


# ===========================================================================
# Wave 5 T09b: POST /api/v1/query with repo_id=null → 422
# Kills bug: null accepted as None (Optional) instead of rejected
# ===========================================================================
def test_query_null_repo_id_returns_422():
    """POST /query with repo_id explicitly set to null → 422 (str, not str|None)."""
    # ST-BNDRY-017-007
    app, mocks = _create_test_app()
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.post("/api/v1/query", json={"query": "find auth handler", "repo_id": None})

    assert resp.status_code == 422, (
        f"Expected 422 (repo_id must be str, not null), got {resp.status_code}. "
        f"Response: {resp.json()}"
    )


# ===========================================================================
# Wave 5 T03: POST /api/v1/query with repo_id="owner/repo@branch" passes raw value
# Verifies the @branch suffix is forwarded to the handler (not parsed at API layer)
# ===========================================================================
def test_query_with_branch_suffix_passes_raw_repo_id_to_handler():
    """POST /query with repo_id='owner/repo@main' → handler receives full string."""
    app, mocks = _create_test_app()
    client = TestClient(app)

    resp = client.post(
        "/api/v1/query",
        json={"query": "find auth handler", "repo_id": "owner/repo@main"},
    )

    assert resp.status_code == 200, f"Unexpected error: {resp.json()}"
    # The full repo_id string (including @branch) must be passed to the handler
    mocks["query_handler"].handle_nl_query.assert_called_once_with(
        "find auth handler", "owner/repo@main", None
    )


# ===========================================================================
# Wave 5 T18: POST /api/v1/query with repo_id="owner/repo@" (empty branch)
# Verifies empty branch suffix is forwarded intact (handler handles _parse_repo)
# ===========================================================================
def test_query_with_empty_branch_suffix_passes_to_handler():
    """POST /query with repo_id='owner/repo@' (empty branch) → handler receives full string."""
    app, mocks = _create_test_app()
    client = TestClient(app)

    resp = client.post(
        "/api/v1/query",
        json={"query": "find auth handler", "repo_id": "owner/repo@"},
    )

    assert resp.status_code == 200, f"Unexpected error: {resp.json()}"
    mocks["query_handler"].handle_nl_query.assert_called_once_with(
        "find auth handler", "owner/repo@", None
    )


# ===========================================================================
# Wave 5 T21: Cache hit short-circuits handler dispatch
# Kills bug: cache hit not short-circuiting pipeline
# ===========================================================================
def test_query_cache_hit_skips_handler():
    """POST /query when cache returns a hit → handler NOT called."""
    app, mocks = _create_test_app()

    cached_response = _make_query_response("cached query")
    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(return_value=cached_response)
    mock_cache.set = AsyncMock()
    app.state.query_cache = mock_cache

    client = TestClient(app)
    resp = client.post(
        "/api/v1/query",
        json={"query": "cached query", "repo_id": "owner/repo"},
    )

    assert resp.status_code == 200
    # Handler must NOT be called when cache returns a hit
    mocks["query_handler"].handle_nl_query.assert_not_called()
    mocks["query_handler"].handle_symbol_query.assert_not_called()
    # Cached response content is returned
    assert resp.json()["query"] == "cached query"


# ===========================================================================
# Wave 5 T22: POST /repos/{id}/reindex with no branch info → job.branch="main"
# Kills bug: branch defaults not applied correctly
# ===========================================================================
def test_reindex_no_branch_defaults_to_main():
    """POST /repos/{id}/reindex, repo has no indexed_branch or default_branch → job.branch='main'."""
    app, mocks = _create_test_app()
    repo_id = uuid.uuid4()

    mock_repo = MagicMock()
    mock_repo.id = repo_id
    mock_repo.name = "owner/repo"
    mock_repo.indexed_branch = None
    mock_repo.default_branch = None  # neither branch set

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = mock_repo
    mocks["session"].execute.return_value = result_mock

    captured_jobs = []

    def capture_add(obj):
        captured_jobs.append(obj)

    mocks["session"].add.side_effect = capture_add

    job_id = uuid.uuid4()
    with patch("src.query.api.v1.endpoints.repos.IndexJob") as MockJob:
        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.status = "pending"
        # Capture the branch argument passed to IndexJob constructor
        def create_job(**kwargs):
            mock_job._created_with = kwargs
            return mock_job
        MockJob.side_effect = lambda **kw: (mock_job.__setattr__("_created_with", kw) or mock_job)
        # Simpler: just inspect the call args
        MockJob.return_value = mock_job

        client = TestClient(app)
        resp = client.post(f"/api/v1/repos/{repo_id}/reindex")

    assert resp.status_code == 200
    # IndexJob must be created with branch="main" (the fallback)
    call_kwargs = MockJob.call_args[1] if MockJob.call_args else MockJob.call_args
    # Check kwargs
    if call_kwargs is None:
        call_kwargs = {}
    # The IndexJob constructor must have been called with branch="main"
    actual_call = MockJob.call_args
    assert actual_call is not None, "IndexJob was not instantiated"
    # Check branch argument (may be positional or keyword)
    call_args, call_kw = actual_call
    branch_val = call_kw.get("branch") or (call_args[1] if len(call_args) > 1 else None)
    assert branch_val == "main", (
        f"Expected branch='main' (fallback), got branch={branch_val!r}"
    )


# ===========================================================================
# Wave 5 T19: GET /api/v1/health with all clients=None → 200, all "down"
# Kills bug: None client not handled → AttributeError
# ===========================================================================
def test_health_all_clients_none_returns_degraded():
    """GET /health with all external clients absent → 200 with all services 'down'."""
    from src.query.app import create_app

    # Create an app with no external clients at all
    session_factory, _ = _mock_session_factory()
    app = create_app(
        es_client=None,
        qdrant_client=None,
        redis_client=None,
        session_factory=session_factory,
    )

    client = TestClient(app)
    resp = client.get("/api/v1/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "degraded", (
        f"Expected 'degraded' when all clients=None, got: {data['status']!r}"
    )
    services = data["services"]
    assert services["elasticsearch"] == "down"
    assert services["qdrant"] == "down"
    assert services["redis"] == "down"


# ===========================================================================
# Wave 5 T20: GET /api/v1/health — ES raises exception → still 200, ES "down"
# Kills bug: exception in one check crashes entire health endpoint
# ===========================================================================
def test_health_one_service_exception_still_returns_200():
    """GET /health when ES.health_check raises → 200, elasticsearch='down', others 'up'."""
    app, mocks = _create_test_app()
    mocks["es_client"].health_check.side_effect = ConnectionError("ES unreachable")

    client = TestClient(app)
    resp = client.get("/api/v1/health")

    assert resp.status_code == 200, (
        f"Health endpoint must not propagate exceptions, got {resp.status_code}"
    )
    data = resp.json()
    assert data["services"]["elasticsearch"] == "down"
    assert data["services"]["qdrant"] == "up"
    assert data["services"]["redis"] == "up"
    assert data["status"] == "degraded"


# ===========================================================================
# Wave 5: Schema-level validation test
# Verifies QueryRequest rejects missing repo_id at the Pydantic model level
# (unit — no ASGI needed)
# ===========================================================================
def test_query_request_schema_requires_repo_id():
    """QueryRequest must reject construction without repo_id (Wave 5 required field)."""
    # ST-BNDRY-017-006
    from pydantic import ValidationError as PydanticValidationError
    from src.query.api.v1.schemas import QueryRequest

    # Should succeed with repo_id provided
    req = QueryRequest(query="test", repo_id="owner/repo")
    assert req.repo_id == "owner/repo"

    # Must raise when repo_id is absent
    with pytest.raises(PydanticValidationError) as exc_info:
        QueryRequest(query="test")  # repo_id missing

    errors = exc_info.value.errors()
    error_fields = [e["loc"] for e in errors]
    assert any("repo_id" in loc for loc in error_fields), (
        f"Expected repo_id error, got: {error_fields}"
    )


# ===========================================================================
# Wave 5: QueryRequest rejects None (str, not Optional[str])
# ===========================================================================
def test_query_request_schema_rejects_none_repo_id():
    """QueryRequest must reject repo_id=None (field is str, not str|None)."""
    # ST-BNDRY-017-007
    from pydantic import ValidationError as PydanticValidationError
    from src.query.api.v1.schemas import QueryRequest

    with pytest.raises(PydanticValidationError) as exc_info:
        QueryRequest(query="test", repo_id=None)

    errors = exc_info.value.errors()
    error_fields = [e["loc"] for e in errors]
    assert any("repo_id" in loc for loc in error_fields), (
        f"Expected repo_id validation error, got: {error_fields}"
    )


# ===========================================================================
# Wave 5: read-role key without repo access → 403
# Kills bug: ACL check (check_repo_access) missing from post_query
# ===========================================================================
def test_query_read_role_without_repo_access_returns_403():
    """POST /query with read-role key that lacks repo access → 403."""
    from unittest.mock import AsyncMock

    app, mocks = _create_test_app(api_key=_make_api_key("read"))

    # Set up mock session to return a repo for the ACL lookup
    mock_repo = MagicMock()
    mock_repo.id = uuid.uuid4()
    mock_repo.name = "owner/repo"

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = mock_repo
    mocks["session"].execute.return_value = result_mock

    # ACL check denies access
    mocks["auth_middleware"].check_repo_access = AsyncMock(return_value=False)

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(
        "/api/v1/query",
        json={"query": "find auth handler", "repo_id": "owner/repo"},
    )

    assert resp.status_code == 403, (
        f"Expected 403 (repo access denied for read key), got {resp.status_code}. "
        f"Response: {resp.json()}"
    )
    assert "Access denied" in resp.json().get("detail", ""), (
        f"Expected 'Access denied' in detail, got: {resp.json()}"
    )


# ===========================================================================
# Wave 5: read-role key with valid repo access → 200
# Verifies ACL check allows through when check_repo_access returns True
# ===========================================================================
def test_query_read_role_with_repo_access_returns_200():
    """POST /query with read-role key that has repo access → 200."""
    from unittest.mock import AsyncMock

    app, mocks = _create_test_app(api_key=_make_api_key("read"))

    mock_repo = MagicMock()
    mock_repo.id = uuid.uuid4()
    mock_repo.name = "owner/repo"

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = mock_repo
    mocks["session"].execute.return_value = result_mock

    # ACL check grants access
    mocks["auth_middleware"].check_repo_access = AsyncMock(return_value=True)

    client = TestClient(app)
    resp = client.post(
        "/api/v1/query",
        json={"query": "find auth handler", "repo_id": "owner/repo"},
    )

    assert resp.status_code == 200, f"Unexpected error: {resp.json()}"
    mocks["query_handler"].handle_nl_query.assert_called_once()


# ===========================================================================
# Wave 5: malformed JSON body → 400 (not 422)
# Kills bug: FastAPI default returns 422 for malformed JSON; spec requires 400
# ===========================================================================
def test_query_malformed_json_returns_400():
    """POST /query with malformed JSON body → 400 (not 422)."""
    # ST-BNDRY-017-001
    app, mocks = _create_test_app()
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.post(
        "/api/v1/query",
        content=b"{invalid json}",
        headers={"Content-Type": "application/json"},
    )

    assert resp.status_code == 400, (
        f"Expected 400 for malformed JSON body, got {resp.status_code}. "
        f"Response: {resp.text}"
    )
