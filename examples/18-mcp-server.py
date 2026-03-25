"""Example: MCP Server — Feature #18 (Wave 5).

Demonstrates the Context7-aligned two-step MCP flow:
  1. resolve_repository(query, libraryName) — discover indexed repos
  2. search_code_context(query, repo) — search scoped to a specific repo
  3. get_chunk(chunk_id) — retrieve full chunk content

Wave 5 changes:
  - resolve_repository replaces list_repositories
  - repo is required in search_code_context (no default)
  - @branch suffix supported: repo="owner/repo@branch"
  - max_tokens parameter removed

Usage:
    python examples/18-mcp-server.py
"""

from __future__ import annotations

import asyncio
import json


async def demo_mcp_server_wave5():
    """Show the Wave 5 MCP server tool registration and two-step flow."""
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

    # Verify Wave 5 changes
    assert "resolve_repository" in tools, "resolve_repository must be registered"
    assert "list_repositories" not in tools, "list_repositories replaced in Wave 5"
    assert "search_code_context" in tools
    assert "get_chunk" in tools

    # Show resolve_repository schema (both params required)
    resolve_schema = tools["resolve_repository"].parameters
    print("resolve_repository input schema:")
    print(json.dumps(resolve_schema, indent=2))
    print()

    # Show search_code_context schema (repo is required, no max_tokens)
    search_schema = tools["search_code_context"].parameters
    print("search_code_context input schema:")
    print(json.dumps(search_schema, indent=2))
    assert "repo" in search_schema.get("required", []), "repo must be required"
    assert "max_tokens" not in search_schema.get("properties", {}), "max_tokens removed"

    print()
    print("Two-step flow:")
    print("  1. resolve_repository(query='JSON parse', libraryName='gson')")
    print("     -> [{id: 'google/gson', indexed_branch: 'main', ...}]")
    print("  2. search_code_context(query='JSON parse', repo='google/gson')")
    print("     -> {code_results: [...], doc_results: [...]}")
    print("  2b. search_code_context(query='JSON parse', repo='google/gson@v2.10')")
    print("      -> branch-filtered results")
    print("  3. get_chunk(chunk_id='abc123')  # optional: get full content")


if __name__ == "__main__":
    asyncio.run(demo_mcp_server_wave5())
