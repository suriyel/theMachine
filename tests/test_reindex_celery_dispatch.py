# Feature #49: Fix reindex API Celery dispatch
# Tests for the bugfix: POST /api/v1/repos/{repo_id}/reindex must dispatch
# reindex_repo_task.delay() after creating the IndexJob record.
#
# [no integration test] — Celery dispatch tested via mock; real Celery broker
# integration is covered by Feature #22's existing integration tests.
# The bugfix adds a single .delay() call; mock verifies it is wired correctly.
# SEC: N/A — auth tested by existing Feature #22 tests; this bugfix doesn't change auth.

import os
for _k in ("ALL_PROXY", "all_proxy"):
    os.environ.pop(_k, None)

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from fastapi.testclient import TestClient

from src.shared.models.api_key import ApiKey


# ---------------------------------------------------------------------------
# Helpers (mirrors test_rest_api.py patterns)
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
    mock_query_handler.handle_nl_query = AsyncMock(
        return_value=MagicMock()
    )

    mock_auth_middleware = MagicMock(spec=AuthMiddleware)
    mock_auth_middleware.check_permission = MagicMock(return_value=True)

    mock_api_key_manager = AsyncMock()

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
        "session": mock_session,
        "auth_middleware": mock_auth_middleware,
        "api_key": api_key,
    }


def _setup_repo_in_session(mocks, repo_id=None):
    """Set up a mock repo that will be found by the reindex endpoint."""
    if repo_id is None:
        repo_id = uuid.uuid4()
    mock_repo = MagicMock()
    mock_repo.id = repo_id
    mock_repo.name = "test-repo"
    mock_repo.indexed_branch = "main"
    mock_repo.default_branch = None

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = mock_repo
    mocks["session"].execute.return_value = result_mock

    return mock_repo, repo_id


# ---------------------------------------------------------------------------
# Test A: FUNC/happy — reindex dispatches Celery task
# [unit] — mocked Celery task
# ---------------------------------------------------------------------------
def test_reindex_dispatches_celery_task():
    """POST /repos/{id}/reindex must call reindex_repo_task.delay(str(repo.id))."""
    app, mocks = _create_test_app()
    mock_repo, repo_id = _setup_repo_in_session(mocks)

    job_id = uuid.uuid4()
    with patch("src.query.api.v1.endpoints.repos.IndexJob") as MockJob, \
         patch("src.query.api.v1.endpoints.repos.reindex_repo_task") as mock_task:
        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.status = "pending"
        MockJob.return_value = mock_job

        client = TestClient(app)
        resp = client.post(f"/api/v1/repos/{repo_id}/reindex")

    assert resp.status_code == 200
    data = resp.json()
    assert data["job_id"] == str(job_id)
    assert data["repo_id"] == str(repo_id)
    assert data["status"] == "pending"
    # THE KEY ASSERTION: delay() was called
    mock_task.delay.assert_called_once_with(str(repo_id))


# ---------------------------------------------------------------------------
# Test B: FUNC/dispatch-args — delay() called with string, not UUID
# [unit] — verifies argument type
# ---------------------------------------------------------------------------
def test_reindex_dispatch_args_are_string():
    """delay() must receive str(repo.id), not the UUID object."""
    app, mocks = _create_test_app()
    mock_repo, repo_id = _setup_repo_in_session(mocks)

    with patch("src.query.api.v1.endpoints.repos.IndexJob") as MockJob, \
         patch("src.query.api.v1.endpoints.repos.reindex_repo_task") as mock_task:
        mock_job = MagicMock()
        mock_job.id = uuid.uuid4()
        mock_job.status = "pending"
        MockJob.return_value = mock_job

        client = TestClient(app)
        client.post(f"/api/v1/repos/{repo_id}/reindex")

    # Verify exactly one arg passed and it's a string
    mock_task.delay.assert_called_once()
    args = mock_task.delay.call_args[0]
    assert len(args) == 1, f"Expected 1 positional arg, got {len(args)}"
    assert isinstance(args[0], str), f"Expected str, got {type(args[0])}"
    assert args[0] == str(repo_id)


# ---------------------------------------------------------------------------
# Test C: FUNC/error-404 — nonexistent repo, no dispatch
# [unit] — negative test
# ---------------------------------------------------------------------------
def test_reindex_nonexistent_repo_no_dispatch():
    """POST /repos/{bad_id}/reindex → 404, delay() NOT called."""
    app, mocks = _create_test_app()
    bad_id = uuid.uuid4()
    # session returns None for repo lookup (default)

    with patch("src.query.api.v1.endpoints.repos.reindex_repo_task") as mock_task:
        client = TestClient(app)
        resp = client.post(f"/api/v1/repos/{bad_id}/reindex")

    assert resp.status_code == 404
    mock_task.delay.assert_not_called()


# ---------------------------------------------------------------------------
# Test D: FUNC/error-dispatch — dispatch fails, endpoint still succeeds
# [unit] — negative test
# ---------------------------------------------------------------------------
def test_reindex_dispatch_failure_still_returns_success():
    """If reindex_repo_task.delay() raises, endpoint still returns 200."""
    app, mocks = _create_test_app()
    mock_repo, repo_id = _setup_repo_in_session(mocks)

    job_id = uuid.uuid4()
    with patch("src.query.api.v1.endpoints.repos.IndexJob") as MockJob, \
         patch("src.query.api.v1.endpoints.repos.reindex_repo_task") as mock_task:
        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.status = "pending"
        MockJob.return_value = mock_job
        mock_task.delay.side_effect = ConnectionError("Celery broker down")

        client = TestClient(app)
        resp = client.post(f"/api/v1/repos/{repo_id}/reindex")

    assert resp.status_code == 200
    data = resp.json()
    assert data["job_id"] == str(job_id)
    assert data["repo_id"] == str(repo_id)
    # IndexJob was still committed
    mocks["session"].commit.assert_awaited()


# ---------------------------------------------------------------------------
# Test E: FUNC/error-permission — read-only key, no dispatch
# [unit] — negative test
# ---------------------------------------------------------------------------
def test_reindex_readonly_key_no_dispatch():
    """POST /repos/{id}/reindex with read-only key → 403, delay() NOT called."""
    readonly_key = _make_api_key("readonly")
    app, mocks = _create_test_app(api_key=readonly_key)
    mocks["auth_middleware"].check_permission = MagicMock(return_value=False)

    repo_id = uuid.uuid4()

    with patch("src.query.api.v1.endpoints.repos.reindex_repo_task") as mock_task:
        client = TestClient(app)
        resp = client.post(f"/api/v1/repos/{repo_id}/reindex")

    assert resp.status_code == 403
    mock_task.delay.assert_not_called()


# ---------------------------------------------------------------------------
# Test F: BNDRY/commit-before-dispatch — ordering: commit then delay
# [unit] — negative test (catches dispatch-before-commit bug)
# ---------------------------------------------------------------------------
def test_reindex_commit_before_dispatch():
    """session.commit() must be called BEFORE reindex_repo_task.delay()."""
    app, mocks = _create_test_app()
    mock_repo, repo_id = _setup_repo_in_session(mocks)

    call_order = []

    original_commit = mocks["session"].commit
    async def tracking_commit():
        call_order.append("commit")
        return await original_commit()

    mocks["session"].commit = tracking_commit

    with patch("src.query.api.v1.endpoints.repos.IndexJob") as MockJob, \
         patch("src.query.api.v1.endpoints.repos.reindex_repo_task") as mock_task:
        mock_job = MagicMock()
        mock_job.id = uuid.uuid4()
        mock_job.status = "pending"
        MockJob.return_value = mock_job
        mock_task.delay.side_effect = lambda *a: call_order.append("delay")

        client = TestClient(app)
        resp = client.post(f"/api/v1/repos/{repo_id}/reindex")

    assert resp.status_code == 200
    assert "commit" in call_order, "commit was never called"
    assert "delay" in call_order, "delay was never called"
    commit_idx = call_order.index("commit")
    delay_idx = call_order.index("delay")
    assert commit_idx < delay_idx, (
        f"commit must happen before delay, got order: {call_order}"
    )


# ---------------------------------------------------------------------------
# Test G: BNDRY/cache-after-dispatch — cache invalidated even on success
# [unit] — boundary test
# ---------------------------------------------------------------------------
def test_reindex_cache_invalidated_with_dispatch():
    """Cache invalidation occurs even when dispatch succeeds."""
    app, mocks = _create_test_app()
    mock_repo, repo_id = _setup_repo_in_session(mocks)

    mock_cache = AsyncMock()
    app.state.query_cache = mock_cache

    with patch("src.query.api.v1.endpoints.repos.IndexJob") as MockJob, \
         patch("src.query.api.v1.endpoints.repos.reindex_repo_task") as mock_task:
        mock_job = MagicMock()
        mock_job.id = uuid.uuid4()
        mock_job.status = "pending"
        MockJob.return_value = mock_job

        client = TestClient(app)
        resp = client.post(f"/api/v1/repos/{repo_id}/reindex")

    assert resp.status_code == 200
    mock_cache.invalidate_repo.assert_awaited_once_with("test-repo")
    mock_task.delay.assert_called_once()


# ---------------------------------------------------------------------------
# Test H: BNDRY/no-cache — no query_cache, endpoint still works
# [unit] — negative/boundary test
# ---------------------------------------------------------------------------
def test_reindex_no_cache_still_succeeds():
    """Endpoint succeeds when app.state.query_cache is None."""
    app, mocks = _create_test_app()
    mock_repo, repo_id = _setup_repo_in_session(mocks)

    # Ensure no query_cache
    if hasattr(app.state, "query_cache"):
        delattr(app.state, "query_cache")

    with patch("src.query.api.v1.endpoints.repos.IndexJob") as MockJob, \
         patch("src.query.api.v1.endpoints.repos.reindex_repo_task") as mock_task:
        mock_job = MagicMock()
        mock_job.id = uuid.uuid4()
        mock_job.status = "pending"
        MockJob.return_value = mock_job

        client = TestClient(app)
        resp = client.post(f"/api/v1/repos/{repo_id}/reindex")

    assert resp.status_code == 200
    mock_task.delay.assert_called_once()
