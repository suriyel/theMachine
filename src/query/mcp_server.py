"""MCP Server — Features #18, #46 (Wave 5).

Standalone MCP server exposing resolve_repository, search_code_context, and
get_chunk tools via the Model Context Protocol.  Delegates to the same
QueryHandler used by the REST API.

Wave 5: Context7-aligned two-step flow (resolve → search).
- resolve_repository replaces list_repositories
- repo is required in search_code_context
- max_tokens removed
- Feature #46: match quality sorting + available_branches population
"""

import json
import logging

from elasticsearch import NotFoundError
from mcp.server.fastmcp import FastMCP
from sqlalchemy import select

from src.query.exceptions import RetrievalError
from src.shared.exceptions import ValidationError
from src.shared.models.repository import Repository

logger = logging.getLogger(__name__)


def _score_match(name: str, url: str, library_name_lower: str) -> int:
    """Score a repository's match quality against a library name.

    Returns:
        Integer tier: 0=exact name, 1=exact URL segment, 2=prefix name,
        3=prefix URL segment, 4=substring. -1 if no match.
    """
    name_lower = name.lower()
    url_lower = url.lower()
    url_segment = url.rstrip("/").rsplit("/", 1)[-1].lower()

    if name_lower == library_name_lower:
        return 0
    if url_segment == library_name_lower:
        return 1
    if name_lower.startswith(library_name_lower):
        return 2
    if url_segment.startswith(library_name_lower):
        return 3
    if library_name_lower in name_lower or library_name_lower in url_lower:
        return 4
    return -1


def _populate_branches(repo, git_cloner) -> list[str]:
    """Get available branches for a repository, with graceful degradation.

    Returns empty list if git_cloner is None, clone_path is missing,
    or any git error occurs.
    """
    if git_cloner is None:
        return []
    if not repo.clone_path:
        return []
    try:
        return git_cloner.list_remote_branches(repo.clone_path)
    except Exception:
        logger.warning(
            "Failed to list branches for %s at %s",
            repo.name, repo.clone_path,
        )
        return []


def create_mcp_server(
    query_handler,
    session_factory,
    es_client,
    git_cloner=None,
) -> FastMCP:
    """Create and configure the MCP server with 3 tools.

    Args:
        query_handler: QueryHandler instance for search operations.
        session_factory: Async session factory for DB access.
        es_client: ElasticsearchClient for chunk retrieval.
        git_cloner: Optional GitCloner for populating available_branches.

    Returns:
        Configured FastMCP instance with resolve_repository,
        search_code_context, and get_chunk tools registered.
    """
    mcp = FastMCP("code-context-retrieval")

    @mcp.tool()
    async def resolve_repository(query: str, libraryName: str) -> str:
        """Resolve a repository name to indexed repositories with branch info.

        Returns only status=indexed repositories matching the libraryName.
        Must be called before search_code_context to discover repo identifiers.

        Args:
            query: User intent for relevance ranking.
            libraryName: Repository name to search (case-insensitive substring match).
        """
        if not query or not query.strip():
            raise ValueError("query is required")
        if not libraryName or not libraryName.strip():
            raise ValueError("libraryName is required")

        session = session_factory()
        try:
            result = await session.execute(
                select(Repository).where(Repository.status == "indexed")
            )
            repos = result.scalars().all()
        except Exception as exc:
            raise RuntimeError(
                f"Failed to resolve repositories: {exc}"
            ) from exc
        finally:
            await session.close()

        lib_lower = libraryName.strip().lower()

        # Score and filter repos by match quality
        scored = []
        for r in repos:
            tier = _score_match(r.name, r.url, lib_lower)
            if tier >= 0:
                scored.append((tier, r))

        # Sort by tier ascending (exact=0 first, substring=4 last)
        scored.sort(key=lambda x: x[0])

        # Build response with branch population
        return json.dumps(
            [
                {
                    "id": r.name,
                    "name": r.name,
                    "url": r.url,
                    "indexed_branch": r.indexed_branch,
                    "default_branch": r.default_branch,
                    "available_branches": _populate_branches(
                        r, git_cloner
                    ),
                    "last_indexed_at": (
                        r.last_indexed_at.isoformat()
                        if r.last_indexed_at
                        else None
                    ),
                }
                for _, r in scored
            ]
        )

    @mcp.tool()
    async def search_code_context(
        query: str,
        repo: str,
        top_k: int = 3,
        languages: list[str] | None = None,
    ) -> str:
        """Search code and documentation context scoped to a repository.

        Args:
            query: Natural language or symbol query string.
            repo: Repository identifier (required). Use "owner/repo" or
                "owner/repo@branch" format. @branch suffix is parsed by
                QueryHandler internally.
            top_k: Number of results to return (default 3).
            languages: Optional list of programming languages to filter by.
        """
        if not query or not query.strip():
            raise ValueError("query is required")

        query_type = query_handler.detect_query_type(query)

        try:
            if query_type == "symbol":
                response = await query_handler.handle_symbol_query(query, repo, languages)
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
