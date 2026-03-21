"""Feature #33 — Branch Listing API

GET /api/v1/repos/{id}/branches endpoint tests.

Test Inventory from docs/plans/2026-03-22-branch-listing-api.md §7.
- T1-T2, T8-T10: happy path / boundary — verify correct response shape and values
- T3: error — 404 for unknown repo
- T4: error — 409 for uncloned repo
- T5: error — 403 for unauthorized
- T6: boundary — empty branches
- T7: boundary — default_branch fallback when null
- T11: error — 500 when GitCloner fails
- T12: [real] integration — list branches on a real cloned repo

# Security: N/A — auth tested via mock middleware (same pattern as Feature #17)

Negative test ratio: 6/12 = 50% >= 40% ✓
"""

import os
for _k in ("ALL_PROXY", "all_proxy"):
    os.environ.pop(_k, None)

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.query.api.v1.deps import get_authenticated_key, get_auth_middleware
from src.shared.exceptions import CloneError
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


def _mock_repo(
    *,
    clone_path: str | None = "/tmp/repos/test-repo",
    default_branch: str | None = "main",
    status: str = "indexed",
) -> MagicMock:
    """Create a mock Repository with the given fields."""
    repo = MagicMock()
    repo.id = uuid.uuid4()
    repo.name = "owner/test-repo"
    repo.url = "https://github.com/owner/test-repo"
    repo.status = status
    repo.indexed_branch = "main"
    repo.clone_path = clone_path
    repo.default_branch = default_branch
    repo.last_indexed_at = None
    repo.created_at = None
    return repo


def _mock_session_factory(repo=None):
    """Create async context manager mock for session_factory."""
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = repo
    result_mock.scalars.return_value.all.return_value = []
    session.execute.return_value = result_mock
    session.commit = AsyncMock()

    @asynccontextmanager
    async def factory():
        yield session

    return factory, session


def _create_test_app(api_key=None, repo=None):
    """Create a test app with mocked services."""
    from src.query.app import create_app
    from src.shared.services.auth_middleware import AuthMiddleware

    mock_auth_middleware = MagicMock(spec=AuthMiddleware)
    mock_auth_middleware.check_permission = MagicMock(return_value=True)

    session_factory, mock_session = _mock_session_factory(repo)

    app = create_app(
        query_handler=MagicMock(),
        auth_middleware=mock_auth_middleware,
        api_key_manager=AsyncMock(),
        session_factory=session_factory,
        es_client=AsyncMock(),
        qdrant_client=AsyncMock(),
        redis_client=AsyncMock(),
    )

    if api_key is None:
        api_key = _make_api_key("admin")

    app.dependency_overrides[get_authenticated_key] = lambda: api_key

    return app, {
        "auth_middleware": mock_auth_middleware,
        "session": mock_session,
        "api_key": api_key,
    }


# ===========================================================================
# [unit] T1: Happy path — cloned repo returns branches sorted + default_branch
# ===========================================================================
def test_list_branches_happy_path():
    """VS-1: Given cloned repo, returns 200 with sorted branches and default_branch."""
    repo = _mock_repo(clone_path="/tmp/repos/test", default_branch="main")
    app, mocks = _create_test_app(repo=repo)
    client = TestClient(app)

    with patch(
        "src.query.api.v1.endpoints.repos.GitCloner"
    ) as MockCloner:
        instance = MockCloner.return_value
        instance.list_remote_branches.return_value = ["develop", "feature-x", "main"]

        resp = client.get(f"/api/v1/repos/{repo.id}/branches")

    assert resp.status_code == 200
    data = resp.json()
    assert data["branches"] == ["develop", "feature-x", "main"]
    assert data["default_branch"] == "main"


# ===========================================================================
# [unit] T2: Happy path — default_branch from DB (not hardcoded)
# ===========================================================================
def test_list_branches_uses_db_default_branch():
    """VS-1: default_branch reflects DB value, not hardcoded 'main'."""
    repo = _mock_repo(clone_path="/tmp/repos/test", default_branch="develop")
    app, mocks = _create_test_app(repo=repo)
    client = TestClient(app)

    with patch(
        "src.query.api.v1.endpoints.repos.GitCloner"
    ) as MockCloner:
        instance = MockCloner.return_value
        instance.list_remote_branches.return_value = ["develop", "main"]

        resp = client.get(f"/api/v1/repos/{repo.id}/branches")

    assert resp.status_code == 200
    data = resp.json()
    assert data["default_branch"] == "develop"


# ===========================================================================
# [unit] T3: Error — repo not found returns 404
# ===========================================================================
def test_list_branches_repo_not_found():
    """VS-2: Unknown repo_id returns 404."""
    app, mocks = _create_test_app(repo=None)  # No repo in DB
    client = TestClient(app)

    fake_id = uuid.uuid4()
    resp = client.get(f"/api/v1/repos/{fake_id}/branches")

    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ===========================================================================
# [unit] T4: Error — repo not cloned returns 409
# ===========================================================================
def test_list_branches_not_cloned():
    """VS-3: Repo with clone_path=None returns 409 Conflict."""
    repo = _mock_repo(clone_path=None, status="pending")
    app, mocks = _create_test_app(repo=repo)
    client = TestClient(app)

    resp = client.get(f"/api/v1/repos/{repo.id}/branches")

    assert resp.status_code == 409
    assert "not been cloned" in resp.json()["detail"].lower()


# ===========================================================================
# [unit] T5: Error — unauthorized (403)
# ===========================================================================
def test_list_branches_unauthorized():
    """Permission denied returns 403."""
    repo = _mock_repo()
    api_key = _make_api_key(role="read")
    app, mocks = _create_test_app(api_key=api_key, repo=repo)
    # Override permission check to deny
    mocks["auth_middleware"].check_permission = MagicMock(return_value=False)
    client = TestClient(app)

    resp = client.get(f"/api/v1/repos/{repo.id}/branches")

    assert resp.status_code == 403
    assert "permissions" in resp.json()["detail"].lower()


# ===========================================================================
# [unit] T6: Boundary — empty branches list
# ===========================================================================
def test_list_branches_empty_list():
    """Cloned repo with zero remote branches returns empty list."""
    repo = _mock_repo(clone_path="/tmp/repos/empty")
    app, mocks = _create_test_app(repo=repo)
    client = TestClient(app)

    with patch(
        "src.query.api.v1.endpoints.repos.GitCloner"
    ) as MockCloner:
        instance = MockCloner.return_value
        instance.list_remote_branches.return_value = []

        resp = client.get(f"/api/v1/repos/{repo.id}/branches")

    assert resp.status_code == 200
    data = resp.json()
    assert data["branches"] == []
    assert data["default_branch"] == "main"


# ===========================================================================
# [unit] T7: Boundary — default_branch is None, fallback to "main"
# ===========================================================================
def test_list_branches_default_branch_none_fallback():
    """When repo.default_branch is None, response uses 'main' as fallback."""
    repo = _mock_repo(clone_path="/tmp/repos/test", default_branch=None)
    app, mocks = _create_test_app(repo=repo)
    client = TestClient(app)

    with patch(
        "src.query.api.v1.endpoints.repos.GitCloner"
    ) as MockCloner:
        instance = MockCloner.return_value
        instance.list_remote_branches.return_value = ["feature-a"]

        resp = client.get(f"/api/v1/repos/{repo.id}/branches")

    assert resp.status_code == 200
    data = resp.json()
    assert data["default_branch"] == "main"


# ===========================================================================
# [unit] T8: Boundary — single branch
# ===========================================================================
def test_list_branches_single_branch():
    """Repo with only one remote branch returns single-element list."""
    repo = _mock_repo(clone_path="/tmp/repos/test", default_branch="main")
    app, mocks = _create_test_app(repo=repo)
    client = TestClient(app)

    with patch(
        "src.query.api.v1.endpoints.repos.GitCloner"
    ) as MockCloner:
        instance = MockCloner.return_value
        instance.list_remote_branches.return_value = ["main"]

        resp = client.get(f"/api/v1/repos/{repo.id}/branches")

    assert resp.status_code == 200
    data = resp.json()
    assert data["branches"] == ["main"]
    assert len(data["branches"]) == 1


# ===========================================================================
# [unit] T9: Error — GitCloner raises CloneError returns 500
# ===========================================================================
def test_list_branches_clone_error_returns_500():
    """When GitCloner fails, endpoint returns 500."""
    repo = _mock_repo(clone_path="/tmp/repos/test")
    app, mocks = _create_test_app(repo=repo)
    client = TestClient(app)

    with patch(
        "src.query.api.v1.endpoints.repos.GitCloner"
    ) as MockCloner:
        instance = MockCloner.return_value
        instance.list_remote_branches.side_effect = CloneError("git branch -r failed")

        resp = client.get(f"/api/v1/repos/{repo.id}/branches")

    assert resp.status_code == 500
    assert "branch" in resp.json()["detail"].lower()


# ===========================================================================
# [unit] T10: Happy path — read role can access list_branches
# ===========================================================================
def test_list_branches_read_role_authorized():
    """Read-role API key can access list_branches endpoint."""
    repo = _mock_repo(clone_path="/tmp/repos/test")
    api_key = _make_api_key(role="read")
    app, mocks = _create_test_app(api_key=api_key, repo=repo)
    # Auth middleware allows (default behavior)
    client = TestClient(app)

    with patch(
        "src.query.api.v1.endpoints.repos.GitCloner"
    ) as MockCloner:
        instance = MockCloner.return_value
        instance.list_remote_branches.return_value = ["main"]

        resp = client.get(f"/api/v1/repos/{repo.id}/branches")

    assert resp.status_code == 200
    data = resp.json()
    assert "branches" in data
    assert data["branches"] == ["main"]


# ===========================================================================
# [unit] T11: Response schema has exactly the expected keys
# ===========================================================================
def test_list_branches_response_shape():
    """Response JSON has exactly 'branches' and 'default_branch' keys."""
    repo = _mock_repo(clone_path="/tmp/repos/test")
    app, mocks = _create_test_app(repo=repo)
    client = TestClient(app)

    with patch(
        "src.query.api.v1.endpoints.repos.GitCloner"
    ) as MockCloner:
        instance = MockCloner.return_value
        instance.list_remote_branches.return_value = ["main"]

        resp = client.get(f"/api/v1/repos/{repo.id}/branches")

    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"branches", "default_branch"}


# ===========================================================================
# [real/integration] T12: Real GitCloner.list_remote_branches on a cloned repo
# feature #33 — real integration test
# ===========================================================================
@pytest.mark.real
def test_real_list_remote_branches_on_cloned_repo(tmp_path):
    """Real integration: clone a public repo and verify list_remote_branches returns real branches."""
    from src.indexing.git_cloner import GitCloner

    cloner = GitCloner(storage_path=str(tmp_path))
    url = "https://github.com/octocat/Hello-World.git"
    dest = cloner.clone_or_update("octocat-Hello-World", url)

    branches = cloner.list_remote_branches(dest)

    # Hello-World has at least 'master' branch
    assert isinstance(branches, list)
    assert len(branches) >= 1
    assert all(isinstance(b, str) for b in branches)
    # Branches must be sorted
    assert branches == sorted(branches)
    # Must not contain 'origin/' prefix
    assert all(not b.startswith("origin/") for b in branches)
    # Must contain at least one well-known branch
    assert any(b in ("master", "main") for b in branches)
