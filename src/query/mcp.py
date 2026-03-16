"""MCP Server for Code Context Retrieval.

Provides search_code_context tool via MCP protocol with stdio and HTTP SSE transport.
"""
import json
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP
from mcp.types import Tool, TextContent

from src.query.handler import QueryHandler
from src.query.rank_fusion import RankFusion
from src.query.reranker import NeuralReranker
from src.query.response_builder import ContextResponseBuilder
from src.query.retriever import KeywordRetriever, SemanticRetriever
from src.query.models import QueryRequest
from src.shared.clients import get_elasticsearch, get_qdrant


# Create MCP server instance
mcp = FastMCP(
    name="code-context-retrieval",
    instructions="Code Context Retrieval MCP Server - provides search_code_context tool"
)


def _create_query_handler() -> QueryHandler:
    """Create QueryHandler with all dependencies wired."""
    es_client = get_elasticsearch()
    qdrant_client = get_qdrant()

    keyword_retriever = KeywordRetriever(es_client=es_client)
    semantic_retriever = SemanticRetriever(qdrant_client=qdrant_client)
    rank_fusion = RankFusion()
    reranker = NeuralReranker()
    response_builder = ContextResponseBuilder()

    return QueryHandler(
        keyword_retriever=keyword_retriever,
        semantic_retriever=semantic_retriever,
        rank_fusion=rank_fusion,
        reranker=reranker,
        response_builder=response_builder,
    )


async def _verify_api_key(api_key: str) -> bool:
    """Verify API key using the database.

    Args:
        api_key: The API key to verify

    Returns:
        True if valid, False otherwise
    """
    from src.query.auth import AuthMiddleware
    from src.shared.db.session import async_session_maker

    async with async_session_maker() as db:
        auth = AuthMiddleware(db)
        result = await auth.verify_api_key(api_key)
        return result is not None


class MCPServer:
    """MCP Server for Code Context Retrieval."""

    def __init__(self):
        self._mcp = mcp
        self._handler = _create_query_handler()
        self._tools = [
            Tool(
                name="search_code_context",
                description="Search code context using natural language or symbol queries",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language or symbol query"
                        },
                        "api_key": {
                            "type": "string",
                            "description": "API key for authentication"
                        },
                        "repo": {
                            "type": "string",
                            "description": "Optional repository name filter"
                        },
                        "language": {
                            "type": "string",
                            "description": "Optional programming language filter (Java, Python, TypeScript, JavaScript, C, C++)"
                        }
                    },
                    "required": ["query", "api_key"]
                }
            )
        ]

    @property
    def tools(self):
        return self._tools

    @property
    def app(self):
        """Return the FastAPI app for SSE transport."""
        return self._mcp.app

    async def call_tool(self, name: str, arguments: dict) -> list[TextContent]:
        """Call a tool with the given arguments."""
        if name != "search_code_context":
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

        # Validate required parameters
        query = arguments.get("query")
        api_key = arguments.get("api_key")

        if query is None:
            return [TextContent(type="text", text=json.dumps({"error": "Missing required parameter: query"}))]

        if api_key is None:
            return [TextContent(type="text", text=json.dumps({"error": "Missing required parameter: api_key"}))]

        # Validate query is not empty/whitespace
        if not query or not query.strip():
            return [TextContent(type="text", text=json.dumps({"error": "Query must not be empty"}))]

        # Validate API key
        is_valid = await _verify_api_key(api_key)
        if not is_valid:
            return [TextContent(type="text", text=json.dumps({"error": "Unauthorized: invalid API key"}))]

        # Build query request
        repo_filter = arguments.get("repo")
        language_filter = arguments.get("language")

        query_request = QueryRequest(
            query=query,
            query_type="natural_language",
            repo_filter=repo_filter,
            language_filter=language_filter
        )

        # Execute query
        try:
            response = await self._handler.handle(query_request)

            # Format results
            results = [
                {
                    "repository": r.repository,
                    "file_path": r.file_path,
                    "symbol": r.symbol,
                    "score": r.score,
                    "content": r.content
                }
                for r in response.results
            ]

            return [TextContent(type="text", text=json.dumps({
                "results": results,
                "query_time_ms": response.query_time_ms
            }))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


# Tool implementation for FastMCP
@mcp.tool()
async def search_code_context(
    query: str,
    api_key: str,
    repo: Optional[str] = None,
    language: Optional[str] = None
) -> str:
    """Search code context using natural language or symbol queries."""
    # Validate required parameters
    if not query or not query.strip():
        return json.dumps({"error": "Query must not be empty"})

    if not api_key:
        return json.dumps({"error": "Missing required parameter: api_key"})

    # Validate API key
    is_valid = await _verify_api_key(api_key)
    if not is_valid:
        return json.dumps({"error": "Unauthorized: invalid API key"})

    # Initialize handler
    handler = _create_query_handler()

    # Build query request
    query_request = QueryRequest(
        query=query,
        query_type="natural_language",
        repo_filter=repo,
        language_filter=language
    )

    # Execute query
    try:
        response = await handler.handle(query_request)

        # Format results
        results = [
            {
                "repository": r.repository,
                "file_path": r.file_path,
                "symbol": r.symbol,
                "score": r.score,
                "content": r.content
            }
            for r in response.results
        ]

        return json.dumps({
            "results": results,
            "query_time_ms": response.query_time_ms
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    # Run stdio server
    mcp.run()
