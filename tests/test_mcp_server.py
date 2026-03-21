"""Tests for Feature #18 — MCP Server.

Tests the MCP server tool handlers: search_code_context, list_repositories, get_chunk.
The MCP server delegates to QueryHandler (Feature #13) for search operations.

# Security: N/A — MCP server auth is deferred (not in v1 scope per design §4.3.5)
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
    """Create a mock async session factory returning repos."""
    repo1_id = uuid.uuid4()
    repo2_id = uuid.uuid4()
    repo3_id = uuid.uuid4()
    now = datetime(2026, 3, 22, 12, 0, 0)

    repo1 = MagicMock()
    repo1.id = repo1_id
    repo1.name = "spring-framework"
    repo1.url = "https://github.com/spring-projects/spring-framework"
    repo1.default_branch = "main"
    repo1.indexed_branch = "main"
    repo1.last_indexed_at = now
    repo1.status = "indexed"

    repo2 = MagicMock()
    repo2.id = repo2_id
    repo2.name = "react"
    repo2.url = "https://github.com/facebook/react"
    repo2.default_branch = "main"
    repo2.indexed_branch = None
    repo2.last_indexed_at = None
    repo2.status = "pending"

    repo3 = MagicMock()
    repo3.id = repo3_id
    repo3.name = "spring-boot"
    repo3.url = "https://github.com/spring-projects/spring-boot"
    repo3.default_branch = "main"
    repo3.indexed_branch = "3.x"
    repo3.last_indexed_at = now
    repo3.status = "indexed"

    session = AsyncMock()
    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [repo1, repo2, repo3]
    result_mock.scalars.return_value = scalars_mock
    session.execute = AsyncMock(return_value=result_mock)
    session.close = AsyncMock()

    factory = MagicMock()
    factory.return_value = session
    factory._repos = [repo1, repo2, repo3]

    return factory


@pytest.fixture
def mock_es_client():
    """Create a mock ElasticsearchClient for get_chunk."""
    client = AsyncMock()
    client._client = AsyncMock()
    return client


# ---------------------------------------------------------------------------
# A1: Happy path — search_code_context returns JSON with correct structure
# [unit] — mocks QueryHandler
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_code_context_returns_valid_json(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """A1: search_code_context with valid query returns JSON response matching REST format."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)

    # Get the tool function
    search_tool = None
    for tool_name, tool_fn in mcp._tool_manager._tools.items():
        if tool_name == "search_code_context":
            search_tool = tool_fn
            break
    assert search_tool is not None, "search_code_context tool not registered"

    result = await search_tool.fn(
        query="spring webclient timeout",
        repo="spring-framework",
    )

    parsed = json.loads(result)
    assert parsed["query"] == "spring webclient timeout"
    assert parsed["query_type"] == "nl"
    assert len(parsed["code_results"]) == 1
    assert parsed["code_results"][0]["file_path"] == "src/WebClient.java"
    assert parsed["code_results"][0]["relevance_score"] == 0.95
    assert len(parsed["doc_results"]) == 1
    assert parsed["doc_results"][0]["file_path"] == "docs/webclient.md"


# ---------------------------------------------------------------------------
# A2: Happy path — list_repositories returns JSON array with correct fields
# [unit] — mocks session
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_repositories_returns_all_repos(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """A2: list_repositories returns JSON array with all 7 required fields."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)

    list_tool = None
    for tool_name, tool_fn in mcp._tool_manager._tools.items():
        if tool_name == "list_repositories":
            list_tool = tool_fn
            break
    assert list_tool is not None, "list_repositories tool not registered"

    result = await list_tool.fn()

    parsed = json.loads(result)
    assert len(parsed) == 3

    repo = parsed[0]
    assert "id" in repo
    assert repo["name"] == "spring-framework"
    assert repo["url"] == "https://github.com/spring-projects/spring-framework"
    assert repo["default_branch"] == "main"
    assert repo["indexed_branch"] == "main"
    assert repo["last_indexed_at"] is not None
    assert repo["status"] == "indexed"


# ---------------------------------------------------------------------------
# A3: Happy path — search without repo param searches all repos
# [unit] — mocks QueryHandler
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_code_context_without_repo(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """A3: search_code_context without repo calls QueryHandler with repo=None."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)

    search_tool = None
    for tool_name, tool_fn in mcp._tool_manager._tools.items():
        if tool_name == "search_code_context":
            search_tool = tool_fn
            break

    await search_tool.fn(query="timeout")

    mock_query_handler.handle_nl_query.assert_called_once_with(
        "timeout", None, None
    )


# ---------------------------------------------------------------------------
# A4: Happy path — symbol query dispatches to handle_symbol_query
# [unit] — mocks QueryHandler
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_code_context_symbol_query(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """A4: When detect_query_type returns 'symbol', handle_symbol_query is called."""
    from src.query.mcp_server import create_mcp_server

    mock_query_handler.detect_query_type.return_value = "symbol"

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)

    search_tool = None
    for tool_name, tool_fn in mcp._tool_manager._tools.items():
        if tool_name == "search_code_context":
            search_tool = tool_fn
            break

    result = await search_tool.fn(query="MyClass.method")

    mock_query_handler.handle_symbol_query.assert_called_once_with(
        "MyClass.method", None
    )
    mock_query_handler.handle_nl_query.assert_not_called()

    parsed = json.loads(result)
    assert parsed["query_type"] == "symbol"


# ---------------------------------------------------------------------------
# A5: Happy path — get_chunk returns full content
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

    get_tool = None
    for tool_name, tool_fn in mcp._tool_manager._tools.items():
        if tool_name == "get_chunk":
            get_tool = tool_fn
            break
    assert get_tool is not None, "get_chunk tool not registered"

    result = await get_tool.fn(chunk_id="abc123")

    parsed = json.loads(result)
    assert parsed["file_path"] == "src/WebClient.java"
    assert parsed["content"] == "public class WebClient { /* full content here */ }"
    assert parsed["language"] == "java"
    assert parsed["symbol"] == "WebClient"


# ---------------------------------------------------------------------------
# A6: Happy path — list_repositories with fuzzy filter
# [unit] — mocks session
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_repositories_with_filter(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """A6: list_repositories with query='spring' returns only matching repos."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)

    list_tool = None
    for tool_name, tool_fn in mcp._tool_manager._tools.items():
        if tool_name == "list_repositories":
            list_tool = tool_fn
            break

    result = await list_tool.fn(query="spring")

    parsed = json.loads(result)
    assert len(parsed) == 2
    names = {r["name"] for r in parsed}
    assert names == {"spring-framework", "spring-boot"}


# ---------------------------------------------------------------------------
# B1: Error — empty query raises ValueError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_code_context_empty_query_raises(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """B1: search_code_context with empty query raises ValueError."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)

    search_tool = None
    for tool_name, tool_fn in mcp._tool_manager._tools.items():
        if tool_name == "search_code_context":
            search_tool = tool_fn
            break

    with pytest.raises(ValueError, match="query is required"):
        await search_tool.fn(query="")


# ---------------------------------------------------------------------------
# B2: Error — RetrievalError becomes RuntimeError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_code_context_retrieval_error(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """B2: RetrievalError from QueryHandler is caught and re-raised as RuntimeError."""
    from src.query.mcp_server import create_mcp_server

    mock_query_handler.handle_nl_query = AsyncMock(
        side_effect=RetrievalError("ES timeout")
    )

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)

    search_tool = None
    for tool_name, tool_fn in mcp._tool_manager._tools.items():
        if tool_name == "search_code_context":
            search_tool = tool_fn
            break

    with pytest.raises(RuntimeError, match="Retrieval failed"):
        await search_tool.fn(query="test query")


# ---------------------------------------------------------------------------
# B3: Error — empty chunk_id raises ValueError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_chunk_empty_id_raises(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """B3: get_chunk with empty chunk_id raises ValueError."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)

    get_tool = None
    for tool_name, tool_fn in mcp._tool_manager._tools.items():
        if tool_name == "get_chunk":
            get_tool = tool_fn
            break

    with pytest.raises(ValueError, match="chunk_id is required"):
        await get_tool.fn(chunk_id="")


# ---------------------------------------------------------------------------
# B4: Error — chunk not found raises ValueError
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

    get_tool = None
    for tool_name, tool_fn in mcp._tool_manager._tools.items():
        if tool_name == "get_chunk":
            get_tool = tool_fn
            break

    with pytest.raises(ValueError, match="Chunk not found"):
        await get_tool.fn(chunk_id="nonexistent")


# ---------------------------------------------------------------------------
# B4b: Error — ES connection failure in get_chunk raises RuntimeError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_chunk_es_connection_failure(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """B4b: get_chunk raises RuntimeError when ES connection fails."""
    from src.query.mcp_server import create_mcp_server

    mock_es_client._client.get = AsyncMock(
        side_effect=ConnectionError("ES connection refused")
    )

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)

    get_tool = None
    for tool_name, tool_fn in mcp._tool_manager._tools.items():
        if tool_name == "get_chunk":
            get_tool = tool_fn
            break

    with pytest.raises(RuntimeError, match="Failed to retrieve chunk"):
        await get_tool.fn(chunk_id="abc123")


# ---------------------------------------------------------------------------
# B5: Error — DB failure in list_repositories raises RuntimeError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_repositories_db_failure(
    mock_query_handler, mock_es_client
):
    """B5: list_repositories raises RuntimeError on DB session failure."""
    from src.query.mcp_server import create_mcp_server

    failing_session = AsyncMock()
    failing_session.execute = AsyncMock(side_effect=Exception("DB connection lost"))
    failing_session.close = AsyncMock()

    factory = MagicMock()
    factory.return_value = failing_session

    mcp = create_mcp_server(mock_query_handler, factory, mock_es_client)

    list_tool = None
    for tool_name, tool_fn in mcp._tool_manager._tools.items():
        if tool_name == "list_repositories":
            list_tool = tool_fn
            break

    with pytest.raises(RuntimeError, match="Failed to list repositories"):
        await list_tool.fn()


# ---------------------------------------------------------------------------
# B6: Error — ValidationError becomes ValueError
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

    search_tool = None
    for tool_name, tool_fn in mcp._tool_manager._tools.items():
        if tool_name == "search_code_context":
            search_tool = tool_fn
            break

    with pytest.raises(ValueError, match="Unsupported language: rust"):
        await search_tool.fn(query="test query")


# ---------------------------------------------------------------------------
# C1: Boundary — whitespace-only query raises ValueError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_code_context_whitespace_query_raises(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """C1: search_code_context with whitespace-only query raises ValueError."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)

    search_tool = None
    for tool_name, tool_fn in mcp._tool_manager._tools.items():
        if tool_name == "search_code_context":
            search_tool = tool_fn
            break

    with pytest.raises(ValueError, match="query is required"):
        await search_tool.fn(query="   ")


# ---------------------------------------------------------------------------
# C2: Boundary — whitespace-only chunk_id raises ValueError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_chunk_whitespace_id_raises(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """C2: get_chunk with whitespace-only chunk_id raises ValueError."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)

    get_tool = None
    for tool_name, tool_fn in mcp._tool_manager._tools.items():
        if tool_name == "get_chunk":
            get_tool = tool_fn
            break

    with pytest.raises(ValueError, match="chunk_id is required"):
        await get_tool.fn(chunk_id="   ")


# ---------------------------------------------------------------------------
# C3: Boundary — empty string filter returns all repos
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_repositories_empty_filter_returns_all(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """C3: list_repositories with empty string query returns all repos (no filter)."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)

    list_tool = None
    for tool_name, tool_fn in mcp._tool_manager._tools.items():
        if tool_name == "list_repositories":
            list_tool = tool_fn
            break

    result = await list_tool.fn(query="")

    parsed = json.loads(result)
    assert len(parsed) == 3


# ---------------------------------------------------------------------------
# C4: Boundary — single char query accepted
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_code_context_single_char_query(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """C4: search_code_context with single character query is accepted."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)

    search_tool = None
    for tool_name, tool_fn in mcp._tool_manager._tools.items():
        if tool_name == "search_code_context":
            search_tool = tool_fn
            break

    result = await search_tool.fn(query="x")

    # Should not raise — handler was called
    mock_query_handler.handle_nl_query.assert_called()
    parsed = json.loads(result)
    assert "query" in parsed


# ---------------------------------------------------------------------------
# C5: Boundary — case-insensitive filter
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_repositories_case_insensitive_filter(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """C5: list_repositories with uppercase query matches case-insensitively."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)

    list_tool = None
    for tool_name, tool_fn in mcp._tool_manager._tools.items():
        if tool_name == "list_repositories":
            list_tool = tool_fn
            break

    result = await list_tool.fn(query="SPRING")

    parsed = json.loads(result)
    assert len(parsed) == 2
    names = {r["name"] for r in parsed}
    assert "spring-framework" in names
    assert "spring-boot" in names


# ---------------------------------------------------------------------------
# Integration: MCP server tool registration
# [integration] — verifies FastMCP tool registration (real mcp SDK)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mcp_server_registers_three_tools(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """Integration: create_mcp_server registers exactly 3 tools with correct names."""
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)

    tool_names = set(mcp._tool_manager._tools.keys())
    assert tool_names == {"search_code_context", "list_repositories", "get_chunk"}


# ---------------------------------------------------------------------------
# Real tests — Feature #18: MCP SDK integration
# [integration] — verifies real mcp SDK tool registration and schema generation
# ---------------------------------------------------------------------------

@pytest.mark.real
@pytest.mark.asyncio
async def test_real_mcp_sdk_tool_registration_feature_18(
    mock_query_handler, mock_session_factory, mock_es_client
):
    """Real test: FastMCP SDK registers tools with correct input schemas.

    Verifies the real mcp SDK (no mocking of SDK internals) correctly
    parses our tool function signatures and generates valid JSON schemas.
    Feature #18 — MCP Server.
    """
    from src.query.mcp_server import create_mcp_server

    mcp = create_mcp_server(mock_query_handler, mock_session_factory, mock_es_client)

    # Verify tool count
    tools = mcp._tool_manager._tools
    assert len(tools) == 3

    # Verify search_code_context schema has required 'query' param
    search_tool = tools["search_code_context"]
    schema = search_tool.parameters
    assert "query" in schema.get("properties", {})
    assert "query" in schema.get("required", [])
    # Optional params should exist but not be required
    assert "repo" in schema["properties"]
    assert "repo" not in schema.get("required", [])

    # Verify list_repositories has optional query param
    list_tool = tools["list_repositories"]
    list_schema = list_tool.parameters
    assert "query" in list_schema.get("properties", {})

    # Verify get_chunk has required chunk_id param
    get_tool = tools["get_chunk"]
    get_schema = get_tool.parameters
    assert "chunk_id" in get_schema.get("properties", {})
    assert "chunk_id" in get_schema.get("required", [])
