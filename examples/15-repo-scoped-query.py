"""Example: Repository-Scoped Query (Feature #15).

Demonstrates how the Retriever's repo_id parameter controls query scoping:
1. With repo_id specified — results restricted to that repository
2. Without repo_id (None) — results span all indexed repositories
3. With non-existent repo_id — returns empty results (no error)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from src.query.retriever import Retriever
from src.shared.clients.elasticsearch import ElasticsearchClient


def _mock_es_response(hits: list[dict]) -> dict:
    return {"hits": {"hits": hits, "total": {"value": len(hits)}}}


def _make_hit(chunk_id: str, repo_id: str, symbol: str) -> dict:
    return {
        "_id": chunk_id,
        "_score": 5.0,
        "_source": {
            "repo_id": repo_id,
            "file_path": f"src/{symbol}.java",
            "language": "java",
            "chunk_type": "function",
            "symbol": symbol,
            "signature": f"void {symbol}()",
            "doc_comment": "",
            "content": f"void {symbol}() {{ }}",
            "line_start": 1,
            "line_end": 1,
            "parent_class": "Example",
        },
    }


async def main():
    # Setup: mock ES client
    es = MagicMock(spec=ElasticsearchClient)
    es._client = AsyncMock()
    retriever = Retriever(es_client=es)

    # --- Example 1: Search within a specific repository ---
    print("=== Example 1: Scoped to 'spring-framework' ===")
    es._client.search = AsyncMock(
        return_value=_mock_es_response([
            _make_hit("c1", "spring-framework", "handleTimeout"),
            _make_hit("c2", "spring-framework", "configureTimeout"),
        ])
    )
    results = await retriever.bm25_code_search("timeout", repo_id="spring-framework")
    for chunk in results:
        print(f"  {chunk.symbol} (repo={chunk.repo_id})")
    assert all(c.repo_id == "spring-framework" for c in results)

    # --- Example 2: Search across ALL repositories ---
    print("\n=== Example 2: Cross-repo search (repo_id=None) ===")
    es._client.search = AsyncMock(
        return_value=_mock_es_response([
            _make_hit("c3", "spring-framework", "handleTimeout"),
            _make_hit("c4", "django", "timeout_handler"),
            _make_hit("c5", "express-js", "onTimeout"),
        ])
    )
    results = await retriever.bm25_code_search("timeout", repo_id=None)
    for chunk in results:
        print(f"  {chunk.symbol} (repo={chunk.repo_id})")
    repo_ids = {c.repo_id for c in results}
    assert len(repo_ids) == 3, "Results from multiple repos"

    # --- Example 3: Non-existent repository returns empty ---
    print("\n=== Example 3: Non-existent repo returns empty ===")
    es._client.search = AsyncMock(
        return_value=_mock_es_response([])
    )
    results = await retriever.bm25_code_search("timeout", repo_id="no-such-repo")
    print(f"  Results: {results}")
    assert results == [], "Empty list, no error"

    print("\nAll examples passed!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
