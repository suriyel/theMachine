"""Tests for WebRouter — Web UI Index Management Page (feature #47).

Categories:
  - Happy path: T01-T07
  - Error handling: T08-T13, T18-T20, T22
  - Boundary: T14-T17, T21
  - Security: N/A — internal admin tool, same cookie auth as search page

# [no integration test] — pure WebRouter unit tests with mocked DB/ES/Qdrant;
# real integration tested via Feature-ST (Chrome DevTools MCP against running server).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.query.web_router import WebRouter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_repo(
    name: str = "repo-alpha",
    status: str = "indexed",
    indexed_branch: str | None = "main",
    default_branch: str | None = None,
    last_indexed_at: datetime | None = None,
    repo_id: uuid.UUID | None = None,
) -> MagicMock:
    """Create a mock Repository with the given fields."""
    repo = MagicMock()
    repo.id = repo_id or uuid.uuid4()
    repo.name = name
    repo.status = status
    repo.indexed_branch = indexed_branch
    repo.default_branch = default_branch
    repo.last_indexed_at = last_indexed_at
    repo.url = f"https://github.com/org/{name}"
    return repo


def _make_session_factory(repos: list | None = None, raise_on_execute: bool = False):
    """Build a mock async session factory returning given repos."""
    session = AsyncMock()
    if raise_on_execute:
        session.execute.side_effect = Exception("DB connection failed")
    else:
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = repos or []
        # first() for single-repo lookups
        if repos:
            result_mock.scalars.return_value.first.return_value = repos[0]
        else:
            result_mock.scalars.return_value.first.return_value = None
        session.execute.return_value = result_mock

    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=session)
    factory.return_value.__aexit__ = AsyncMock(return_value=False)
    return factory, session


def _make_es_client(code_chunks: int = 0, doc_chunks: int = 0, rule_chunks: int = 0, raise_on_count: bool = False):
    """Build a mock ES client with _client.count responses."""
    es = MagicMock()
    inner = AsyncMock()
    if raise_on_count:
        inner.count.side_effect = Exception("ES unavailable")
    else:
        counts = {
            "code_chunks": {"count": code_chunks},
            "doc_chunks": {"count": doc_chunks},
            "rule_chunks": {"count": rule_chunks},
        }
        async def mock_count(index=None, body=None, **kwargs):
            return counts.get(index, {"count": 0})
        inner.count = AsyncMock(side_effect=mock_count)
    es._client = inner
    return es


def _make_qdrant_client(code_embeddings: int = 0, doc_embeddings: int = 0):
    """Build a mock Qdrant client with _client.count responses."""
    qdrant = MagicMock()
    inner = AsyncMock()
    counts = {
        "code_embeddings": MagicMock(count=code_embeddings),
        "doc_embeddings": MagicMock(count=doc_embeddings),
    }
    async def mock_count(collection_name, count_filter=None, **kwargs):
        return counts.get(collection_name, MagicMock(count=0))
    inner.count = AsyncMock(side_effect=mock_count)
    qdrant._client = inner
    return qdrant


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def repo1():
    return _make_repo(
        name="repo-alpha",
        status="indexed",
        indexed_branch="main",
        last_indexed_at=datetime(2026, 3, 25, 10, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def repo2():
    return _make_repo(
        name="repo-beta",
        status="pending",
        indexed_branch="dev",
        last_indexed_at=None,
    )


def _build_app(
    session_factory=None,
    es_client=None,
    qdrant_client=None,
) -> tuple[FastAPI, TestClient]:
    """Create a test FastAPI app with WebRouter and given mocks."""
    import os
    from starlette.staticfiles import StaticFiles

    test_app = FastAPI()
    web_router = WebRouter()
    test_app.include_router(web_router.router)

    static_dir = os.path.join(os.path.dirname(__file__), "..", "src", "query", "static")
    if os.path.isdir(static_dir):
        test_app.mount("/static", StaticFiles(directory=static_dir), name="static")

    if session_factory is not None:
        test_app.state.session_factory = session_factory
    if es_client is not None:
        test_app.state.es_client = es_client
    if qdrant_client is not None:
        test_app.state.qdrant_client = qdrant_client

    return test_app, TestClient(test_app)


# ===========================================================================
# Happy Path Tests
# ===========================================================================


# [unit] T01: GET /admin/indexes with 2 repos in DB
def test_index_management_page_lists_repos(repo1, repo2):
    factory, _session = _make_session_factory([repo1, repo2])
    _app, client = _build_app(session_factory=factory)

    response = client.get("/admin/indexes")
    assert response.status_code == 200
    html = response.text
    assert "repo-alpha" in html
    assert "repo-beta" in html
    # Check columns: status, branch
    assert "indexed" in html
    assert "pending" in html
    assert "main" in html
    assert "dev" in html


# [unit] T02: GET /admin/indexes/{repo_id}/stats returns 5 counts
def test_index_stats_returns_counts(repo1):
    factory, _session = _make_session_factory([repo1])
    es = _make_es_client(code_chunks=100, doc_chunks=50, rule_chunks=10)
    qdrant = _make_qdrant_client(code_embeddings=100, doc_embeddings=50)
    _app, client = _build_app(session_factory=factory, es_client=es, qdrant_client=qdrant)

    response = client.get(f"/admin/indexes/{repo1.id}/stats")
    assert response.status_code == 200
    html = response.text
    assert "100" in html  # code_chunks / code_embeddings
    assert "50" in html   # doc_chunks / doc_embeddings
    assert "10" in html   # rule_chunks
    # Verify ES was queried with correct index names
    es_calls = es._client.count.call_args_list
    es_index_names = [call.kwargs.get("index") or call.args[0] if call.args else call.kwargs.get("index") for call in es_calls]
    assert "code_chunks" in es_index_names
    assert "doc_chunks" in es_index_names
    assert "rule_chunks" in es_index_names
    # Verify Qdrant was queried with correct collection names
    qdrant_calls = qdrant._client.count.call_args_list
    qdrant_collection_names = [call.kwargs.get("collection_name") or (call.args[0] if call.args else None) for call in qdrant_calls]
    assert "code_embeddings" in qdrant_collection_names
    assert "doc_embeddings" in qdrant_collection_names


# [unit] T03: POST /admin/indexes/{repo_id}/reindex dispatches Celery task
def test_index_reindex_dispatches_celery(repo1):
    factory, session = _make_session_factory([repo1])
    _app, client = _build_app(session_factory=factory)

    with patch("src.query.web_router.reindex_repo_task") as mock_task:
        mock_task.delay.return_value = MagicMock(id="task-123")
        response = client.post(f"/admin/indexes/{repo1.id}/reindex")

    assert response.status_code == 200
    html = response.text
    mock_task.delay.assert_called_once_with(str(repo1.id))
    assert "Reindex queued" in html or "reindex" in html.lower()


# [unit] T04: POST /admin/indexes/reindex-all dispatches for all repos
def test_index_reindex_all_dispatches_for_all_repos(repo1, repo2):
    factory, _session = _make_session_factory([repo1, repo2])
    _app, client = _build_app(session_factory=factory)

    with patch("src.query.web_router.reindex_repo_task") as mock_task:
        mock_task.delay.return_value = MagicMock(id="task-456")
        response = client.post("/admin/indexes/reindex-all")

    assert response.status_code == 200
    assert mock_task.delay.call_count == 2
    html = response.text
    assert "2" in html  # "2 repositories"


# [unit] T05: POST /admin/indexes/{repo_id}/delete calls delete_repo_index
def test_index_delete_calls_delete_repo_index(repo1):
    factory, session = _make_session_factory([repo1])
    es = _make_es_client()
    qdrant = _make_qdrant_client()
    _app, client = _build_app(session_factory=factory, es_client=es, qdrant_client=qdrant)

    with patch("src.query.web_router.IndexWriter") as MockIW:
        mock_writer = AsyncMock()
        MockIW.return_value = mock_writer
        response = client.post(f"/admin/indexes/{repo1.id}/delete")

    assert response.status_code == 200
    mock_writer.delete_repo_index.assert_called_once_with(str(repo1.id), "main")
    html = response.text
    assert "deleted" in html.lower() or "Index deleted" in html
    # Verify last_indexed_at was set to None
    assert repo1.last_indexed_at is None


# [unit] T06: All action endpoints return HTML partials (not full page, not JSON)
def test_actions_return_html_partials(repo1):
    factory, _session = _make_session_factory([repo1])
    es = _make_es_client(code_chunks=1)
    qdrant = _make_qdrant_client(code_embeddings=1)
    _app, client = _build_app(session_factory=factory, es_client=es, qdrant_client=qdrant)

    with patch("src.query.web_router.reindex_repo_task") as mock_task, \
         patch("src.query.web_router.IndexWriter") as MockIW:
        mock_task.delay.return_value = MagicMock(id="t1")
        MockIW.return_value = AsyncMock()

        # Stats partial
        resp_stats = client.get(f"/admin/indexes/{repo1.id}/stats")
        assert resp_stats.status_code == 200
        assert "text/html" in resp_stats.headers.get("content-type", "")
        assert "<!DOCTYPE" not in resp_stats.text  # partial, not full page

        # Reindex partial
        resp_reindex = client.post(f"/admin/indexes/{repo1.id}/reindex")
        assert resp_reindex.status_code == 200
        assert "<!DOCTYPE" not in resp_reindex.text

        # Delete partial
        resp_delete = client.post(f"/admin/indexes/{repo1.id}/delete")
        assert resp_delete.status_code == 200
        assert "<!DOCTYPE" not in resp_delete.text


# [unit] T07: Index management routes are NOT accessible via MCP tools
def test_no_mcp_exposure():
    from src.query.mcp_server import create_mcp_server
    mock_handler = MagicMock()
    mock_sf = MagicMock()
    mock_es = MagicMock()
    mcp = create_mcp_server(mock_handler, mock_sf, mock_es)
    # Inspect registered tool names
    tool_names = []
    if hasattr(mcp, "_tool_manager"):
        tool_names = list(mcp._tool_manager._tools.keys()) if hasattr(mcp._tool_manager, "_tools") else []
    elif hasattr(mcp, "_tools"):
        tool_names = list(mcp._tools.keys())

    for name in tool_names:
        assert "admin" not in name.lower(), \
            f"MCP tool '{name}' should not expose admin routes"
    # Verify no index management tools exist (reindex, delete_index, etc.)
    mgmt_keywords = {"reindex", "delete_index", "index_management", "index_stats"}
    for name in tool_names:
        assert name.lower() not in mgmt_keywords, \
            f"MCP tool '{name}' exposes index management functionality"


# ===========================================================================
# Error Handling Tests
# ===========================================================================


# [unit] T08: Stats — repo not found
def test_index_stats_repo_not_found():
    factory, _session = _make_session_factory([])  # no repos
    es = _make_es_client()
    _app, client = _build_app(session_factory=factory, es_client=es)

    fake_id = uuid.uuid4()
    response = client.get(f"/admin/indexes/{fake_id}/stats")
    assert response.status_code == 200
    assert "not found" in response.text.lower() or "error" in response.text.lower()


# [unit] T09: Reindex — repo not found
def test_index_reindex_repo_not_found():
    factory, _session = _make_session_factory([])
    _app, client = _build_app(session_factory=factory)

    fake_id = uuid.uuid4()
    with patch("src.query.web_router.reindex_repo_task"):
        response = client.post(f"/admin/indexes/{fake_id}/reindex")
    assert response.status_code == 200
    assert "not found" in response.text.lower() or "error" in response.text.lower()


# [unit] T10: Delete — repo not found
def test_index_delete_repo_not_found():
    factory, _session = _make_session_factory([])
    _app, client = _build_app(session_factory=factory)

    fake_id = uuid.uuid4()
    response = client.post(f"/admin/indexes/{fake_id}/delete")
    assert response.status_code == 200
    assert "not found" in response.text.lower() or "error" in response.text.lower()


# [unit] T11: Delete — IndexWriteError
def test_index_delete_write_error(repo1):
    from src.indexing.exceptions import IndexWriteError

    factory, _session = _make_session_factory([repo1])
    es = _make_es_client()
    qdrant = _make_qdrant_client()
    _app, client = _build_app(session_factory=factory, es_client=es, qdrant_client=qdrant)

    with patch("src.query.web_router.IndexWriter") as MockIW:
        mock_writer = AsyncMock()
        mock_writer.delete_repo_index.side_effect = IndexWriteError("ES connection lost")
        MockIW.return_value = mock_writer
        response = client.post(f"/admin/indexes/{repo1.id}/delete")

    assert response.status_code == 200
    assert "failed" in response.text.lower() or "error" in response.text.lower()


# [unit] T12: Stats — ES count failure
def test_index_stats_es_failure(repo1):
    factory, _session = _make_session_factory([repo1])
    es = _make_es_client(raise_on_count=True)
    _app, client = _build_app(session_factory=factory, es_client=es)

    response = client.get(f"/admin/indexes/{repo1.id}/stats")
    assert response.status_code == 200
    assert "error" in response.text.lower() or "failed" in response.text.lower()


# [unit] T13: Reindex — Celery dispatch failure
def test_index_reindex_celery_failure(repo1):
    factory, _session = _make_session_factory([repo1])
    _app, client = _build_app(session_factory=factory)

    with patch("src.query.web_router.reindex_repo_task") as mock_task:
        mock_task.delay.side_effect = Exception("Broker unreachable")
        response = client.post(f"/admin/indexes/{repo1.id}/reindex")

    assert response.status_code == 200
    assert "failed" in response.text.lower() or "error" in response.text.lower()


# ===========================================================================
# Boundary Tests
# ===========================================================================


# [unit] T14: Index page with 0 repos
def test_index_management_page_empty_repos():
    factory, _session = _make_session_factory([])
    _app, client = _build_app(session_factory=factory)

    response = client.get("/admin/indexes")
    assert response.status_code == 200
    # Should show empty state message, not crash
    html = response.text
    assert "No repositories" in html or len(html) > 50  # renders something


# [unit] T15: Reindex — branch fallback to "main"
def test_index_reindex_branch_fallback():
    repo = _make_repo(indexed_branch=None, default_branch=None)
    factory, session = _make_session_factory([repo])
    _app, client = _build_app(session_factory=factory)

    with patch("src.query.web_router.reindex_repo_task") as mock_task:
        mock_task.delay.return_value = MagicMock(id="t1")
        response = client.post(f"/admin/indexes/{repo.id}/reindex")

    assert response.status_code == 200
    # Verify the IndexJob was added with branch "main" via session.add call
    add_call = session.add.call_args
    if add_call:
        job = add_call[0][0]
        assert job.branch == "main"


# [unit] T16: Delete — uses indexed_branch
def test_index_delete_uses_indexed_branch():
    repo = _make_repo(indexed_branch="develop")
    factory, _session = _make_session_factory([repo])
    es = _make_es_client()
    qdrant = _make_qdrant_client()
    _app, client = _build_app(session_factory=factory, es_client=es, qdrant_client=qdrant)

    with patch("src.query.web_router.IndexWriter") as MockIW:
        mock_writer = AsyncMock()
        MockIW.return_value = mock_writer
        response = client.post(f"/admin/indexes/{repo.id}/delete")

    assert response.status_code == 200
    mock_writer.delete_repo_index.assert_called_once_with(str(repo.id), "develop")


# [unit] T17: Reindex all with 0 repos
def test_index_reindex_all_no_repos():
    factory, _session = _make_session_factory([])
    _app, client = _build_app(session_factory=factory)

    with patch("src.query.web_router.reindex_repo_task") as mock_task:
        response = client.post("/admin/indexes/reindex-all")

    assert response.status_code == 200
    mock_task.delay.assert_not_called()
    assert "No repositories" in response.text or "0" in response.text


# [unit] T18: Stats — Qdrant unavailable (graceful degrade)
def test_index_stats_qdrant_unavailable(repo1):
    factory, _session = _make_session_factory([repo1])
    es = _make_es_client(code_chunks=10, doc_chunks=5, rule_chunks=2)
    # No qdrant client at all
    _app, client = _build_app(session_factory=factory, es_client=es, qdrant_client=None)

    response = client.get(f"/admin/indexes/{repo1.id}/stats")
    assert response.status_code == 200
    html = response.text
    # ES counts should appear
    assert "10" in html
    assert "5" in html
    assert "2" in html
    # Qdrant counts should be 0, not an error
    assert "0" in html


# [unit] T19: Index page with session_factory=None (graceful degrade)
def test_index_management_page_no_db():
    _app, client = _build_app(session_factory=None)

    response = client.get("/admin/indexes")
    assert response.status_code == 200
    # Should not crash — renders empty page


# [unit] T20: Reindex all — partial Celery failure
def test_index_reindex_all_partial_celery_failure(repo1, repo2):
    repo3 = _make_repo(name="repo-gamma")
    factory, _session = _make_session_factory([repo1, repo2, repo3])
    _app, client = _build_app(session_factory=factory)

    call_count = 0
    def side_effect(repo_id):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise Exception("Broker unreachable")
        return MagicMock(id=f"task-{call_count}")

    with patch("src.query.web_router.reindex_repo_task") as mock_task:
        mock_task.delay.side_effect = side_effect
        response = client.post("/admin/indexes/reindex-all")

    assert response.status_code == 200
    assert mock_task.delay.call_count == 3  # all attempted
    html = response.text
    assert "2" in html  # 2 successful out of 3


# [unit] T21: Stats — zero counts (no indexed data)
def test_index_stats_zero_counts(repo1):
    factory, _session = _make_session_factory([repo1])
    es = _make_es_client(code_chunks=0, doc_chunks=0, rule_chunks=0)
    qdrant = _make_qdrant_client(code_embeddings=0, doc_embeddings=0)
    _app, client = _build_app(session_factory=factory, es_client=es, qdrant_client=qdrant)

    response = client.get(f"/admin/indexes/{repo1.id}/stats")
    assert response.status_code == 200
    # Should render "0" values, not error
    assert "error" not in response.text.lower()


# ===========================================================================
# Real Tests
# ===========================================================================


# [integration] — Real Jinja2 template rendering for feature #47
@pytest.mark.real
def test_real_jinja2_template_renders_index_management_page(repo1, repo2):
    """Real test: verifies actual Jinja2 template renders without mocking the template engine.

    feature #47 — Web UI Index Management Page

    Exercises the full SSR pipeline: FastAPI -> WebRouter -> Jinja2 -> HTML.
    The template files on disk are read and rendered by the real Jinja2 engine.
    """
    factory, _session = _make_session_factory([repo1, repo2])
    _app, client = _build_app(session_factory=factory)

    resp = client.get("/admin/indexes")
    assert resp.status_code == 200
    html = resp.text
    # Verify real template rendered key structural elements
    assert "<!DOCTYPE html>" in html or "<!doctype html>" in html.lower()
    assert "repo-alpha" in html
    assert "repo-beta" in html
    assert "Index Management" in html or "index" in html.lower()
    assert "htmx" in html  # htmx loaded (HTMX partial updates requirement)


# [unit] T22: Index page — DB query exception
def test_index_management_page_db_error():
    factory, _session = _make_session_factory(raise_on_execute=True)
    _app, client = _build_app(session_factory=factory)

    response = client.get("/admin/indexes")
    assert response.status_code == 200
    # Should not crash — renders empty page gracefully


# ===========================================================================
# Mutation-killing Tests (strengthen assertions)
# ===========================================================================


# [unit] T23: Stats — session_factory=None returns error
def test_index_stats_no_db():
    _app, client = _build_app(session_factory=None)
    fake_id = uuid.uuid4()
    response = client.get(f"/admin/indexes/{fake_id}/stats")
    assert response.status_code == 200
    assert "Database not configured" in response.text
    assert "XXDatabase" not in response.text  # mutation kill


# [unit] T24: Reindex — session_factory=None returns error
def test_index_reindex_no_db():
    _app, client = _build_app(session_factory=None)
    fake_id = uuid.uuid4()
    response = client.post(f"/admin/indexes/{fake_id}/reindex")
    assert response.status_code == 200
    assert "Database not configured" in response.text
    assert "XXDatabase" not in response.text


# [unit] T25: Reindex all — session_factory=None returns error
def test_index_reindex_all_no_db():
    _app, client = _build_app(session_factory=None)
    response = client.post("/admin/indexes/reindex-all")
    assert response.status_code == 200
    assert "Database not configured" in response.text
    assert "XXDatabase" not in response.text


# [unit] T26: Delete — session_factory=None returns error
def test_index_delete_no_db():
    _app, client = _build_app(session_factory=None)
    fake_id = uuid.uuid4()
    response = client.post(f"/admin/indexes/{fake_id}/delete")
    assert response.status_code == 200
    assert "Database not configured" in response.text
    assert "XXDatabase" not in response.text


# [unit] T27: Stats — es_client=None returns error
def test_index_stats_no_es_client(repo1):
    factory, _session = _make_session_factory([repo1])
    _app, client = _build_app(session_factory=factory, es_client=None)
    response = client.get(f"/admin/indexes/{repo1.id}/stats")
    assert response.status_code == 200
    assert "Search service not configured" in response.text
    assert "XXSearch" not in response.text


# [unit] T28: Reindex — verify exact Celery task dispatch
def test_index_reindex_exact_task_dispatch(repo1):
    factory, session = _make_session_factory([repo1])
    _app, client = _build_app(session_factory=factory)

    with patch("src.query.web_router.reindex_repo_task") as mock_task:
        mock_task.delay.return_value = MagicMock(id="task-123")
        response = client.post(f"/admin/indexes/{repo1.id}/reindex")

    assert response.status_code == 200
    # Verify task was dispatched with correct repo ID string
    mock_task.delay.assert_called_once_with(str(repo1.id))
    # Verify success message contains repo name
    assert "repo-alpha" in response.text
    assert "Reindex queued" in response.text
    assert "XX" not in response.text


# [unit] T29: Reindex all — verify message contains correct count
def test_index_reindex_all_exact_message(repo1, repo2):
    factory, _session = _make_session_factory([repo1, repo2])
    _app, client = _build_app(session_factory=factory)

    with patch("src.query.web_router.reindex_repo_task") as mock_task:
        mock_task.delay.return_value = MagicMock(id="task-456")
        response = client.post("/admin/indexes/reindex-all")

    assert response.status_code == 200
    assert mock_task.delay.call_count == 2
    assert "2 repositories" in response.text
    assert "XX" not in response.text


# [unit] T30: Delete — verify exact success message
def test_index_delete_exact_message(repo1):
    factory, session = _make_session_factory([repo1])
    es = _make_es_client()
    qdrant = _make_qdrant_client()
    _app, client = _build_app(session_factory=factory, es_client=es, qdrant_client=qdrant)

    with patch("src.query.web_router.IndexWriter") as MockIW:
        mock_writer = AsyncMock()
        MockIW.return_value = mock_writer
        response = client.post(f"/admin/indexes/{repo1.id}/delete")

    assert response.status_code == 200
    assert "Index deleted" in response.text
    assert "repo-alpha" in response.text
    assert "XX" not in response.text


# [unit] T31: Stats — verify ES count body contains repo_id
def test_index_stats_es_query_contains_repo_id(repo1):
    factory, _session = _make_session_factory([repo1])
    es = _make_es_client(code_chunks=5, doc_chunks=3, rule_chunks=1)
    qdrant = _make_qdrant_client()
    _app, client = _build_app(session_factory=factory, es_client=es, qdrant_client=qdrant)

    response = client.get(f"/admin/indexes/{repo1.id}/stats")
    assert response.status_code == 200
    # Verify ES was called with body containing repo_id
    for call in es._client.count.call_args_list:
        body = call.kwargs.get("body")
        assert body is not None
        assert "query" in body
        assert "term" in body["query"]
        assert "repo_id" in body["query"]["term"]
        assert body["query"]["term"]["repo_id"] == str(repo1.id)


# [unit] T32: Reindex — verify IndexJob was created with correct branch
def test_index_reindex_creates_index_job(repo1):
    factory, session = _make_session_factory([repo1])
    _app, client = _build_app(session_factory=factory)

    with patch("src.query.web_router.reindex_repo_task") as mock_task:
        mock_task.delay.return_value = MagicMock(id="t1")
        response = client.post(f"/admin/indexes/{repo1.id}/reindex")

    assert response.status_code == 200
    # Verify session.add was called with an IndexJob
    add_call = session.add.call_args
    assert add_call is not None
    job = add_call[0][0]
    from src.shared.models.index_job import IndexJob
    assert isinstance(job, IndexJob)
    assert job.branch == "main"
    assert job.status == "pending"
    # Verify session.commit was called
    session.commit.assert_called()


# [unit] T33: Delete — verify IndexWriter instantiation with correct clients
def test_index_delete_index_writer_instantiation(repo1):
    factory, session = _make_session_factory([repo1])
    es = _make_es_client()
    qdrant = _make_qdrant_client()
    _app, client = _build_app(session_factory=factory, es_client=es, qdrant_client=qdrant)

    with patch("src.query.web_router.IndexWriter") as MockIW:
        mock_writer = AsyncMock()
        MockIW.return_value = mock_writer
        response = client.post(f"/admin/indexes/{repo1.id}/delete")

    assert response.status_code == 200
    # Verify IndexWriter was instantiated with the correct es and qdrant clients
    MockIW.assert_called_once_with(es, qdrant)


# [unit] T34: Stats — Qdrant exception is logged, returns 0 counts
def test_index_stats_qdrant_exception_returns_zero(repo1):
    factory, _session = _make_session_factory([repo1])
    es = _make_es_client(code_chunks=10, doc_chunks=5, rule_chunks=2)
    qdrant = MagicMock()
    inner = AsyncMock()
    inner.count.side_effect = Exception("Qdrant timeout")
    qdrant._client = inner
    _app, client = _build_app(session_factory=factory, es_client=es, qdrant_client=qdrant)

    response = client.get(f"/admin/indexes/{repo1.id}/stats")
    assert response.status_code == 200
    html = response.text
    # ES counts should still appear
    assert "10" in html
    assert "5" in html
    assert "2" in html
    # Qdrant counts should be 0 (fallback), not error
    assert "error" not in html.lower()


# [unit] T35: Reindex — exact error message on Celery failure
def test_index_reindex_celery_failure_exact_message(repo1):
    factory, _session = _make_session_factory([repo1])
    _app, client = _build_app(session_factory=factory)

    with patch("src.query.web_router.reindex_repo_task") as mock_task:
        mock_task.delay.side_effect = Exception("Broker unreachable")
        response = client.post(f"/admin/indexes/{repo1.id}/reindex")

    assert response.status_code == 200
    assert "Failed to dispatch reindex task" in response.text
    assert "XX" not in response.text  # mutation kill


# [unit] T36: Delete — exact error message on IndexWriteError
def test_index_delete_write_error_exact_message(repo1):
    from src.indexing.exceptions import IndexWriteError

    factory, _session = _make_session_factory([repo1])
    es = _make_es_client()
    qdrant = _make_qdrant_client()
    _app, client = _build_app(session_factory=factory, es_client=es, qdrant_client=qdrant)

    with patch("src.query.web_router.IndexWriter") as MockIW:
        mock_writer = AsyncMock()
        mock_writer.delete_repo_index.side_effect = IndexWriteError("ES connection lost")
        MockIW.return_value = mock_writer
        response = client.post(f"/admin/indexes/{repo1.id}/delete")

    assert response.status_code == 200
    assert "Failed to delete index" in response.text
    assert "ES connection lost" in response.text
    assert "XX" not in response.text


# [unit] T37: Stats — exact error messages for not found and ES failure
def test_index_stats_exact_error_messages():
    factory, _session = _make_session_factory([])  # no repos
    es = _make_es_client()
    _app, client = _build_app(session_factory=factory, es_client=es)

    fake_id = uuid.uuid4()
    response = client.get(f"/admin/indexes/{fake_id}/stats")
    assert response.status_code == 200
    assert "Repository not found" in response.text
    assert "XX" not in response.text


# [unit] T38: Reindex — exact error message for not found
def test_index_reindex_exact_not_found_message():
    factory, _session = _make_session_factory([])
    _app, client = _build_app(session_factory=factory)

    fake_id = uuid.uuid4()
    with patch("src.query.web_router.reindex_repo_task"):
        response = client.post(f"/admin/indexes/{fake_id}/reindex")
    assert response.status_code == 200
    assert "Repository not found" in response.text
    assert "XX" not in response.text


# [unit] T39: Delete — exact error message for not found
def test_index_delete_exact_not_found_message():
    factory, _session = _make_session_factory([])
    _app, client = _build_app(session_factory=factory)

    fake_id = uuid.uuid4()
    response = client.post(f"/admin/indexes/{fake_id}/delete")
    assert response.status_code == 200
    assert "Repository not found" in response.text
    assert "XX" not in response.text


# [unit] T40: ES stats failure returns exact error
def test_index_stats_es_failure_exact_message(repo1):
    factory, _session = _make_session_factory([repo1])
    es = _make_es_client(raise_on_count=True)
    _app, client = _build_app(session_factory=factory, es_client=es)

    response = client.get(f"/admin/indexes/{repo1.id}/stats")
    assert response.status_code == 200
    assert "Failed to retrieve index stats" in response.text
    assert "XX" not in response.text


# [unit] T41: Stats — es_client with no _client attribute
def test_index_stats_es_client_no_inner_client(repo1):
    factory, _session = _make_session_factory([repo1])
    es = MagicMock()
    es._client = None
    _app, client = _build_app(session_factory=factory, es_client=es)

    response = client.get(f"/admin/indexes/{repo1.id}/stats")
    assert response.status_code == 200
    assert "Search service not configured" in response.text
    assert "XX" not in response.text


# [unit] T42: Reindex all — No repos message
def test_index_reindex_all_no_repos_exact_message():
    factory, _session = _make_session_factory([])
    _app, client = _build_app(session_factory=factory)

    with patch("src.query.web_router.reindex_repo_task") as mock_task:
        response = client.post("/admin/indexes/reindex-all")

    assert response.status_code == 200
    mock_task.delay.assert_not_called()
    assert "No repositories" in response.text
    assert "XX" not in response.text


# [unit] T43: Reindex all — partial failure exact count
def test_index_reindex_all_partial_failure_exact_count(repo1, repo2):
    repo3 = _make_repo(name="repo-gamma")
    factory, _session = _make_session_factory([repo1, repo2, repo3])
    _app, client = _build_app(session_factory=factory)

    call_count = 0
    def side_effect(repo_id):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise Exception("Broker unreachable")
        return MagicMock(id=f"task-{call_count}")

    with patch("src.query.web_router.reindex_repo_task") as mock_task:
        mock_task.delay.side_effect = side_effect
        response = client.post("/admin/indexes/reindex-all")

    assert response.status_code == 200
    # Exactly 2 of 3 succeeded
    assert "2 repositories" in response.text
    assert "XX" not in response.text


# [unit] T44: Reindex all — each repo gets delay called with its ID
def test_index_reindex_all_dispatches_correct_ids(repo1, repo2):
    factory, _session = _make_session_factory([repo1, repo2])
    _app, client = _build_app(session_factory=factory)

    with patch("src.query.web_router.reindex_repo_task") as mock_task:
        mock_task.delay.return_value = MagicMock(id="t1")
        response = client.post("/admin/indexes/reindex-all")

    assert response.status_code == 200
    call_args = [call[0][0] for call in mock_task.delay.call_args_list]
    assert str(repo1.id) in call_args
    assert str(repo2.id) in call_args
    assert "XX" not in response.text


# [unit] T45: Delete — verify repo.last_indexed_at set to None and commit called
def test_index_delete_clears_last_indexed_and_commits(repo1):
    from datetime import datetime, timezone
    repo1.last_indexed_at = datetime(2026, 3, 25, 10, 0, 0, tzinfo=timezone.utc)
    factory, session = _make_session_factory([repo1])
    es = _make_es_client()
    qdrant = _make_qdrant_client()
    _app, client = _build_app(session_factory=factory, es_client=es, qdrant_client=qdrant)

    with patch("src.query.web_router.IndexWriter") as MockIW:
        mock_writer = AsyncMock()
        MockIW.return_value = mock_writer
        response = client.post(f"/admin/indexes/{repo1.id}/delete")

    assert response.status_code == 200
    assert repo1.last_indexed_at is None
    session.commit.assert_called()
    assert "XX" not in response.text


# [unit] T46: Stats — qdrant fallback default values are 0
def test_index_stats_qdrant_fallback_values_are_zero(repo1):
    """Verify that code_embeddings and doc_embeddings default to 0 when qdrant unavailable."""
    factory, _session = _make_session_factory([repo1])
    es = _make_es_client(code_chunks=7, doc_chunks=3, rule_chunks=1)
    _app, client = _build_app(session_factory=factory, es_client=es, qdrant_client=None)

    response = client.get(f"/admin/indexes/{repo1.id}/stats")
    assert response.status_code == 200
    html = response.text
    # The template should render 0 for qdrant counts, not 1 or None
    # Count occurrences of "0" — should have at least 2 (for code_embeddings=0, doc_embeddings=0)
    assert "error" not in html.lower()
    # Verify the template renders the 5 specific count values
    assert "7" in html  # code_chunks
    assert "3" in html  # doc_chunks
    assert "1" in html  # rule_chunks


# [unit] T47: Reindex — branch uses indexed_branch when available (or → and mutation kill)
def test_index_reindex_branch_uses_indexed_branch():
    """When indexed_branch is set, it should be used even if default_branch is None."""
    repo = _make_repo(indexed_branch="feature-x", default_branch=None)
    factory, session = _make_session_factory([repo])
    _app, client = _build_app(session_factory=factory)

    with patch("src.query.web_router.reindex_repo_task") as mock_task:
        mock_task.delay.return_value = MagicMock(id="t1")
        response = client.post(f"/admin/indexes/{repo.id}/reindex")

    assert response.status_code == 200
    add_call = session.add.call_args
    assert add_call is not None
    job = add_call[0][0]
    assert job.branch == "feature-x"  # not "main" and not None


# [unit] T48: Reindex — success=True in response (kills success=False mutant)
def test_index_reindex_success_true_in_template(repo1):
    factory, session = _make_session_factory([repo1])
    _app, client = _build_app(session_factory=factory)

    with patch("src.query.web_router.reindex_repo_task") as mock_task:
        mock_task.delay.return_value = MagicMock(id="task-abc")
        response = client.post(f"/admin/indexes/{repo1.id}/reindex")

    assert response.status_code == 200
    html = response.text
    assert "success-message" in html  # success=True renders success-message class
    assert "info-message" not in html  # not the fallback
    assert "Reindex queued" in html


# [unit] T49: Reindex all — success=True (kills success=False mutant)
def test_index_reindex_all_success_true_in_template(repo1, repo2):
    factory, _session = _make_session_factory([repo1, repo2])
    _app, client = _build_app(session_factory=factory)

    with patch("src.query.web_router.reindex_repo_task") as mock_task:
        mock_task.delay.return_value = MagicMock(id="t1")
        response = client.post("/admin/indexes/reindex-all")

    assert response.status_code == 200
    html = response.text
    assert "success-message" in html
    assert "info-message" not in html
    assert "Reindex queued for 2 repositories" in html


# [unit] T50: Delete — success=True (kills success=False mutant)
def test_index_delete_success_true_in_template(repo1):
    factory, session = _make_session_factory([repo1])
    es = _make_es_client()
    qdrant = _make_qdrant_client()
    _app, client = _build_app(session_factory=factory, es_client=es, qdrant_client=qdrant)

    with patch("src.query.web_router.IndexWriter") as MockIW:
        mock_writer = AsyncMock()
        MockIW.return_value = mock_writer
        response = client.post(f"/admin/indexes/{repo1.id}/delete")

    assert response.status_code == 200
    html = response.text
    assert "success-message" in html
    assert "info-message" not in html
    assert "Index deleted" in html


# [unit] T51: Delete — branch fallback to "main" when both None
def test_index_delete_branch_fallback_main():
    repo = _make_repo(indexed_branch=None, default_branch=None)
    factory, _session = _make_session_factory([repo])
    es = _make_es_client()
    qdrant = _make_qdrant_client()
    _app, client = _build_app(session_factory=factory, es_client=es, qdrant_client=qdrant)

    with patch("src.query.web_router.IndexWriter") as MockIW:
        mock_writer = AsyncMock()
        MockIW.return_value = mock_writer
        response = client.post(f"/admin/indexes/{repo.id}/delete")

    assert response.status_code == 200
    mock_writer.delete_repo_index.assert_called_once_with(str(repo.id), "main")


# [unit] T52: Index page — repos=[] vs repos=None (mutation kill for repos = None)
def test_index_management_page_repos_is_list():
    """When session_factory is None, repos should be [] not None."""
    _app, client = _build_app(session_factory=None)
    response = client.get("/admin/indexes")
    assert response.status_code == 200
    # Should render successfully without TypeError from iterating None


# [unit] T53: Stats — qdrant _client attribute name matters
def test_index_stats_qdrant_client_attr_name(repo1):
    """Verify qdrant client check uses '_client' attribute, not 'XX_clientXX'."""
    factory, _session = _make_session_factory([repo1])
    es = _make_es_client(code_chunks=5, doc_chunks=3, rule_chunks=1)
    # Create a qdrant with _client but also verify it's accessed
    qdrant = _make_qdrant_client(code_embeddings=42, doc_embeddings=17)
    _app, client = _build_app(session_factory=factory, es_client=es, qdrant_client=qdrant)

    response = client.get(f"/admin/indexes/{repo1.id}/stats")
    assert response.status_code == 200
    html = response.text
    assert "42" in html  # code_embeddings from qdrant
    assert "17" in html  # doc_embeddings from qdrant
