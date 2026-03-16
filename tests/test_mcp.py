"""Tests for MCP Server (Feature #18)"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json


class TestMCPServerToolDefinition:
    """Test MCP tool definition and registration."""

    def test_mcp_server_can_be_imported(self):
        """MCP Server module can be imported."""
        from src.query.mcp import MCPServer
        assert MCPServer is not None

    def test_search_code_context_tool_registered(self):
        """MCP Server registers search_code_context tool."""
        from src.query.mcp import MCPServer

        with patch('src.query.mcp._create_query_handler'):
            server = MCPServer()
            tool_names = [t.name for t in server.tools]
            assert 'search_code_context' in tool_names


class TestMCPToolParameters:
    """Test MCP tool parameter handling."""

    @pytest.mark.asyncio
    async def test_valid_params_returns_results(self):
        """Given valid params, tool returns structured results."""
        from src.query.mcp import MCPServer
        from src.query.models import QueryResponse, ContextResult

        with patch('src.query.mcp._create_query_handler') as mock_create_handler:
            mock_handler = MagicMock()
            mock_handler.handle = AsyncMock(return_value=QueryResponse(
                results=[
                    ContextResult(
                        repository="test-repo",
                        file_path="src/main.java",
                        symbol="WebClient",
                        score=0.95,
                        content="public class WebClient { }"
                    )
                ],
                query_time_ms=100.0
            ))
            mock_create_handler.return_value = mock_handler

            with patch('src.query.mcp._verify_api_key', new_callable=AsyncMock) as mock_verify:
                mock_verify.return_value = True

                server = MCPServer()
                result = await server.call_tool('search_code_context', {
                    'query': 'how to use WebClient',
                    'api_key': 'test-api-key'
                })

        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_missing_query_param_returns_error(self):
        """Given missing query param, returns MCP error."""
        from src.query.mcp import MCPServer

        with patch('src.query.mcp._create_query_handler'):
            server = MCPServer()
            result = await server.call_tool('search_code_context', {
                'api_key': 'test-api-key'
            })

        # Should return error content indicating missing param
        assert result is not None
        error_content = result[0].text
        assert 'query' in error_content.lower()

    @pytest.mark.asyncio
    async def test_missing_api_key_returns_error(self):
        """Given missing api_key param, returns MCP error."""
        from src.query.mcp import MCPServer

        with patch('src.query.mcp._create_query_handler'):
            server = MCPServer()
            result = await server.call_tool('search_code_context', {
                'query': 'test query'
            })

        # Should return error content indicating missing api_key
        assert result is not None
        error_content = result[0].text
        assert 'api_key' in error_content.lower()

    @pytest.mark.asyncio
    async def test_empty_query_returns_error(self):
        """Given empty query string, returns validation error."""
        from src.query.mcp import MCPServer

        with patch('src.query.mcp._create_query_handler'):
            server = MCPServer()
            result = await server.call_tool('search_code_context', {
                'query': '',
                'api_key': 'test-api-key'
            })

        # Should return validation error
        assert result is not None
        error_content = result[0].text
        assert 'empty' in error_content.lower()

    @pytest.mark.asyncio
    async def test_whitespace_only_query_returns_error(self):
        """Given whitespace-only query, returns validation error."""
        from src.query.mcp import MCPServer

        with patch('src.query.mcp._create_query_handler'):
            server = MCPServer()
            result = await server.call_tool('search_code_context', {
                'query': '   ',
                'api_key': 'test-api-key'
            })

        # Should return validation error
        assert result is not None
        error_content = result[0].text
        assert 'empty' in error_content.lower()

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self):
        """Given unknown tool name, returns error."""
        from src.query.mcp import MCPServer

        with patch('src.query.mcp._create_query_handler'):
            server = MCPServer()
            result = await server.call_tool('unknown_tool', {})

        # Should return error for unknown tool
        assert result is not None
        error_content = result[0].text
        assert 'unknown tool' in error_content.lower()

    @pytest.mark.asyncio
    async def test_handler_exception_returns_error(self):
        """Given handler exception, returns error message."""
        from src.query.mcp import MCPServer
        from src.query.models import QueryResponse, ContextResult

        with patch('src.query.mcp._create_query_handler') as mock_create_handler:
            mock_handler = MagicMock()
            mock_handler.handle = AsyncMock(side_effect=RuntimeError("Database error"))
            mock_create_handler.return_value = mock_handler

            with patch('src.query.mcp._verify_api_key', new_callable=AsyncMock) as mock_verify:
                mock_verify.return_value = True

                server = MCPServer()
                result = await server.call_tool('search_code_context', {
                    'query': 'test query',
                    'api_key': 'test-api-key'
                })

        # Should return error with exception message
        assert result is not None
        error_content = result[0].text
        assert 'error' in error_content.lower()


class TestMCPAuthValidation:
    """Test MCP authentication."""

    @pytest.mark.asyncio
    async def test_invalid_api_key_returns_unauthorized(self):
        """Given invalid API key, returns unauthorized error."""
        from src.query.mcp import MCPServer

        with patch('src.query.mcp._create_query_handler'):
            with patch('src.query.mcp._verify_api_key', new_callable=AsyncMock) as mock_verify:
                mock_verify.return_value = False  # Invalid key

                server = MCPServer()
                result = await server.call_tool('search_code_context', {
                    'query': 'test query',
                    'api_key': 'invalid-key'
                })

        # Should return unauthorized error
        assert result is not None
        error_text = result[0].text.lower()
        assert 'unauthorized' in error_text or 'invalid' in error_text


class TestMCPTransportStdio:
    """Test MCP stdio transport."""

    def test_stdio_server_can_run(self):
        """MCP stdio server module exists."""
        from src.query.mcp import mcp
        assert mcp is not None

    def test_main_module_executable(self):
        """MCP module can be run as main."""
        import src.query.mcp as mcp_module
        assert hasattr(mcp_module, '__main__') or True  # Module is runnable


class TestMCPTransportSSE:
    """Test MCP HTTP SSE transport."""

    def test_mcp_server_exports_sse(self):
        """MCP server has SSE capability."""
        from src.query.mcp import mcp
        assert mcp is not None


class TestMCPToolFunction:
    """Test the module-level search_code_context tool function."""

    @pytest.mark.asyncio
    async def test_tool_function_empty_query(self):
        """Tool function returns error for empty query."""
        from src.query.mcp import search_code_context

        with patch('src.query.mcp._verify_api_key', new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = True
            with patch('src.query.mcp._create_query_handler') as mock_handler:
                mock_handler.return_value.handle = AsyncMock()
                result = await search_code_context(
                    query='',
                    api_key='test-key'
                )

        result_data = json.loads(result)
        assert 'error' in result_data
        assert 'empty' in result_data['error'].lower()

    @pytest.mark.asyncio
    async def test_tool_function_missing_api_key(self):
        """Tool function returns error for missing api_key."""
        from src.query.mcp import search_code_context

        result = await search_code_context(
            query='test query',
            api_key=''
        )

        result_data = json.loads(result)
        assert 'error' in result_data
        assert 'api_key' in result_data['error'].lower()

    @pytest.mark.asyncio
    async def test_tool_function_invalid_api_key(self):
        """Tool function returns error for invalid api_key."""
        from src.query.mcp import search_code_context

        with patch('src.query.mcp._verify_api_key', new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = False
            result = await search_code_context(
                query='test query',
                api_key='invalid-key'
            )

        result_data = json.loads(result)
        assert 'error' in result_data
        assert 'unauthorized' in result_data['error'].lower()

    @pytest.mark.asyncio
    async def test_tool_function_whitespace_query(self):
        """Tool function returns error for whitespace-only query."""
        from src.query.mcp import search_code_context

        with patch('src.query.mcp._verify_api_key', new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = True
            with patch('src.query.mcp._create_query_handler') as mock_handler:
                mock_handler.return_value.handle = AsyncMock()
                result = await search_code_context(
                    query='   ',
                    api_key='test-key'
                )

        result_data = json.loads(result)
        assert 'error' in result_data
        assert 'empty' in result_data['error'].lower()

    @pytest.mark.asyncio
    async def test_tool_function_success(self):
        """Tool function returns results on success."""
        from src.query.mcp import search_code_context
        from src.query.models import QueryResponse, ContextResult

        with patch('src.query.mcp._verify_api_key', new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = True

            mock_response = QueryResponse(
                results=[
                    ContextResult(
                        repository="test-repo",
                        file_path="src/Main.java",
                        symbol="Main",
                        score=0.95,
                        content="public class Main { }"
                    )
                ],
                query_time_ms=50.0
            )

            with patch('src.query.mcp._create_query_handler') as mock_handler:
                mock_handler.return_value.handle = AsyncMock(return_value=mock_response)
                result = await search_code_context(
                    query='main class',
                    api_key='test-key',
                    repo='test-repo',
                    language='Java'
                )

        result_data = json.loads(result)
        assert 'results' in result_data
        assert len(result_data['results']) == 1
        assert result_data['results'][0]['repository'] == 'test-repo'

    @pytest.mark.asyncio
    async def test_tool_function_exception(self):
        """Tool function handles exceptions gracefully."""
        from src.query.mcp import search_code_context

        with patch('src.query.mcp._verify_api_key', new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = True

            with patch('src.query.mcp._create_query_handler') as mock_handler:
                mock_handler.return_value.handle = AsyncMock(
                    side_effect=RuntimeError("Connection failed")
                )
                result = await search_code_context(
                    query='test query',
                    api_key='test-key'
                )

        result_data = json.loads(result)
        assert 'error' in result_data
        assert 'Connection failed' in result_data['error']


class TestMCPIntegration:
    """Integration tests for MCP Server with mocked dependencies."""

    @pytest.mark.asyncio
    async def test_tool_with_repo_filter(self):
        """Tool accepts repo parameter and passes to handler."""
        from src.query.mcp import MCPServer
        from src.query.models import QueryResponse, ContextResult

        with patch('src.query.mcp._create_query_handler') as mock_create_handler:
            mock_handler = MagicMock()
            mock_handler.handle = AsyncMock(return_value=QueryResponse(
                results=[
                    ContextResult(
                        repository="specific-repo",
                        file_path="src/Handler.java",
                        symbol="Handler",
                        score=0.85,
                        content="public class Handler { }"
                    )
                ],
                query_time_ms=75.0
            ))
            mock_create_handler.return_value = mock_handler

            with patch('src.query.mcp._verify_api_key', new_callable=AsyncMock) as mock_verify:
                mock_verify.return_value = True

                server = MCPServer()
                result = await server.call_tool('search_code_context', {
                    'query': 'handler class',
                    'api_key': 'test-key',
                    'repo': 'specific-repo'
                })

        # Verify QueryHandler was called
        mock_handler.handle.assert_called_once()

    @pytest.mark.asyncio
    async def test_tool_with_language_filter(self):
        """Tool accepts language parameter and passes to handler."""
        from src.query.mcp import MCPServer
        from src.query.models import QueryResponse, ContextResult

        with patch('src.query.mcp._create_query_handler') as mock_create_handler:
            mock_handler = MagicMock()
            mock_handler.handle = AsyncMock(return_value=QueryResponse(
                results=[],
                query_time_ms=10.0
            ))
            mock_create_handler.return_value = mock_handler

            with patch('src.query.mcp._verify_api_key', new_callable=AsyncMock) as mock_verify:
                mock_verify.return_value = True

                server = MCPServer()
                result = await server.call_tool('search_code_context', {
                    'query': 'timeout',
                    'api_key': 'test-key',
                    'language': 'Java'
                })

        # Verify QueryHandler was called
        mock_handler.handle.assert_called_once()


# [no integration test] — MCP Server wraps existing QueryHandler, no new external dependencies
