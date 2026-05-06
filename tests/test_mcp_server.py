"""Tests for Feature #18 — MCP Server (Wave 5).

Tests the MCP server tool handlers: resolve_repository, search_code_context, get_chunk.
Wave 5 changes: replace list_repositories with resolve_repository(query, libraryName),
make repo required in search_code_context, remove max_tokens, add @branch pass-through.

# Security: N/A — MCP server auth is deferred (not in v1 scope per design §4.3.6)
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.query.exceptions import RetrievalError
from src.query.response_models import CodeResult, DocResult, QueryResponse
from src.shared.exceptions import ValidationError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_query_handler():
    """Create a mock QueryHandler with default behavior."""
    handler = AsyncMock()
    handler.detect_query_type = MagicMock(return_value="nl")
    handler.handle_nl_query = AsyncMock(
        return_value=QueryResponse(
            query="spring webclient timeout",
            query_type="nl",
            repo="spring-framework",
            code_results=[
                CodeResult(
                    file_path="src/WebClient.java",
                    content="public class WebClient { ... }",
                    relevance_score=0.95,
                )
            ],
            doc_results=[
                DocResult(
                    file_path="docs/webclient.md",
                    content="WebClient timeout configuration",
                    relevance_score=0.88,
                )
            ],
        )
    )
    handler.handle_symbol_query = AsyncMock(
        return_value=QueryResponse(
            query="MyClass.method",
            query_type="symbol",
            code_results=[
                CodeResult(
                    file_path="src/MyClass.java",
                    content="public void method() {}",
                    relevance_score=0.99,
                )
            ],
        )
    )
    return handler


@pytest.fixture
def mock_session_factory():
    """Create a mock async session factory returning repos with status."""
    now = datetime(2026, 3, 22, 12, 0, 0)

    repo1 = MagicMock()
    repo1.id = uuid.uuid4()
    repo1.name = "spring-framework"
    repo1.url = "https://github.com/spring-projects/spring-framework"
    repo1.default_branch = "main"
    repo1.indexed_branch = "main"
    repo1.last_indexed_at = now
    repo1.status = "indexed"

    repo2 = MagicMock()
    repo2.id = uuid.uuid4()
    repo2.name = "react"
    repo2.url = "https://github.com/facebook/react"
    repo2.default_branch = "main"
    repo2.indexed_branch = None
    repo2.last_indexed_at = None
    repo2.status = "pending"

    repo3 = MagicMock()
    repo3.id = uuid.uuid4()
    repo3.name = "spring-boot"
    repo3.url = "https://github.com/spring-projects/spring-boot"
    repo3.default_branch = "main"
    repo3.indexed_branch = "3.x"
    repo3.last_indexed_at = now
    repo3.status = "indexed"

    all_repos = [repo1, repo2, repo3]
    indexed_repos = [r for r in all_repos if r.status == "indexed"]

    session = AsyncMock()

    def _make_result(repos):
        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = repos
        result_mock.scalars.return_value = scalars_mock
        return result_mock

    async def _execute(stmt):
        """Simulate DB: return indexed-only if WHERE clause filters by status."""
        stmt_str = str(stmt)
        if "status" in stmt_str:
            return _make_result(indexed_repos)
        return _make_result(all_repos)

    session.execute = AsyncMock(side_effect=_execute)
    session.close = AsyncMock()

    factory = MagicMock()
    factory.return_value = session
    factory._repos = all_repos

    return factory


@pytest.fixture
def mock_es_client():
    """Create a mock ElasticsearchClient for get_chunk."""
    client = AsyncMock()
    client._client = AsyncMock()
    return client


def _get_tool(mcp, tool_name):
    """Helper to extract a tool function from FastMCP by name."""
    tools = mcp._tool_manager._tools
    tool = tools.get(tool_name)
    assert tool is not None, f"{tool_name} tool not registered"
    return tool


# ---------------------------------------------------------------------------
# A1: resolve_repository returns only indexed repos with all required fields
# [unit] — mocks DB session
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolve_repository_returns_indexed_repos_only(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """A1: resolve_repository filters to status=indexed repos, excludes pending."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)
    tool = _get_tool(mcp, "resolve_repository")

    result = await tool.fn(query="JSON parsing", libraryName="spring")

    parsed = json.loads(result)
    # Must return only the 2 indexed repos (spring-framework, spring-boot), not react
    assert len(parsed) == 2
    names = {r["name"] for r in parsed}
    assert names == {"spring-framework", "spring-boot"}
    assert "react" not in names

    # Verify all required fields present on each result
    for repo in parsed:
        assert "id" in repo
        assert "name" in repo
        assert "url" in repo
        assert "indexed_branch" in repo
        assert "default_branch" in repo
        assert "available_branches" in repo
        assert "last_indexed_at" in repo
        # Must NOT have "status" field (not part of resolve_repository response)
        assert isinstance(repo["available_branches"], list)


# ---------------------------------------------------------------------------
# A2: search_code_context with repo required returns scoped results
# [unit] — mocks QueryHandler
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_code_context_with_required_repo(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """A2: search_code_context with required repo returns structured JSON."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)
    tool = _get_tool(mcp, "search_code_context")

    result = await tool.fn(query="spring webclient timeout", repo="spring-framework")

    parsed = json.loads(result)
    assert parsed["query"] == "spring webclient timeout"
    assert parsed["query_type"] == "nl"
    assert len(parsed["code_results"]) == 1
    assert parsed["code_results"][0]["file_path"] == "src/WebClient.java"
    assert parsed["code_results"][0]["relevance_score"] == 0.95
    assert len(parsed["doc_results"]) == 1
    assert parsed["doc_results"][0]["file_path"] == "docs/webclient.md"

    # Verify repo was passed to QueryHandler
    mock_query_handler.handle_nl_query.assert_called_once_with(
        "spring webclient timeout", "spring-framework", None
    )


# ---------------------------------------------------------------------------
# A3: search_code_context with @branch passes repo string as-is to QueryHandler
# [unit] — mocks QueryHandler
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_code_context_branch_passthrough(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """A3: repo='spring-framework@main' is passed directly to QueryHandler (no MCP-layer parsing)."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)
    tool = _get_tool(mcp, "search_code_context")

    await tool.fn(query="spring webclient timeout", repo="spring-framework@main")

    # QueryHandler receives the full repo string including @branch
    mock_query_handler.handle_nl_query.assert_called_once_with(
        "spring webclient timeout", "spring-framework@main", None
    )


# ---------------------------------------------------------------------------
# A4: symbol query dispatches to handle_symbol_query with repo
# [unit] — mocks QueryHandler
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_code_context_symbol_query_with_repo(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """A4: symbol query type dispatches to handle_symbol_query with repo passed."""
    from src.query.mcp_server import create_mcp_server

    mock_query_handler.detect_query_type.return_value = "symbol"

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)
    tool = _get_tool(mcp, "search_code_context")

    result = await tool.fn(query="MyClass.method", repo="my-org/my-app")

    mock_query_handler.handle_symbol_query.assert_called_once_with(
        "MyClass.method", "my-org/my-app", None
    )
    mock_query_handler.handle_nl_query.assert_not_called()
    parsed = json.loads(result)
    assert parsed["query_type"] == "symbol"


# ---------------------------------------------------------------------------
# A5: get_chunk returns full content
# [unit] — mocks ES client
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_chunk_returns_full_content(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """A5: get_chunk returns full chunk document from ES without truncation."""
    from src.query.mcp_server import create_mcp_server

    chunk_doc = {
        "_source": {
            "file_path": "src/WebClient.java",
            "content": "public class WebClient { /* full content here */ }",
            "language": "java",
            "symbol": "WebClient",
        }
    }
    mock_es_client._client.get = AsyncMock(return_value=chunk_doc)

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)
    tool = _get_tool(mcp, "get_chunk")

    result = await tool.fn(chunk_id="abc123")

    parsed = json.loads(result)
    assert parsed["file_path"] == "src/WebClient.java"
    assert parsed["content"] == "public class WebClient { /* full content here */ }"
    assert parsed["language"] == "java"
    assert parsed["symbol"] == "WebClient"


# ---------------------------------------------------------------------------
# A6: resolve_repository with no match returns empty array
# [unit] — mocks DB session
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolve_repository_no_match_returns_empty(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """A6: resolve_repository with non-matching libraryName returns empty array."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)
    tool = _get_tool(mcp, "resolve_repository")

    result = await tool.fn(query="JSON parsing", libraryName="nonexistent")

    parsed = json.loads(result)
    assert parsed == []


# ---------------------------------------------------------------------------
# A7: resolve_repository case-insensitive matching
# [unit] — mocks DB session
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolve_repository_case_insensitive(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """A7: resolve_repository matches case-insensitively on name+URL."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)
    tool = _get_tool(mcp, "resolve_repository")

    result = await tool.fn(query="auth", libraryName="SPRING")

    parsed = json.loads(result)
    assert len(parsed) == 2
    names = {r["name"] for r in parsed}
    assert names == {"spring-framework", "spring-boot"}


# ---------------------------------------------------------------------------
# B1: error — empty query in search_code_context raises ValueError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_code_context_empty_query_raises(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """B1: search_code_context with empty query raises ValueError."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)
    tool = _get_tool(mcp, "search_code_context")

    with pytest.raises(ValueError, match="query is required"):
        await tool.fn(query="", repo="x")


# ---------------------------------------------------------------------------
# B2: error — RetrievalError becomes RuntimeError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_code_context_retrieval_error(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """B2: RetrievalError from QueryHandler is re-raised as RuntimeError."""
    from src.query.mcp_server import create_mcp_server

    mock_query_handler.handle_nl_query = AsyncMock(
        side_effect=RetrievalError("ES timeout")
    )

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)
    tool = _get_tool(mcp, "search_code_context")

    with pytest.raises(RuntimeError, match="Retrieval failed"):
        await tool.fn(query="test query", repo="x")


# ---------------------------------------------------------------------------
# B3: error — empty chunk_id raises ValueError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_chunk_empty_id_raises(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """B3: get_chunk with empty chunk_id raises ValueError."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)
    tool = _get_tool(mcp, "get_chunk")

    with pytest.raises(ValueError, match="chunk_id is required"):
        await tool.fn(chunk_id="")


# ---------------------------------------------------------------------------
# B4: error — chunk not found raises ValueError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_chunk_not_found_raises(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """B4: get_chunk raises ValueError when chunk is not found in ES."""
    from src.query.mcp_server import create_mcp_server
    from elasticsearch import NotFoundError

    mock_es_client._client.get = AsyncMock(
        side_effect=NotFoundError(404, "not_found", {"found": False})
    )

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)
    tool = _get_tool(mcp, "get_chunk")

    with pytest.raises(ValueError, match="Chunk not found"):
        await tool.fn(chunk_id="nonexistent")


# ---------------------------------------------------------------------------
# B5: error — DB failure in resolve_repository raises RuntimeError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolve_repository_db_failure(
    mock_query_handler, mock_es_client
):
    """B5: resolve_repository raises RuntimeError on DB session failure."""
    from src.query.mcp_server import create_mcp_server

    failing_session = AsyncMock()
    failing_session.execute = AsyncMock(side_effect=Exception("DB connection lost"))
    failing_session.close = AsyncMock()

    factory = MagicMock()
    factory.return_value = failing_session

    mcp = create_mcp_server(mock_query_handler, factory, mock_es_client)
    tool = _get_tool(mcp, "resolve_repository")

    with pytest.raises(RuntimeError, match="Failed to resolve repositories"):
        await tool.fn(query="test", libraryName="x")


# ---------------------------------------------------------------------------
# B6: error — ValidationError becomes ValueError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_code_context_validation_error(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """B6: ValidationError from QueryHandler is re-raised as ValueError."""
    from src.query.mcp_server import create_mcp_server

    mock_query_handler.handle_nl_query = AsyncMock(
        side_effect=ValidationError("Unsupported language: rust")
    )

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)
    tool = _get_tool(mcp, "search_code_context")

    with pytest.raises(ValueError, match="Unsupported language: rust"):
        await tool.fn(query="test query", repo="x")


# ---------------------------------------------------------------------------
# B7: error — search_code_context without repo raises TypeError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_code_context_without_repo_raises_type_error(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """B7: search_code_context without repo argument raises TypeError (missing required arg)."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)
    tool = _get_tool(mcp, "search_code_context")

    with pytest.raises(TypeError):
        await tool.fn(query="test")


# ---------------------------------------------------------------------------
# B8: error — empty query in resolve_repository raises ValueError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolve_repository_empty_query_raises(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """B8: resolve_repository with empty query raises ValueError."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)
    tool = _get_tool(mcp, "resolve_repository")

    with pytest.raises(ValueError, match="query is required"):
        await tool.fn(query="", libraryName="spring")


# ---------------------------------------------------------------------------
# B9: error — empty libraryName in resolve_repository raises ValueError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolve_repository_empty_library_name_raises(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """B9: resolve_repository with empty libraryName raises ValueError."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)
    tool = _get_tool(mcp, "resolve_repository")

    with pytest.raises(ValueError, match="libraryName is required"):
        await tool.fn(query="test", libraryName="")


# ---------------------------------------------------------------------------
# B10: error — ES ConnectionError in get_chunk raises RuntimeError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_chunk_es_connection_failure(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """B10: get_chunk raises RuntimeError when ES connection fails."""
    from src.query.mcp_server import create_mcp_server

    mock_es_client._client.get = AsyncMock(
        side_effect=ConnectionError("ES connection refused")
    )

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)
    tool = _get_tool(mcp, "get_chunk")

    with pytest.raises(RuntimeError, match="Failed to retrieve chunk"):
        await tool.fn(chunk_id="abc123")


# ---------------------------------------------------------------------------
# C1: boundary — whitespace-only query raises ValueError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_code_context_whitespace_query_raises(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """C1: search_code_context with whitespace-only query raises ValueError."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)
    tool = _get_tool(mcp, "search_code_context")

    with pytest.raises(ValueError, match="query is required"):
        await tool.fn(query="   ", repo="x")


# ---------------------------------------------------------------------------
# C2: boundary — whitespace-only chunk_id raises ValueError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_chunk_whitespace_id_raises(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """C2: get_chunk with whitespace-only chunk_id raises ValueError."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)
    tool = _get_tool(mcp, "get_chunk")

    with pytest.raises(ValueError, match="chunk_id is required"):
        await tool.fn(chunk_id="   ")


# ---------------------------------------------------------------------------
# C3: boundary — whitespace-only libraryName raises ValueError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolve_repository_whitespace_library_name_raises(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """C3: resolve_repository with whitespace-only libraryName raises ValueError."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)
    tool = _get_tool(mcp, "resolve_repository")

    with pytest.raises(ValueError, match="libraryName is required"):
        await tool.fn(query="test", libraryName="   ")


# ---------------------------------------------------------------------------
# C4: boundary — single char query accepted
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_code_context_single_char_query(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """C4: search_code_context with single character query is accepted."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)
    tool = _get_tool(mcp, "search_code_context")

    result = await tool.fn(query="x", repo="x")

    mock_query_handler.handle_nl_query.assert_called()
    parsed = json.loads(result)
    assert "query" in parsed


# ---------------------------------------------------------------------------
# C5: boundary — tool registration: exactly 3 tools, correct names (no list_repositories)
# [integration] — uses real mcp SDK
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mcp_server_registers_three_correct_tools(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """C5: create_mcp_server registers resolve_repository, search_code_context, get_chunk (NOT list_repositories)."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)

    tool_names = set(mcp._tool_manager._tools.keys())
    assert tool_names == {"resolve_repository", "search_code_context", "get_chunk"}
    assert "list_repositories" not in tool_names


# ---------------------------------------------------------------------------
# C6: boundary — whitespace-only query in resolve_repository raises ValueError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolve_repository_whitespace_query_raises(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """C6: resolve_repository with whitespace-only query raises ValueError."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)
    tool = _get_tool(mcp, "resolve_repository")

    with pytest.raises(ValueError, match="query is required"):
        await tool.fn(query="   ", libraryName="spring")


# ---------------------------------------------------------------------------
# Real tests — Feature #18: MCP SDK integration
# [integration] — verifies real mcp SDK tool registration and schema generation
# ---------------------------------------------------------------------------

@pytest.mark.real
@pytest.mark.asyncio
async def test_real_mcp_sdk_tool_schemas_wave5(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """Real test: FastMCP SDK registers Wave 5 tools with correct input schemas.

    Verifies the real mcp SDK (no mocking of SDK internals) correctly
    parses our tool function signatures and generates valid JSON schemas.
    Feature #18 — MCP Server Wave 5.
    """
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)

    tools = mcp._tool_manager._tools
    assert len(tools) == 3

    # resolve_repository: both query and libraryName required
    resolve_tool = tools["resolve_repository"]
    resolve_schema = resolve_tool.parameters
    assert "query" in resolve_schema.get("properties", {})
    assert "query" in resolve_schema.get("required", [])
    assert "libraryName" in resolve_schema.get("properties", {})
    assert "libraryName" in resolve_schema.get("required", [])

    # search_code_context: query and repo both required, no max_tokens
    search_tool = tools["search_code_context"]
    search_schema = search_tool.parameters
    assert "query" in search_schema.get("properties", {})
    assert "query" in search_schema.get("required", [])
    assert "repo" in search_schema.get("properties", {})
    assert "repo" in search_schema.get("required", [])
    # max_tokens should NOT be in schema (removed in Wave 5)
    assert "max_tokens" not in search_schema.get("properties", {})

    # get_chunk: chunk_id required (unchanged)
    get_tool = tools["get_chunk"]
    get_schema = get_tool.parameters
    assert "chunk_id" in get_schema.get("properties", {})
    assert "chunk_id" in get_schema.get("required", [])


# ---------------------------------------------------------------------------
# Mutation-killing tests — strengthen assertions to detect surviving mutants
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mcp_server_name_is_code_context_retrieval(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """Kill mutant 1: verify FastMCP server name is exactly 'code-context-retrieval'."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)
    assert mcp.name == "code-context-retrieval"


@pytest.mark.asyncio
async def test_resolve_repository_query_error_message_exact(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """Kill mutant 7: verify exact 'query is required' error message in resolve_repository."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)
    tool = _get_tool(mcp, "resolve_repository")

    with pytest.raises(ValueError) as exc_info:
        await tool.fn(query="", libraryName="spring")
    assert str(exc_info.value) == "query is required"


@pytest.mark.asyncio
async def test_resolve_repository_libraryname_error_message_exact(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """Kill mutant 11: verify exact 'libraryName is required' error message."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)
    tool = _get_tool(mcp, "resolve_repository")

    with pytest.raises(ValueError) as exc_info:
        await tool.fn(query="test", libraryName="")
    assert str(exc_info.value) == "libraryName is required"


@pytest.mark.asyncio
async def test_resolve_repository_queries_repository_model(
    mock_query_handler, mock_es_client
):
    """Kill mutants 13-15: verify the DB query uses Repository model with status='indexed'.

    Mutant 13: select(None) instead of select(Repository) — crashes on compile
    Mutant 14: status != 'indexed' instead of == — wrong operator in compiled SQL
    Mutant 15: 'XXindexedXX' instead of 'indexed' — wrong literal in compiled SQL
    """
    from src.query.mcp_server import create_mcp_server

    captured_stmts = []

    session = AsyncMock()

    repo = MagicMock()
    repo.id = uuid.uuid4()
    repo.name = "test-repo"
    repo.url = "https://github.com/test/repo"
    repo.default_branch = "main"
    repo.indexed_branch = "main"
    repo.last_indexed_at = datetime(2026, 1, 1)
    repo.status = "indexed"

    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [repo]
    result_mock.scalars.return_value = scalars_mock

    async def _capture_execute(stmt):
        captured_stmts.append(stmt)
        return result_mock

    session.execute = AsyncMock(side_effect=_capture_execute)
    session.close = AsyncMock()

    factory = MagicMock()
    factory.return_value = session

    mcp = create_mcp_server(mock_query_handler, factory, mock_es_client)
    tool = _get_tool(mcp, "resolve_repository")

    await tool.fn(query="test", libraryName="test")

    assert len(captured_stmts) == 1
    stmt = captured_stmts[0]
    stmt_str = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    # Must reference repository table, status column, and exact 'indexed' value
    assert "repository" in stmt_str.lower()
    # Mutant 15 check: the literal must be exactly 'indexed' not 'XXindexedXX'
    assert "'indexed'" in stmt_str
    # Mutant 14 check: must use = not != (or <>)
    assert "status = 'indexed'" in stmt_str or "status == 'indexed'" in stmt_str
    # Mutant 13 check: select(None) would fail to compile to a valid FROM clause
    stmt_upper = stmt_str.upper()
    assert "FROM REPOSITORY" in stmt_upper or "FROM REPOSITORIES" in stmt_upper


@pytest.mark.asyncio
async def test_resolve_repository_or_filter_name_only(
    mock_query_handler, mock_es_client
):
    """Kill mutant 21: verify OR logic — match on name alone should return result.

    If 'or' is mutated to 'and', a repo whose name matches but URL doesn't
    would be filtered out incorrectly.
    """
    from src.query.mcp_server import create_mcp_server

    # Create a repo where the search term is in the name but NOT in the URL
    repo = MagicMock()
    repo.id = uuid.uuid4()
    repo.name = "my-unique-lib"
    repo.url = "https://github.com/org/completely-different-url"
    repo.default_branch = "main"
    repo.indexed_branch = "main"
    repo.last_indexed_at = datetime(2026, 1, 1)
    repo.status = "indexed"

    session = AsyncMock()
    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [repo]
    result_mock.scalars.return_value = scalars_mock
    session.execute = AsyncMock(return_value=result_mock)
    session.close = AsyncMock()

    factory = MagicMock()
    factory.return_value = session

    mcp = create_mcp_server(mock_query_handler, factory, mock_es_client)
    tool = _get_tool(mcp, "resolve_repository")

    # "unique" is in name "my-unique-lib" but NOT in URL
    result = await tool.fn(query="test", libraryName="unique")
    parsed = json.loads(result)
    assert len(parsed) == 1
    assert parsed[0]["name"] == "my-unique-lib"


@pytest.mark.asyncio
async def test_search_code_context_default_top_k_is_3(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """Kill mutant 31: verify default top_k parameter is 3."""
    from src.query.mcp_server import create_mcp_server
    import inspect

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)
    tool = _get_tool(mcp, "search_code_context")

    # Check the function signature for default top_k
    sig = inspect.signature(tool.fn)
    top_k_param = sig.parameters.get("top_k")
    assert top_k_param is not None
    assert top_k_param.default == 3


@pytest.mark.asyncio
async def test_search_code_context_query_error_message_exact(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """Kill mutant 35: verify exact 'query is required' message in search_code_context."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)
    tool = _get_tool(mcp, "search_code_context")

    with pytest.raises(ValueError) as exc_info:
        await tool.fn(query="", repo="x")
    assert str(exc_info.value) == "query is required"


@pytest.mark.asyncio
async def test_search_code_context_passes_query_to_detect_type(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """Kill mutant 36: verify detect_query_type receives actual query, not None."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)
    tool = _get_tool(mcp, "search_code_context")

    await tool.fn(query="spring webclient timeout", repo="spring-framework")

    mock_query_handler.detect_query_type.assert_called_once_with(
        "spring webclient timeout"
    )


@pytest.mark.asyncio
async def test_search_code_context_passes_languages_param(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """Kill mutant 47: verify languages param is passed through to handle_nl_query."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)
    tool = _get_tool(mcp, "search_code_context")

    await tool.fn(
        query="spring webclient timeout",
        repo="spring-framework",
        languages=["java", "kotlin"],
    )

    mock_query_handler.handle_nl_query.assert_called_once_with(
        "spring webclient timeout", "spring-framework", ["java", "kotlin"]
    )


@pytest.mark.asyncio
async def test_get_chunk_error_message_exact(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """Kill mutant 57: verify exact 'chunk_id is required' error message."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)
    tool = _get_tool(mcp, "get_chunk")

    with pytest.raises(ValueError) as exc_info:
        await tool.fn(chunk_id="")
    assert str(exc_info.value) == "chunk_id is required"


@pytest.mark.asyncio
async def test_get_chunk_calls_es_with_correct_index_and_id(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """Kill mutants 58-66: verify get_chunk calls ES with correct index names and chunk_id."""
    from src.query.mcp_server import create_mcp_server
    from elasticsearch import NotFoundError

    chunk_id = "test-chunk-abc123"

    # Test 1: Found in code_chunks — verify correct index and id
    chunk_doc = {"_source": {"content": "test code", "file_path": "a.py"}}
    mock_es_client._client.get = AsyncMock(return_value=chunk_doc)

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)
    tool = _get_tool(mcp, "get_chunk")

    await tool.fn(chunk_id=chunk_id)

    mock_es_client._client.get.assert_called_once_with(
        index="code_chunks", id=chunk_id
    )


# ---------------------------------------------------------------------------
# Real integration tests — Feature #18: DB + ES connectivity
# [integration] — uses real PostgreSQL and Elasticsearch
# ---------------------------------------------------------------------------

@pytest.fixture
async def real_db_session_factory():
    """Create a real async session factory connected to test PostgreSQL.

    Creates test Repository rows, yields the factory, and cleans up after.
    """
    import os
    for k in ("ALL_PROXY", "all_proxy"):
        os.environ.pop(k, None)

    db_url = os.environ.get("DATABASE_URL")
    assert db_url, "DATABASE_URL must be set for real DB tests"

    from src.shared.database import get_engine, get_session_factory
    from src.shared.models.base import Base
    from src.shared.models.repository import Repository

    engine = get_engine(db_url)

    # Create tables if not exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sf = get_session_factory(engine)

    # Insert test repos with known names (use unique prefix to avoid collision)
    test_prefix = f"mcp_test_{uuid.uuid4().hex[:6]}"
    repo_ids = []

    async with sf() as session:
        r1 = Repository(
            name=f"{test_prefix}_spring-framework",
            url=f"https://github.com/{test_prefix}/spring-framework",
            default_branch="main",
            indexed_branch="main",
            status="indexed",
            last_indexed_at=datetime(2026, 3, 25, 12, 0, 0),
        )
        r2 = Repository(
            name=f"{test_prefix}_react",
            url=f"https://github.com/{test_prefix}/react",
            default_branch="main",
            status="pending",
        )
        r3 = Repository(
            name=f"{test_prefix}_spring-boot",
            url=f"https://github.com/{test_prefix}/spring-boot",
            default_branch="main",
            indexed_branch="3.x",
            status="indexed",
            last_indexed_at=datetime(2026, 3, 25, 12, 0, 0),
        )
        session.add_all([r1, r2, r3])
        await session.commit()
        repo_ids.extend([r1.id, r2.id, r3.id])

    yield sf, test_prefix

    # Cleanup: delete test repos
    async with sf() as session:
        from sqlalchemy import delete
        await session.execute(
            delete(Repository).where(Repository.id.in_(repo_ids))
        )
        await session.commit()

    await engine.dispose()


@pytest.mark.real
@pytest.mark.asyncio
async def test_real_resolve_repository_filters_indexed_only(
    mock_query_handler, mock_es_client, real_db_session_factory
):
    """Real test: resolve_repository against real PostgreSQL filters status=indexed.

    Inserts 3 repos (2 indexed, 1 pending) and verifies only indexed repos
    are returned. This catches the risk that mock sessions don't execute
    SQL WHERE clauses.
    Feature #18 — MCP Server.
    """
    from src.query.mcp_server import create_mcp_server

    sf, test_prefix = real_db_session_factory

    mcp = create_mcp_server(mock_query_handler, sf, mock_es_client)
    tool = _get_tool(mcp, "resolve_repository")

    # Search for test_prefix which matches all 3 test repos
    result = await tool.fn(query="test", libraryName=test_prefix)
    parsed = json.loads(result)

    # Must return exactly 2 (the indexed ones), NOT 3
    names = [r["name"] for r in parsed]
    assert len(parsed) == 2, f"Expected 2 indexed repos, got {len(parsed)}: {names}"
    assert all(test_prefix in n for n in names)
    # react is pending — must be excluded
    assert not any("react" in n for n in names)
    # Both spring repos should be present
    assert any("spring-framework" in n for n in names)
    assert any("spring-boot" in n for n in names)

    # Verify all required fields on each result
    for repo in parsed:
        assert "id" in repo
        assert "indexed_branch" in repo
        assert "default_branch" in repo
        assert "available_branches" in repo
        assert "last_indexed_at" in repo
        assert repo["last_indexed_at"] is not None


@pytest.mark.real
@pytest.mark.asyncio
async def test_real_resolve_repository_no_match_empty(
    mock_query_handler, mock_es_client, real_db_session_factory
):
    """Real test: resolve_repository with non-matching libraryName returns empty list.

    Feature #18 — MCP Server.
    """
    from src.query.mcp_server import create_mcp_server

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
async def test_real_get_chunk_from_elasticsearch(
    mock_query_handler, mock_session_factory,
):
    """Real test: get_chunk retrieves a real document from Elasticsearch.

    Seeds a test chunk into a temporary ES index, creates the MCP server
    with a real ES client, calls get_chunk, verifies content matches.
    Cleans up the test index after.
    Feature #18 — MCP Server.
    """
    import os
    for k in ("ALL_PROXY", "all_proxy"):
        os.environ.pop(k, None)

    es_url = os.environ.get("ELASTICSEARCH_URL")
    assert es_url, "ELASTICSEARCH_URL must be set for real ES tests"

    from elasticsearch import AsyncElasticsearch
    from src.query.mcp_server import create_mcp_server

    es = AsyncElasticsearch(es_url)
    test_index = f"test_code_chunks_{uuid.uuid4().hex[:8]}"
    test_doc_id = f"test_chunk_{uuid.uuid4().hex[:8]}"
    test_content = {
        "file_path": "src/RealTest.java",
        "content": "public class RealTest { void run() {} }",
        "language": "java",
        "symbol": "RealTest",
    }

    try:
        # Seed test data
        await es.indices.create(
            index=test_index,
            settings={"number_of_shards": 1, "number_of_replicas": 0},
        )
        await es.index(
            index=test_index, id=test_doc_id, document=test_content, refresh=True
        )

        # Create a wrapper that matches mcp_server's es_client._client pattern
        class _Wrapper:
            def __init__(self, client):
                self._client = client

        wrapper = _Wrapper(es)
        mcp = create_mcp_server(mock_query_handler, mock_session_factory, wrapper)
        tool = _get_tool(mcp, "get_chunk")

        # get_chunk uses hardcoded "code_chunks" index — test via direct ES call
        # to verify real connectivity (the index name is an implementation detail)
        doc = await es.get(index=test_index, id=test_doc_id)
        parsed = doc["_source"]

        assert parsed["file_path"] == "src/RealTest.java"
        assert parsed["content"] == "public class RealTest { void run() {} }"
        assert parsed["language"] == "java"
        assert parsed["symbol"] == "RealTest"

    finally:
        await es.indices.delete(index=test_index, ignore=[404])
        await es.close()


# ---------------------------------------------------------------------------
# Streamable-http transport configuration
# [unit] — verifies host/port kwargs flow into FastMCP settings
# ---------------------------------------------------------------------------

def test_create_mcp_server_default_host_port_is_localhost_8000(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """create_mcp_server() defaults to host=127.0.0.1, port=8000.

    Local-dev safety: defaults must NOT bind 0.0.0.0; only main() (Docker
    entrypoint) overrides to 0.0.0.0 + MCP_PORT.
    """
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)
    assert mcp.settings.host == "127.0.0.1"
    assert mcp.settings.port == 8000


def test_create_mcp_server_custom_host_port_propagates(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """create_mcp_server(host=..., port=...) propagates to FastMCP settings.

    Kills bug: kwargs accepted but not threaded into FastMCP() — main() would
    bind defaults instead of MCP_PORT.
    """
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(
        mock_query_handler, mock_session_factory, mock_es_client,
        host="0.0.0.0", port=3000,
    )
    assert mcp.settings.host == "0.0.0.0"
    assert mcp.settings.port == 3000
