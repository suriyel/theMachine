"""MCP Server — Feature #18.

Standalone MCP server exposing search_code_context, list_repositories, and
get_chunk tools via the Model Context Protocol.  Delegates to the same
QueryHandler used by the REST API.
"""

import json
from typing import Optional

from elasticsearch import NotFoundError
from mcp.server.fastmcp import FastMCP
from sqlalchemy import select

from src.query.exceptions import RetrievalError
from src.shared.exceptions import ValidationError
from src.shared.models.repository import Repository


def create_mcp_server(
    query_handler,
    session_factory,
    es_client,
) -> FastMCP:
    """Create and configure the MCP server with 3 tools.

    Args:
        query_handler: QueryHandler instance for search operations.
        session_factory: Async session factory for DB access.
        es_client: ElasticsearchClient for chunk retrieval.

    Returns:
        Configured FastMCP instance with search_code_context,
        list_repositories, and get_chunk tools registered.
    """
    mcp = FastMCP("code-context-retrieval")

    @mcp.tool()
    async def search_code_context(
        query: str,
        repo: Optional[str] = None,
        top_k: int = 3,
        languages: Optional[list[str]] = None,
        max_tokens: int = 5000,
    ) -> str:
        """Search code and documentation context.

        Returns structured results with code snippets, documentation,
        and repository rules.

        Args:
            query: Natural language or symbol query string.
            repo: Optional repository name to scope the search.
            top_k: Number of results to return (default 3).
                Reserved for future use — QueryHandler does not yet
                accept top_k; included per design spec §4.3.4.
            languages: Optional list of programming languages to filter by.
            max_tokens: Maximum response size in tokens (default 5000).
                Reserved for future use — response truncation by token
                budget not yet implemented; included per design spec §4.3.4.
        """
        if not query or not query.strip():
            raise ValueError("query is required")

        query_type = query_handler.detect_query_type(query)

        try:
            if query_type == "symbol":
                response = await query_handler.handle_symbol_query(query, repo)
            else:
                response = await query_handler.handle_nl_query(
                    query, repo, languages
                )
        except RetrievalError as exc:
            raise RuntimeError(f"Retrieval failed: {exc}") from exc
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc

        return response.model_dump_json()

    @mcp.tool()
    async def list_repositories(query: Optional[str] = None) -> str:
        """List indexed repositories.

        Args:
            query: Optional filter — matches against repository name or URL
                   (case-insensitive substring match).
        """
        session = session_factory()
        try:
            result = await session.execute(select(Repository))
            repos = result.scalars().all()
        except Exception as exc:
            raise RuntimeError(f"Failed to list repositories: {exc}") from exc
        finally:
            await session.close()

        if query and query.strip():
            query_lower = query.lower()
            repos = [
                r
                for r in repos
                if query_lower in r.name.lower()
                or query_lower in r.url.lower()
            ]

        return json.dumps(
            [
                {
                    "id": str(r.id),
                    "name": r.name,
                    "url": r.url,
                    "default_branch": r.default_branch,
                    "indexed_branch": r.indexed_branch,
                    "last_indexed_at": (
                        r.last_indexed_at.isoformat()
                        if r.last_indexed_at
                        else None
                    ),
                    "status": r.status,
                }
                for r in repos
            ]
        )

    @mcp.tool()
    async def get_chunk(chunk_id: str) -> str:
        """Get full content of a specific chunk by ID.

        Bypasses the truncation limit so the agent can retrieve
        the complete content of a previously truncated result.

        Args:
            chunk_id: The Elasticsearch document ID of the chunk.
        """
        if not chunk_id or not chunk_id.strip():
            raise ValueError("chunk_id is required")

        try:
            doc = await es_client._client.get(index="code_chunks", id=chunk_id)
        except NotFoundError:
            try:
                doc = await es_client._client.get(
                    index="doc_chunks", id=chunk_id
                )
            except NotFoundError:
                raise ValueError(f"Chunk not found: {chunk_id}")
        except Exception as exc:
            raise RuntimeError(f"Failed to retrieve chunk: {exc}") from exc

        return json.dumps(doc["_source"])

    return mcp
