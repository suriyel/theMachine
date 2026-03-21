"""Example: MCP Server — Feature #18.

Demonstrates how to create and configure the MCP server with the
search_code_context, list_repositories, and get_chunk tools.

Usage:
    # To run as a standalone MCP server (stdio transport):
    python examples/18-mcp-server.py

    # To use as a library:
    from src.query.mcp_server import create_mcp_server
    mcp = create_mcp_server(query_handler, session_factory, es_client)
"""

from __future__ import annotations

import asyncio
import json


async def demo_mcp_server_creation():
    """Show how to create an MCP server instance."""
    # In production, these would be real service instances:
    #   from src.query.query_handler import QueryHandler
    #   from src.shared.clients.elasticsearch import ElasticsearchClient
    #   query_handler = QueryHandler(retriever, rank_fusion, reranker, response_builder)
    #   es_client = ElasticsearchClient(url="http://localhost:9200")
    #   session_factory = get_session_factory(database_url)

    # For this demo, we show the tool registration structure
    from src.query.mcp_server import create_mcp_server

    # Use None placeholders (tools won't be callable without real services)
    mcp = create_mcp_server(
        query_handler=None,
        session_factory=None,
        es_client=None,
    )

    # Inspect registered tools
    tools = mcp._tool_manager._tools
    print(f"MCP Server: {mcp.name}")
    print(f"Registered tools: {len(tools)}")
    print()

    for name, tool in tools.items():
        print(f"Tool: {name}")
        print(f"  Description: {tool.description[:80]}...")
        schema = tool.parameters
        required = schema.get("required", [])
        optional = [
            k for k in schema.get("properties", {}) if k not in required
        ]
        print(f"  Required params: {required}")
        print(f"  Optional params: {optional}")
        print()

    # Show the input schema for search_code_context
    search_schema = tools["search_code_context"].parameters
    print("search_code_context input schema:")
    print(json.dumps(search_schema, indent=2))


if __name__ == "__main__":
    asyncio.run(demo_mcp_server_creation())
