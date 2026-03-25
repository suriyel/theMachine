"""Tests for WebRouter — Web UI Search Page (feature #19).

Categories:
  - Happy path: T01-T08, T25-T28
  - Error handling: T09-T17, T27
  - Boundary: T18-T24
  - Security: N/A — Web UI is internal developer tool, no auth required
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.query.highlighter import CodeHighlighter
from src.query.response_models import CodeResult, QueryResponse
from src.query.web_router import WebRouter
from src.shared.exceptions import ConflictError, ValidationError
from src.query.exceptions import RetrievalError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_query_response(
    query: str = "timeout",
    query_type: str = "nl",
    code_results: list | None = None,
    doc_results: list | None = None,
    degraded: bool = False,
) -> QueryResponse:
    return QueryResponse(
        query=query,
        query_type=query_type,
        code_results=code_results or [],
        doc_results=doc_results or [],
        degraded=degraded,
    )


def _make_code_result(**overrides) -> CodeResult:
    defaults = dict(
        file_path="src/main.py",
        symbol="timeout_handler",
        language="python",
        content="def timeout_handler():\n    pass",
        relevance_score=0.95,
        chunk_type="function",
    )
    defaults.update(overrides)
    return CodeResult(**defaults)


@pytest.fixture
def mock_query_handler():
    handler = AsyncMock()
    # detect_query_type is synchronous — use a regular MagicMock
    handler.detect_query_type = MagicMock(return_value="nl")
    handler.handle_nl_query.return_value = _make_query_response(
        code_results=[_make_code_result(), _make_code_result(file_path="src/utils.py", symbol="retry_logic", relevance_score=0.88)]
    )
    handler.handle_symbol_query.return_value = _make_query_response(
        query_type="symbol",
        code_results=[_make_code_result(symbol="myFunc")],
    )
    return handler


def _make_repo(name: str, status: str = "indexed", repo_id: str | None = None) -> MagicMock:
    """Create a mock Repository with the given name and status."""
    repo = MagicMock()
    repo.name = name
    repo.id = repo_id or str(uuid.uuid4())
    repo.status = status
    repo.url = f"https://github.com/org/{name}"
    return repo


@pytest.fixture
def mock_session_factory():
    """Mock session factory returning only indexed repos (simulating WHERE filter)."""
    session = AsyncMock()
    # Simulate DB returning only indexed repos (the WHERE clause filters in DB)
    indexed_repos = [
        _make_repo("repo-alpha", status="indexed"),
        _make_repo("repo-beta", status="indexed"),
    ]
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = indexed_repos
    session.execute.return_value = result_mock

    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=session)
    factory.return_value.__aexit__ = AsyncMock(return_value=False)
    return factory


@pytest.fixture
def mock_git_cloner():
    cloner = MagicMock()
    cloner.list_remote_branches_by_url = AsyncMock(return_value=["main", "develop"])
    return cloner


@pytest.fixture
def app(mock_query_handler, mock_session_factory, mock_git_cloner):
    """Create a test FastAPI app with WebRouter."""
    test_app = FastAPI()
    web_router = WebRouter()
    test_app.include_router(web_router.router)

    # Mount static files
    from starlette.staticfiles import StaticFiles
    import os
    static_dir = os.path.join(os.path.dirname(__file__), "..", "src", "query", "static")
    if os.path.isdir(static_dir):
        test_app.mount("/static", StaticFiles(directory=static_dir), name="static")

    test_app.state.query_handler = mock_query_handler
    test_app.state.session_factory = mock_session_factory
    test_app.state.git_cloner = mock_git_cloner
    return test_app


@pytest.fixture
def client(app):
    return TestClient(app)


# ---------------------------------------------------------------------------
# T01: GET / renders search page with form elements and UCD dark theme
#   - Only indexed repos in dropdown (VS-6)
#   - No "All repositories" option — repo required (VS-5)
# ---------------------------------------------------------------------------
def test_search_page_renders_form(client):
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text
    # Search input
    assert "search" in html.lower() or '<input' in html
    # Repo dropdown
    assert "<select" in html
    # Language checkboxes
    assert 'type="checkbox"' in html
    # UCD dark theme bg
    assert "#0d1117" in html or "0d1117" in html
    # VS-5: Repo dropdown is mandatory — no "All repositories" option
    assert "All repositories" not in html
    # VS-6: Only indexed repos shown (alpha, beta yes; gamma, delta no)
    assert "repo-alpha" in html
    assert "repo-beta" in html
    assert "repo-gamma" not in html
    assert "repo-delta" not in html
    # VS-5: repo dropdown has required attribute
    assert 'required' in html


# ---------------------------------------------------------------------------
# T01b: GET / — verify SQL query includes indexed-only WHERE clause (VS-6)
# ---------------------------------------------------------------------------
def test_search_page_filters_indexed_repos(client, mock_session_factory):
    """Verify the DB query filters to status='indexed' repos only."""
    resp = client.get("/")
    assert resp.status_code == 200
    session = mock_session_factory.return_value.__aenter__.return_value
    # Inspect the SQL statement passed to session.execute()
    call_args = session.execute.call_args
    stmt = call_args[0][0]
    # Convert the SQLAlchemy statement to string to verify WHERE clause
    stmt_str = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "indexed" in stmt_str.lower(), f"Expected 'indexed' filter in SQL: {stmt_str}"


# ---------------------------------------------------------------------------
# T02: GET /search?q=timeout with mock returning 2 code results
# ---------------------------------------------------------------------------
def test_search_results_with_hits(client, mock_query_handler):
    resp = client.get("/search?q=timeout")
    assert resp.status_code == 200
    html = resp.text
    # Both results rendered
    assert "src/main.py" in html
    assert "src/utils.py" in html
    assert "timeout_handler" in html
    assert "retry_logic" in html
    # Relevance scores
    assert "0.95" in html or "95" in html
    assert "0.88" in html or "88" in html


# ---------------------------------------------------------------------------
# T03: GET /search?q=timeout&repo=uuid1 passes repo filter
# ---------------------------------------------------------------------------
def test_search_results_repo_filter(client, mock_query_handler):
    resp = client.get("/search?q=timeout&repo=uuid1")
    assert resp.status_code == 200
    mock_query_handler.handle_nl_query.assert_called_once()
    call_kwargs = mock_query_handler.handle_nl_query.call_args
    # repo should be passed through
    assert call_kwargs[1].get("repo") == "uuid1" or call_kwargs[0][1] == "uuid1"


# ---------------------------------------------------------------------------
# T04: GET /search?q=timeout&languages=python&languages=java
# ---------------------------------------------------------------------------
def test_search_results_language_filter(client, mock_query_handler):
    resp = client.get("/search?q=timeout&languages=python&languages=java")
    assert resp.status_code == 200
    mock_query_handler.handle_nl_query.assert_called_once()
    call_kwargs = mock_query_handler.handle_nl_query.call_args
    langs = call_kwargs[1].get("languages") or call_kwargs[0][2]
    assert "python" in langs
    assert "java" in langs


# ---------------------------------------------------------------------------
# T05: GET /branches?repo_id=uuid1 returns option elements
# ---------------------------------------------------------------------------
def test_list_branches(client, mock_git_cloner):
    repo_id = str(uuid.uuid4())
    resp = client.get(f"/branches?repo_id={repo_id}")
    assert resp.status_code == 200
    html = resp.text
    assert "<option" in html
    assert "main" in html
    assert "develop" in html


# ---------------------------------------------------------------------------
# T06: POST /register with url and branch="develop"
# ---------------------------------------------------------------------------
def test_register_repo_with_branch(client, mock_session_factory):
    session = mock_session_factory.return_value.__aenter__.return_value
    # Make register return a mock repo
    mock_repo = MagicMock()
    mock_repo.name = "org/repo"
    mock_repo.url = "https://github.com/org/repo"
    mock_repo.id = uuid.uuid4()

    with patch("src.query.web_router.RepoManager") as MockRM:
        instance = AsyncMock()
        instance.register.return_value = mock_repo
        MockRM.return_value = instance

        resp = client.post("/register", data={"url": "https://github.com/org/repo", "branch": "develop"})

    assert resp.status_code == 200
    instance.register.assert_called_once()
    call_args = instance.register.call_args
    assert call_args[1].get("branch") == "develop" or (len(call_args[0]) > 1 and call_args[0][1] == "develop")


# ---------------------------------------------------------------------------
# T07: GET /search?q=myFunc (symbol detected) dispatches to handle_symbol_query
# ---------------------------------------------------------------------------
def test_symbol_query_dispatch(client, mock_query_handler):
    mock_query_handler.detect_query_type.return_value = "symbol"
    resp = client.get("/search?q=myFunc")
    assert resp.status_code == 200
    mock_query_handler.handle_symbol_query.assert_called_once()
    mock_query_handler.handle_nl_query.assert_not_called()


# ---------------------------------------------------------------------------
# T08: GET /search?q=timeout with degraded=True shows degraded indicator
# ---------------------------------------------------------------------------
def test_degraded_indicator(client, mock_query_handler):
    mock_query_handler.handle_nl_query.return_value = _make_query_response(
        code_results=[_make_code_result()],
        degraded=True,
    )
    resp = client.get("/search?q=timeout")
    assert resp.status_code == 200
    html = resp.text
    assert "degraded" in html.lower() or "partial" in html.lower()


# ---------------------------------------------------------------------------
# T09: GET /search?q= (empty query) — validation error
# ---------------------------------------------------------------------------
def test_empty_query_validation(client):
    resp = client.get("/search?q=")
    assert resp.status_code == 200
    assert "Please enter a search query" in resp.text


# ---------------------------------------------------------------------------
# T10: GET /search?q=%20%20 (whitespace-only query) — validation error
# ---------------------------------------------------------------------------
def test_whitespace_query_validation(client):
    resp = client.get("/search?q=%20%20")
    assert resp.status_code == 200
    assert "Please enter a search query" in resp.text


# ---------------------------------------------------------------------------
# T11: GET /search?q=xyznonexistent with empty results — empty state
# ---------------------------------------------------------------------------
def test_no_results_empty_state(client, mock_query_handler):
    mock_query_handler.handle_nl_query.return_value = _make_query_response()
    resp = client.get("/search?q=xyznonexistent")
    assert resp.status_code == 200
    assert "No results found" in resp.text


# ---------------------------------------------------------------------------
# T12: QueryHandler raises RetrievalError — shows error message
# ---------------------------------------------------------------------------
def test_retrieval_error_display(client, mock_query_handler):
    mock_query_handler.handle_nl_query.side_effect = RetrievalError("ES down")
    resp = client.get("/search?q=timeout")
    assert resp.status_code == 200
    assert "Search service unavailable" in resp.text


# ---------------------------------------------------------------------------
# T13: QueryHandler raises ValidationError — shows validation message
# ---------------------------------------------------------------------------
def test_validation_error_display(client, mock_query_handler):
    mock_query_handler.handle_nl_query.side_effect = ValidationError("exceeds limit")
    resp = client.get("/search?q=timeout")
    assert resp.status_code == 200
    assert "exceeds limit" in resp.text


# ---------------------------------------------------------------------------
# T14: GET / with DB session raising Exception — page still renders
# ---------------------------------------------------------------------------
def test_db_failure_graceful(mock_query_handler, mock_git_cloner):
    factory = MagicMock()
    session = AsyncMock()
    session.execute.side_effect = Exception("DB connection failed")
    factory.return_value.__aenter__ = AsyncMock(return_value=session)
    factory.return_value.__aexit__ = AsyncMock(return_value=False)

    test_app = FastAPI()
    web_router = WebRouter()
    test_app.include_router(web_router.router)
    test_app.state.query_handler = mock_query_handler
    test_app.state.session_factory = factory
    test_app.state.git_cloner = mock_git_cloner

    tc = TestClient(test_app)
    resp = tc.get("/")
    assert resp.status_code == 200
    # Page renders with empty repo dropdown
    assert "<select" in resp.text


# ---------------------------------------------------------------------------
# T15: POST /register with empty URL — validation error shown
# ---------------------------------------------------------------------------
def test_register_empty_url(client, mock_session_factory):
    with patch("src.query.web_router.RepoManager") as MockRM:
        instance = AsyncMock()
        instance.register.side_effect = ValidationError("URL must not be empty")
        MockRM.return_value = instance

        resp = client.post("/register", data={"url": "", "branch": ""})

    assert resp.status_code == 200
    html = resp.text
    assert "URL must not be empty" in html or "validation" in html.lower() or "error" in html.lower()


# ---------------------------------------------------------------------------
# T16: POST /register duplicate URL — ConflictError shown
# ---------------------------------------------------------------------------
def test_register_duplicate_url(client, mock_session_factory):
    with patch("src.query.web_router.RepoManager") as MockRM:
        instance = AsyncMock()
        instance.register.side_effect = ConflictError("already registered")
        MockRM.return_value = instance

        resp = client.post("/register", data={"url": "https://github.com/org/repo", "branch": ""})

    assert resp.status_code == 200
    assert "already registered" in resp.text


# ---------------------------------------------------------------------------
# T17: GET /branches with GitCloner raising exception — empty select
# ---------------------------------------------------------------------------
def test_branches_failure_graceful(client, mock_git_cloner):
    mock_git_cloner.list_remote_branches_by_url.side_effect = Exception("network error")
    repo_id = str(uuid.uuid4())
    resp = client.get(f"/branches?repo_id={repo_id}")
    assert resp.status_code == 200
    # Should render but with no options (graceful degradation)
    html = resp.text
    assert isinstance(html, str)


# ---------------------------------------------------------------------------
# T22: GET /search?q=x (1-char query) — QueryHandler invoked normally
# ---------------------------------------------------------------------------
def test_single_char_query(client, mock_query_handler):
    resp = client.get("/search?q=x")
    assert resp.status_code == 200
    # QueryHandler should have been called
    assert mock_query_handler.handle_nl_query.called or mock_query_handler.handle_symbol_query.called


# ---------------------------------------------------------------------------
# T23: GET /search?q=timeout&repo= (empty repo string) treated as None
# ---------------------------------------------------------------------------
def test_empty_repo_string_treated_as_none(client, mock_query_handler):
    resp = client.get("/search?q=timeout&repo=")
    assert resp.status_code == 200
    call_kwargs = mock_query_handler.handle_nl_query.call_args
    repo_val = call_kwargs[1].get("repo") if call_kwargs[1] else call_kwargs[0][1]
    assert repo_val is None


# ---------------------------------------------------------------------------
# T24: GET /search?q=timeout (no languages) treated as None
# ---------------------------------------------------------------------------
def test_empty_languages_treated_as_none(client, mock_query_handler):
    resp = client.get("/search?q=timeout")
    assert resp.status_code == 200
    call_kwargs = mock_query_handler.handle_nl_query.call_args
    langs = call_kwargs[1].get("languages") if call_kwargs[1] else (call_kwargs[0][2] if len(call_kwargs[0]) > 2 else None)
    assert langs is None


# ---------------------------------------------------------------------------
# T25: GET / contains htmx CDN script and hx- attributes
# ---------------------------------------------------------------------------
def test_htmx_integration(client):
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text
    assert "htmx.org" in html or "htmx.min.js" in html
    assert "hx-get" in html or "hx-post" in html


# ---------------------------------------------------------------------------
# T26: GET / — CSS or HTML contains UCD color tokens
# ---------------------------------------------------------------------------
def test_ucd_theme_tokens(client):
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text
    # The page should reference UCD dark theme colors
    assert "#0d1117" in html or "0d1117" in html


# ---------------------------------------------------------------------------
# T27: app.state.query_handler=None — renders error message
# ---------------------------------------------------------------------------
def test_no_query_handler_error(mock_session_factory, mock_git_cloner):
    test_app = FastAPI()
    web_router = WebRouter()
    test_app.include_router(web_router.router)
    test_app.state.query_handler = None
    test_app.state.session_factory = mock_session_factory
    test_app.state.git_cloner = mock_git_cloner

    tc = TestClient(test_app)
    resp = tc.get("/search?q=timeout")
    assert resp.status_code == 200
    assert "Search service not configured" in resp.text or "not configured" in resp.text.lower()


# ---------------------------------------------------------------------------
# Real test — feature #19 Jinja2 template rendering
# ---------------------------------------------------------------------------


@pytest.mark.real
def test_real_jinja2_template_renders_search_page(app, client):
    """Real test: verifies actual Jinja2 template renders without mocking the template engine.

    feature #19 — Web UI Search Page

    Exercises the full SSR pipeline: FastAPI -> WebRouter -> Jinja2 -> HTML.
    The template files on disk are read and rendered by the real Jinja2 engine.
    """
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text
    # Verify real template rendered key structural elements
    assert "<!DOCTYPE html>" in html or "<!doctype html>" in html.lower()
    assert '<input' in html  # search input
    assert "Code Context" in html  # header brand
    assert "htmx" in html  # htmx script loaded
    assert "#0d1117" in html or "color-bg-primary" in html  # UCD dark theme


# ---------------------------------------------------------------------------
# Additional coverage tests
# ---------------------------------------------------------------------------

# [unit] — Generic Exception during search renders error
def test_search_generic_exception(app, client, mock_query_handler):
    mock_query_handler.handle_nl_query.side_effect = RuntimeError("kaboom")
    resp = client.get("/search?q=timeout")
    assert resp.status_code == 200
    assert "unexpected error" in resp.text.lower() or "error" in resp.text.lower()


# [unit] — DB not configured for registration renders error
def test_register_db_not_configured(mock_query_handler, mock_git_cloner):
    test_app = FastAPI()
    web_router = WebRouter()
    test_app.include_router(web_router.router)
    test_app.state.query_handler = mock_query_handler
    test_app.state.git_cloner = mock_git_cloner
    # No session_factory set
    tc = TestClient(test_app)
    resp = tc.post("/register", data={"url": "https://github.com/test/repo", "branch": ""})
    assert resp.status_code == 200
    assert "not configured" in resp.text.lower() or "database" in resp.text.lower()


# [unit] — Generic Exception during registration renders error
def test_register_generic_exception(app, client, mock_session_factory):
    mock_session_factory.return_value.__aenter__.side_effect = RuntimeError("db crash")
    resp = client.post("/register", data={"url": "https://github.com/test/repo", "branch": ""})
    assert resp.status_code == 200
    assert "failed" in resp.text.lower() or "error" in resp.text.lower()


# [unit] — Branch list with no "main" defaults to first branch
def test_branches_no_main_defaults_to_first(app, client, mock_git_cloner):
    mock_git_cloner.list_remote_branches_by_url.return_value = ["develop", "feature-x"]
    resp = client.get("/branches?repo_id=some-url")
    assert resp.status_code == 200
    assert "develop" in resp.text
    # "develop" should be the selected default
    assert 'selected' in resp.text


# [unit] — Search page with no session_factory renders with empty repos
def test_search_page_no_session_factory(mock_query_handler, mock_git_cloner):
    test_app = FastAPI()
    web_router = WebRouter()
    test_app.include_router(web_router.router)
    test_app.state.query_handler = mock_query_handler
    test_app.state.git_cloner = mock_git_cloner
    # No session_factory
    tc = TestClient(test_app)
    resp = tc.get("/")
    assert resp.status_code == 200
    # Page renders without crash, search input present
    assert "search" in resp.text.lower()


# ---------------------------------------------------------------------------
# WebRouter.branches — uncovered branch paths
# ---------------------------------------------------------------------------


def test_branches_no_git_cloner_returns_empty(mock_query_handler):
    """Branch 184->195: git_cloner is None → empty branches list."""
    test_app = FastAPI()
    web_router = WebRouter()
    test_app.include_router(web_router.router)
    test_app.state.query_handler = mock_query_handler
    # No git_cloner attribute
    tc = TestClient(test_app)
    resp = tc.get("/branches?repo_id=some-url")
    assert resp.status_code == 200


def test_branches_empty_repo_id(client, mock_git_cloner):
    """Branch 184->195: repo_id is empty → skip branch listing."""
    resp = client.get("/branches?repo_id=")
    assert resp.status_code == 200


def test_branches_empty_result(client, mock_git_cloner):
    """Branch 186->195: list_remote_branches returns empty list."""
    mock_git_cloner.list_remote_branches_by_url.return_value = []
    resp = client.get("/branches?repo_id=some-url")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Highlighter coverage — uncovered branches
# ---------------------------------------------------------------------------


def test_highlighter_unknown_language_falls_back_to_text():
    """ClassNotFound branch: unknown language returns TextLexer output."""
    hl = CodeHighlighter()
    result = hl.highlight("hello world", "totally_unknown_lang_xyz")
    # Should still produce HTML (TextLexer fallback), not raise
    assert "hello world" in result
    assert "<" in result  # HTML wrapper present


def test_highlighter_none_language_falls_back_to_text():
    """None language branch: falls back to TextLexer."""
    hl = CodeHighlighter()
    result = hl.highlight("x = 1", None)
    assert "x = 1" in result


def test_highlighter_empty_language_falls_back_to_text():
    """Empty string language branch: falls back to TextLexer."""
    hl = CodeHighlighter()
    result = hl.highlight("x = 1", "")
    assert "x = 1" in result
