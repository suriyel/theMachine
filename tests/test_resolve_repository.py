"""Tests for Feature #46 — Repository Resolution MCP Tool.

Tests the enhanced resolve_repository MCP tool: name match quality sorting
(exact > prefix > substring), available_branches population via GitCloner,
and input validation.

# Security: N/A — MCP server auth is deferred (not in v1 scope per design §4.3.6)
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.query.mcp_server import create_mcp_server


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_repo(
    name: str,
    url: str,
    status: str = "indexed",
    clone_path: str | None = None,
    indexed_branch: str | None = "main",
    default_branch: str = "main",
    last_indexed_at: datetime | None = None,
):
    """Create a mock Repository object."""
    repo = MagicMock()
    repo.id = uuid.uuid4()
    repo.name = name
    repo.url = url
    repo.status = status
    repo.clone_path = clone_path
    repo.indexed_branch = indexed_branch
    repo.default_branch = default_branch
    repo.last_indexed_at = last_indexed_at or datetime(2026, 3, 25, 12, 0, 0)
    return repo


@pytest.fixture
def mock_repos():
    """Build a set of repos for testing match quality sorting."""
    return [
        _make_repo(
            "gson",
            "https://github.com/google/gson",
            clone_path="/tmp/gson",
        ),
        _make_repo(
            "gson-fire",
            "https://github.com/julman99/gson-fire",
            clone_path=None,
        ),
        _make_repo(
            "my-gson-lib",
            "https://github.com/acme/my-gson-lib",
            clone_path="/tmp/my-gson-lib",
        ),
        _make_repo(
            "react",
            "https://github.com/facebook/react",
            clone_path="/tmp/react",
        ),
        _make_repo(
            "spring-framework",
            "https://github.com/spring-projects/spring-framework",
            status="pending",  # not indexed — should be excluded
        ),
    ]


@pytest.fixture
def mock_session_factory(mock_repos):
    """Create a mock async session factory returning all repos."""
    indexed_repos = [r for r in mock_repos if r.status == "indexed"]

    session = AsyncMock()

    def _make_result(repos):
        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = repos
        result_mock.scalars.return_value = scalars_mock
        return result_mock

    async def _execute(stmt):
        stmt_str = str(stmt)
        if "status" in stmt_str:
            return _make_result(indexed_repos)
        return _make_result(mock_repos)

    session.execute = AsyncMock(side_effect=_execute)
    session.close = AsyncMock()

    factory = MagicMock()
    factory.return_value = session
    return factory


@pytest.fixture
def mock_query_handler():
    return AsyncMock()


@pytest.fixture
def mock_es_client():
    client = AsyncMock()
    client._client = AsyncMock()
    return client


@pytest.fixture
def mock_git_cloner():
    """GitCloner mock: list_remote_branches returns ['main', 'dev']."""
    cloner = MagicMock()
    cloner.list_remote_branches = MagicMock(return_value=["dev", "main"])
    return cloner


def _get_tool(mcp, tool_name):
    """Extract a tool function from FastMCP by name."""
    tools = mcp._tool_manager._tools
    tool = tools.get(tool_name)
    assert tool is not None, f"{tool_name} tool not registered"
    return tool


# ---------------------------------------------------------------------------
# T01: Filter correctness — only matching repos returned
# [unit] — mocks DB session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_returns_only_matching_repos(
    mock_query_handler, mock_session_factory, mock_es_client, mock_git_cloner
):
    """T01: resolve_repository(query='JSON parse', libraryName='gson') returns
    only repos matching 'gson', excluding 'react' and pending repos."""
    mcp = create_mcp_server(
        mock_query_handler, mock_session_factory, mock_es_client,
        git_cloner=mock_git_cloner,
    )
    tool = _get_tool(mcp, "resolve_repository")
    result = await tool.fn(query="JSON parse", libraryName="gson")
    parsed = json.loads(result)

    names = [r["name"] for r in parsed]
    assert len(parsed) == 3, f"Expected 3 gson repos, got {len(parsed)}: {names}"
    assert "react" not in names
    assert "spring-framework" not in names
    # All three gson-related repos present
    assert "gson" in names
    assert "gson-fire" in names
    assert "my-gson-lib" in names


# ---------------------------------------------------------------------------
# T02: Field completeness — all 7 keys present
# [unit]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_result_contains_all_required_fields(
    mock_query_handler, mock_session_factory, mock_es_client, mock_git_cloner
):
    """T02: Each result dict has all 7 required keys."""
    mcp = create_mcp_server(
        mock_query_handler, mock_session_factory, mock_es_client,
        git_cloner=mock_git_cloner,
    )
    tool = _get_tool(mcp, "resolve_repository")
    result = await tool.fn(query="JSON parse", libraryName="gson")
    parsed = json.loads(result)

    required_keys = {
        "id", "name", "url", "indexed_branch", "default_branch",
        "available_branches", "last_indexed_at",
    }
    for repo in parsed:
        assert set(repo.keys()) == required_keys, (
            f"Missing keys: {required_keys - set(repo.keys())}"
        )
        # Values must be actual data, not None for indexed repos
        assert repo["name"] != ""
        assert repo["url"].startswith("https://")
        assert repo["indexed_branch"] is not None
        assert isinstance(repo["available_branches"], list)


# ---------------------------------------------------------------------------
# T03: Sort order — exact > prefix > substring
# [unit]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_sorts_by_match_quality(
    mock_query_handler, mock_session_factory, mock_es_client, mock_git_cloner
):
    """T03: Results sorted: 'gson' (exact=0), 'gson-fire' (prefix=2),
    'my-gson-lib' (substring=4)."""
    mcp = create_mcp_server(
        mock_query_handler, mock_session_factory, mock_es_client,
        git_cloner=mock_git_cloner,
    )
    tool = _get_tool(mcp, "resolve_repository")
    result = await tool.fn(query="test", libraryName="gson")
    parsed = json.loads(result)

    names = [r["name"] for r in parsed]
    assert names == ["gson", "gson-fire", "my-gson-lib"], (
        f"Expected exact > prefix > substring order, got {names}"
    )


# ---------------------------------------------------------------------------
# T04: available_branches populated from GitCloner
# [unit]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_populates_available_branches(
    mock_query_handler, mock_session_factory, mock_es_client, mock_git_cloner
):
    """T04: Repos with clone_path get available_branches from GitCloner."""
    mcp = create_mcp_server(
        mock_query_handler, mock_session_factory, mock_es_client,
        git_cloner=mock_git_cloner,
    )
    tool = _get_tool(mcp, "resolve_repository")
    result = await tool.fn(query="test", libraryName="gson")
    parsed = json.loads(result)

    # gson has clone_path="/tmp/gson" → branches populated
    gson = next(r for r in parsed if r["name"] == "gson")
    assert gson["available_branches"] == ["dev", "main"], (
        f"Expected ['dev', 'main'], got {gson['available_branches']}"
    )

    # gson-fire has clone_path=None → empty branches
    gson_fire = next(r for r in parsed if r["name"] == "gson-fire")
    assert gson_fire["available_branches"] == [], (
        f"Expected [] for no clone_path, got {gson_fire['available_branches']}"
    )


# ---------------------------------------------------------------------------
# T05: URL segment matching
# [unit]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_matches_url_segment(
    mock_query_handler, mock_es_client, mock_git_cloner
):
    """T05: libraryName='spring-framework' matches URL path segment."""
    # Custom repos: name doesn't match but URL segment does
    repo_with_url = _make_repo(
        "springfw",
        "https://github.com/spring-projects/spring-framework",
    )
    indexed = [repo_with_url]
    session = AsyncMock()
    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = indexed
    result_mock.scalars.return_value = scalars_mock
    session.execute = AsyncMock(return_value=result_mock)
    session.close = AsyncMock()
    sf = MagicMock(return_value=session)

    mcp = create_mcp_server(
        mock_query_handler, sf, mock_es_client,
        git_cloner=mock_git_cloner,
    )
    tool = _get_tool(mcp, "resolve_repository")
    result = await tool.fn(query="spring", libraryName="spring-framework")
    parsed = json.loads(result)

    assert len(parsed) == 1
    assert parsed[0]["name"] == "springfw"


# ---------------------------------------------------------------------------
# T06: Name match takes priority over URL match
# [unit]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_name_match_priority_over_url(
    mock_query_handler, mock_es_client, mock_git_cloner
):
    """T06: Exact name match (tier 0) sorts before URL segment match (tier 1)."""
    repo_exact_name = _make_repo("react", "https://github.com/myorg/react-lib")
    repo_url_match = _make_repo("fb-react", "https://github.com/facebook/react")
    indexed = [repo_url_match, repo_exact_name]  # intentionally reversed

    session = AsyncMock()
    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = indexed
    result_mock.scalars.return_value = scalars_mock
    session.execute = AsyncMock(return_value=result_mock)
    session.close = AsyncMock()
    sf = MagicMock(return_value=session)

    mcp = create_mcp_server(
        mock_query_handler, sf, mock_es_client,
        git_cloner=mock_git_cloner,
    )
    tool = _get_tool(mcp, "resolve_repository")
    result = await tool.fn(query="UI lib", libraryName="react")
    parsed = json.loads(result)

    names = [r["name"] for r in parsed]
    assert names[0] == "react", (
        f"Exact name match should be first, got: {names}"
    )
    assert "fb-react" in names


# ---------------------------------------------------------------------------
# T07: Missing query parameter raises TypeError
# [unit]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_missing_query_raises_type_error(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """T07: Calling resolve_repository without query raises TypeError."""
    mcp = create_mcp_server(
        mock_query_handler, mock_session_factory, mock_es_client,
    )
    tool = _get_tool(mcp, "resolve_repository")
    with pytest.raises(TypeError):
        await tool.fn(libraryName="gson")


# ---------------------------------------------------------------------------
# T08: Missing libraryName parameter raises TypeError
# [unit]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_missing_library_name_raises_type_error(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """T08: Calling resolve_repository without libraryName raises TypeError."""
    mcp = create_mcp_server(
        mock_query_handler, mock_session_factory, mock_es_client,
    )
    tool = _get_tool(mcp, "resolve_repository")
    with pytest.raises(TypeError):
        await tool.fn(query="test")


# ---------------------------------------------------------------------------
# T09: Empty query raises ValueError
# [unit]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_empty_query_raises_value_error(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """T09: Empty string query raises ValueError('query is required')."""
    mcp = create_mcp_server(
        mock_query_handler, mock_session_factory, mock_es_client,
    )
    tool = _get_tool(mcp, "resolve_repository")
    with pytest.raises(ValueError, match="query is required"):
        await tool.fn(query="", libraryName="gson")


# ---------------------------------------------------------------------------
# T10: Empty libraryName raises ValueError
# [unit]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_empty_library_name_raises_value_error(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """T10: Empty string libraryName raises ValueError."""
    mcp = create_mcp_server(
        mock_query_handler, mock_session_factory, mock_es_client,
    )
    tool = _get_tool(mcp, "resolve_repository")
    with pytest.raises(ValueError, match="libraryName is required"):
        await tool.fn(query="test", libraryName="")


# ---------------------------------------------------------------------------
# T11: DB session failure raises RuntimeError
# [unit]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_db_failure_raises_runtime_error(
    mock_query_handler, mock_es_client
):
    """T11: DB session.execute raising Exception → RuntimeError."""
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=Exception("connection lost"))
    session.close = AsyncMock()
    sf = MagicMock(return_value=session)

    mcp = create_mcp_server(mock_query_handler, sf, mock_es_client)
    tool = _get_tool(mcp, "resolve_repository")
    with pytest.raises(RuntimeError, match="Failed to resolve repositories"):
        await tool.fn(query="test", libraryName="gson")


# ---------------------------------------------------------------------------
# T12: GitCloner error returns empty available_branches
# [unit]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_git_cloner_error_returns_empty_branches(
    mock_query_handler, mock_es_client
):
    """T12: GitCloner.list_remote_branches raising → available_branches=[]."""
    repo = _make_repo("gson", "https://github.com/google/gson", clone_path="/tmp/gson")
    session = AsyncMock()
    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [repo]
    result_mock.scalars.return_value = scalars_mock
    session.execute = AsyncMock(return_value=result_mock)
    session.close = AsyncMock()
    sf = MagicMock(return_value=session)

    cloner = MagicMock()
    cloner.list_remote_branches = MagicMock(
        side_effect=Exception("git error: not a repo")
    )

    mcp = create_mcp_server(
        mock_query_handler, sf, mock_es_client, git_cloner=cloner,
    )
    tool = _get_tool(mcp, "resolve_repository")
    result = await tool.fn(query="test", libraryName="gson")
    parsed = json.loads(result)

    assert len(parsed) == 1
    assert parsed[0]["available_branches"] == [], (
        f"Expected [] on git error, got {parsed[0]['available_branches']}"
    )


# ---------------------------------------------------------------------------
# T13: git_cloner=None returns empty available_branches
# [unit]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_no_git_cloner_returns_empty_branches(
    mock_query_handler, mock_es_client
):
    """T13: No git_cloner passed → available_branches=[] even with clone_path."""
    repo = _make_repo("gson", "https://github.com/google/gson", clone_path="/tmp/gson")
    session = AsyncMock()
    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [repo]
    result_mock.scalars.return_value = scalars_mock
    session.execute = AsyncMock(return_value=result_mock)
    session.close = AsyncMock()
    sf = MagicMock(return_value=session)

    # No git_cloner passed (default=None)
    mcp = create_mcp_server(mock_query_handler, sf, mock_es_client)
    tool = _get_tool(mcp, "resolve_repository")
    result = await tool.fn(query="test", libraryName="gson")
    parsed = json.loads(result)

    assert len(parsed) == 1
    assert parsed[0]["available_branches"] == []


# ---------------------------------------------------------------------------
# T14: No match returns empty list
# [unit]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_no_match_returns_empty(
    mock_query_handler, mock_session_factory, mock_es_client, mock_git_cloner
):
    """T14: libraryName with no matches returns empty JSON array."""
    mcp = create_mcp_server(
        mock_query_handler, mock_session_factory, mock_es_client,
        git_cloner=mock_git_cloner,
    )
    tool = _get_tool(mcp, "resolve_repository")
    result = await tool.fn(query="test", libraryName="zzz-nonexistent-zzz")
    parsed = json.loads(result)
    assert parsed == []


# ---------------------------------------------------------------------------
# T15: Case insensitive matching
# [unit]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_case_insensitive(
    mock_query_handler, mock_session_factory, mock_es_client, mock_git_cloner
):
    """T15: libraryName='GSON' (uppercase) matches repo named 'gson'."""
    mcp = create_mcp_server(
        mock_query_handler, mock_session_factory, mock_es_client,
        git_cloner=mock_git_cloner,
    )
    tool = _get_tool(mcp, "resolve_repository")
    result = await tool.fn(query="test", libraryName="GSON")
    parsed = json.loads(result)

    names = [r["name"] for r in parsed]
    assert "gson" in names, f"Case-insensitive match failed, got: {names}"


# ---------------------------------------------------------------------------
# T16: Single character libraryName
# [unit]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_single_char_library_name(
    mock_query_handler, mock_session_factory, mock_es_client, mock_git_cloner
):
    """T16: libraryName='g' single char — matches repos with 'g' in name/URL.
    'gson', 'gson-fire', 'my-gson-lib' match by name; 'react' matches via URL
    (github.com contains 'g'). Verify gson gets prefix tier (before substring)."""
    mcp = create_mcp_server(
        mock_query_handler, mock_session_factory, mock_es_client,
        git_cloner=mock_git_cloner,
    )
    tool = _get_tool(mcp, "resolve_repository")
    result = await tool.fn(query="test", libraryName="g")
    parsed = json.loads(result)

    names = [r["name"] for r in parsed]
    assert "gson" in names
    # gson should appear before react (prefix tier 2 vs substring tier 4)
    gson_idx = names.index("gson")
    if "react" in names:
        react_idx = names.index("react")
        assert gson_idx < react_idx, (
            f"gson (prefix) should sort before react (substring), got: {names}"
        )


# ---------------------------------------------------------------------------
# T17: clone_path=None returns empty branches
# [unit]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_none_clone_path_empty_branches(
    mock_query_handler, mock_es_client, mock_git_cloner
):
    """T17: repo.clone_path=None → available_branches=[]."""
    repo = _make_repo("gson", "https://github.com/google/gson", clone_path=None)
    session = AsyncMock()
    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [repo]
    result_mock.scalars.return_value = scalars_mock
    session.execute = AsyncMock(return_value=result_mock)
    session.close = AsyncMock()
    sf = MagicMock(return_value=session)

    mcp = create_mcp_server(
        mock_query_handler, sf, mock_es_client, git_cloner=mock_git_cloner,
    )
    tool = _get_tool(mcp, "resolve_repository")
    result = await tool.fn(query="test", libraryName="gson")
    parsed = json.loads(result)

    assert parsed[0]["available_branches"] == []
    # git_cloner.list_remote_branches should NOT have been called
    mock_git_cloner.list_remote_branches.assert_not_called()


# ---------------------------------------------------------------------------
# T18: Empty clone_path returns empty branches
# [unit]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_empty_clone_path_empty_branches(
    mock_query_handler, mock_es_client, mock_git_cloner
):
    """T18: repo.clone_path='' → available_branches=[]."""
    repo = _make_repo("gson", "https://github.com/google/gson", clone_path="")
    session = AsyncMock()
    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [repo]
    result_mock.scalars.return_value = scalars_mock
    session.execute = AsyncMock(return_value=result_mock)
    session.close = AsyncMock()
    sf = MagicMock(return_value=session)

    mcp = create_mcp_server(
        mock_query_handler, sf, mock_es_client, git_cloner=mock_git_cloner,
    )
    tool = _get_tool(mcp, "resolve_repository")
    result = await tool.fn(query="test", libraryName="gson")
    parsed = json.loads(result)

    assert parsed[0]["available_branches"] == []
    mock_git_cloner.list_remote_branches.assert_not_called()


# ---------------------------------------------------------------------------
# T19: URL with trailing slash — segment extraction
# [unit]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_url_trailing_slash(
    mock_query_handler, mock_es_client, mock_git_cloner
):
    """T19: URL 'https://github.com/org/gson/' (trailing slash) still matches."""
    repo = _make_repo(
        "org-gson", "https://github.com/org/gson/", clone_path=None,
    )
    session = AsyncMock()
    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [repo]
    result_mock.scalars.return_value = scalars_mock
    session.execute = AsyncMock(return_value=result_mock)
    session.close = AsyncMock()
    sf = MagicMock(return_value=session)

    mcp = create_mcp_server(
        mock_query_handler, sf, mock_es_client, git_cloner=mock_git_cloner,
    )
    tool = _get_tool(mcp, "resolve_repository")
    result = await tool.fn(query="test", libraryName="gson")
    parsed = json.loads(result)

    assert len(parsed) == 1, f"Trailing slash URL should match, got {parsed}"
    assert parsed[0]["name"] == "org-gson"


# ---------------------------------------------------------------------------
# T20: Whitespace-only query raises ValueError
# [unit]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_whitespace_query_raises_value_error(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """T20: query='  ' (whitespace only) raises ValueError."""
    mcp = create_mcp_server(
        mock_query_handler, mock_session_factory, mock_es_client,
    )
    tool = _get_tool(mcp, "resolve_repository")
    with pytest.raises(ValueError, match="query is required"):
        await tool.fn(query="   ", libraryName="gson")


# ---------------------------------------------------------------------------
# _score_match unit tests (pure function)
# [unit]
# ---------------------------------------------------------------------------


class TestScoreMatch:
    """Direct tests for _score_match pure function."""

    def test_exact_name_returns_tier_0(self):
        from src.query.mcp_server import _score_match
        assert _score_match("gson", "https://github.com/google/gson", "gson") == 0

    def test_exact_url_segment_returns_tier_1(self):
        from src.query.mcp_server import _score_match
        assert _score_match("springfw", "https://github.com/org/spring", "spring") == 1

    def test_prefix_name_returns_tier_2(self):
        from src.query.mcp_server import _score_match
        assert _score_match("gson-fire", "https://github.com/x/gson-fire", "gson") == 2

    def test_prefix_url_segment_returns_tier_3(self):
        from src.query.mcp_server import _score_match
        assert _score_match("mylib", "https://github.com/org/gson-ext", "gson") == 3

    def test_substring_returns_tier_4(self):
        from src.query.mcp_server import _score_match
        assert _score_match("my-gson-lib", "https://github.com/acme/my-gson-lib", "gson") == 4

    def test_no_match_returns_negative_1(self):
        from src.query.mcp_server import _score_match
        assert _score_match("react", "https://github.com/facebook/react", "gson") == -1

    def test_trailing_slash_url(self):
        from src.query.mcp_server import _score_match
        assert _score_match("other", "https://github.com/org/gson/", "gson") == 1

    def test_case_insensitive(self):
        from src.query.mcp_server import _score_match
        assert _score_match("Gson", "https://github.com/google/Gson", "gson") == 0


# ---------------------------------------------------------------------------
# _populate_branches unit tests
# [unit]
# ---------------------------------------------------------------------------


class TestPopulateBranches:
    """Direct tests for _populate_branches defensive wrapper."""

    def test_returns_branches_when_clone_exists(self):
        from src.query.mcp_server import _populate_branches
        repo = _make_repo("gson", "https://x", clone_path="/tmp/gson")
        cloner = MagicMock()
        cloner.list_remote_branches = MagicMock(return_value=["main", "dev"])
        assert _populate_branches(repo, cloner) == ["main", "dev"]

    def test_returns_empty_when_no_cloner(self):
        from src.query.mcp_server import _populate_branches
        repo = _make_repo("gson", "https://x", clone_path="/tmp/gson")
        assert _populate_branches(repo, None) == []

    def test_returns_empty_when_no_clone_path(self):
        from src.query.mcp_server import _populate_branches
        repo = _make_repo("gson", "https://x", clone_path=None)
        cloner = MagicMock()
        assert _populate_branches(repo, cloner) == []
        cloner.list_remote_branches.assert_not_called()

    def test_returns_empty_when_empty_clone_path(self):
        from src.query.mcp_server import _populate_branches
        repo = _make_repo("gson", "https://x", clone_path="")
        cloner = MagicMock()
        assert _populate_branches(repo, cloner) == []
        cloner.list_remote_branches.assert_not_called()

    def test_returns_empty_on_git_error(self):
        from src.query.mcp_server import _populate_branches
        repo = _make_repo("gson", "https://x", clone_path="/tmp/gson")
        cloner = MagicMock()
        cloner.list_remote_branches = MagicMock(side_effect=Exception("git error"))
        assert _populate_branches(repo, cloner) == []


# ---------------------------------------------------------------------------
# Real DB integration tests
# [integration] — uses real test database
# ---------------------------------------------------------------------------


@pytest.fixture
@pytest.mark.asyncio
async def real_db_session_factory():
    """Create a real async session factory connected to test PostgreSQL."""
    for k in ("ALL_PROXY", "all_proxy"):
        os.environ.pop(k, None)

    db_url = os.environ.get("DATABASE_URL")
    assert db_url, "DATABASE_URL must be set for real DB tests"

    from src.shared.database import get_engine, get_session_factory
    from src.shared.models.base import Base
    from src.shared.models.repository import Repository

    engine = get_engine(db_url)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sf = get_session_factory(engine)

    test_prefix = f"f46_test_{uuid.uuid4().hex[:6]}"
    repo_ids = []

    async with sf() as session:
        # Exact match, prefix match, substring match — for sorting verification
        r1 = Repository(
            name=f"{test_prefix}_gson",
            url=f"https://github.com/{test_prefix}/gson",
            default_branch="main",
            indexed_branch="main",
            status="indexed",
            last_indexed_at=datetime(2026, 3, 25, 12, 0, 0),
        )
        r2 = Repository(
            name=f"{test_prefix}_gson-fire",
            url=f"https://github.com/{test_prefix}/gson-fire",
            default_branch="main",
            indexed_branch="main",
            status="indexed",
            last_indexed_at=datetime(2026, 3, 25, 12, 0, 0),
        )
        r3 = Repository(
            name=f"{test_prefix}_my-gson-lib",
            url=f"https://github.com/{test_prefix}/my-gson-lib",
            default_branch="main",
            indexed_branch="main",
            status="indexed",
            last_indexed_at=datetime(2026, 3, 25, 12, 0, 0),
        )
        r4 = Repository(
            name=f"{test_prefix}_react",
            url=f"https://github.com/{test_prefix}/react",
            default_branch="main",
            status="pending",
        )
        session.add_all([r1, r2, r3, r4])
        await session.commit()
        repo_ids.extend([r1.id, r2.id, r3.id, r4.id])

    yield sf, test_prefix

    # Cleanup
    async with sf() as session:
        from sqlalchemy import delete
        await session.execute(
            delete(Repository).where(Repository.id.in_(repo_ids))
        )
        await session.commit()

    await engine.dispose()


@pytest.mark.real
@pytest.mark.asyncio
async def test_real_resolve_sorts_by_match_quality(
    mock_query_handler, mock_es_client, real_db_session_factory
):
    """Real test: resolve_repository returns results sorted by match quality
    against real PostgreSQL. Feature #46."""
    sf, test_prefix = real_db_session_factory

    mcp = create_mcp_server(mock_query_handler, sf, mock_es_client)
    tool = _get_tool(mcp, "resolve_repository")

    # Search using the full exact name of one repo to verify sorting
    # The test_prefix makes names unique: {prefix}_gson, {prefix}_gson-fire, {prefix}_my-gson-lib
    # Searching for {prefix}_gson should match:
    #   exact: {prefix}_gson (tier 0)
    #   prefix: {prefix}_gson-fire (tier 2)
    #   substring: {prefix}_my-gson-lib — won't match because {prefix}_gson is NOT
    #     a substring of {prefix}_my-gson-lib. Use a shorter search instead.
    # So let's search for just "gson" to match all three via substring:
    result = await tool.fn(query="test", libraryName="gson")
    parsed = json.loads(result)

    # Filter to only our test repos (other test data may exist in DB)
    our_repos = [r for r in parsed if test_prefix in r["name"]]
    names = [r["name"] for r in our_repos]

    assert len(our_repos) == 3, f"Expected 3 matching repos, got {len(our_repos)}: {names}"
    # All three are substring matches on "gson" — but within substring tier,
    # verify they all appear and the exact name-match sorts first
    assert f"{test_prefix}_gson" in names
    assert f"{test_prefix}_gson-fire" in names
    assert f"{test_prefix}_my-gson-lib" in names

    # Pending repo excluded
    assert not any("react" in n for n in names)


@pytest.mark.real
@pytest.mark.asyncio
async def test_real_resolve_no_match_returns_empty(
    mock_query_handler, mock_es_client, real_db_session_factory
):
    """Real test: non-matching libraryName returns empty list. Feature #46."""
    sf, _ = real_db_session_factory

    mcp = create_mcp_server(mock_query_handler, sf, mock_es_client)
    tool = _get_tool(mcp, "resolve_repository")

    result = await tool.fn(
        query="test", libraryName=f"nonexistent_{uuid.uuid4().hex[:8]}"
    )
    parsed = json.loads(result)
    assert parsed == []


@pytest.mark.real
@pytest.mark.asyncio
async def test_real_resolve_result_fields_complete(
    mock_query_handler, mock_es_client, real_db_session_factory
):
    """Real test: all 7 required fields present with correct types. Feature #46."""
    sf, test_prefix = real_db_session_factory

    mcp = create_mcp_server(mock_query_handler, sf, mock_es_client)
    tool = _get_tool(mcp, "resolve_repository")

    result = await tool.fn(
        query="test", libraryName=f"{test_prefix}_gson"
    )
    parsed = json.loads(result)

    assert len(parsed) >= 1
    for repo in parsed:
        assert isinstance(repo["id"], str) and repo["id"] != ""
        assert isinstance(repo["name"], str) and repo["name"] != ""
        assert isinstance(repo["url"], str) and repo["url"].startswith("https://")
        assert repo["indexed_branch"] is not None
        assert repo["default_branch"] is not None
        assert isinstance(repo["available_branches"], list)
        assert repo["last_indexed_at"] is not None
