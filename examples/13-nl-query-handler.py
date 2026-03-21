"""Example: Natural Language Query Handler (Feature #13).

Demonstrates the QueryHandler orchestrating the full hybrid retrieval pipeline
with query expansion, symbol boost, and degraded response handling.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from src.query.query_handler import QueryHandler
from src.query.response_builder import ResponseBuilder
from src.query.response_models import QueryResponse
from src.query.rank_fusion import RankFusion
from src.query.reranker import Reranker
from src.query.scored_chunk import ScoredChunk
from src.shared.exceptions import ValidationError


def _make_chunks(n: int, content_type: str = "code") -> list[ScoredChunk]:
    return [
        ScoredChunk(
            chunk_id=f"chunk-{i}",
            content_type=content_type,
            repo_id="my-org/my-app",
            file_path=f"src/file_{i}.py",
            content=f"def example_{i}(): pass",
            score=float(10 - i),
            language="python" if content_type == "code" else None,
            chunk_type="function" if content_type == "code" else None,
            symbol=f"example_{i}" if content_type == "code" else None,
        )
        for i in range(n)
    ]


async def main() -> None:
    # Set up mock retriever (real retriever needs ES/Qdrant)
    retriever = MagicMock()
    retriever.bm25_code_search = AsyncMock(return_value=_make_chunks(5, "code"))
    retriever.vector_code_search = AsyncMock(return_value=_make_chunks(5, "code"))
    retriever.bm25_doc_search = AsyncMock(return_value=_make_chunks(3, "doc"))
    retriever.vector_doc_search = AsyncMock(return_value=_make_chunks(3, "doc"))
    retriever._execute_search = AsyncMock(return_value=[])
    retriever._parse_code_hits = MagicMock(return_value=[])
    retriever._code_index = "code_chunks"

    rank_fusion = RankFusion(k=60)
    reranker = Reranker()  # Falls back to fusion order (no API key)
    response_builder = ResponseBuilder()

    handler = QueryHandler(
        retriever=retriever,
        rank_fusion=rank_fusion,
        reranker=reranker,
        response_builder=response_builder,
    )

    # 1. Normal NL query
    print("--- Normal NL Query ---")
    response = await handler.handle_nl_query(
        "how to authenticate users", "my-org/my-app"
    )
    print(f"Query: {response.query}")
    print(f"Type: {response.query_type}")
    print(f"Code results: {len(response.code_results)}")
    print(f"Doc results: {len(response.doc_results)}")
    print(f"Degraded: {response.degraded}")

    # 2. Query expansion demo
    print("\n--- Query Expansion ---")
    identifiers = handler._extract_identifiers("how does AuthService validate tokens")
    print(f"Identifiers found: {identifiers}")

    identifiers2 = handler._extract_identifiers("check the get_user_name function")
    print(f"Snake case: {identifiers2}")

    identifiers3 = handler._extract_identifiers("how to configure timeout")
    print(f"No identifiers: {identifiers3}")

    # 3. Query type detection (stub)
    print("\n--- Query Type Detection ---")
    print(f"detect_query_type('anything'): {handler.detect_query_type('anything')}")

    # 4. Validation errors
    print("\n--- Validation ---")
    try:
        await handler.handle_nl_query("", "test-repo")
    except ValidationError as e:
        print(f"Empty query: {e}")

    try:
        await handler.handle_nl_query("x" * 501, "test-repo")
    except ValidationError as e:
        print(f"Too long: {e}")

    # 5. Degraded response (simulated timeout)
    print("\n--- Degraded Response ---")
    retriever.bm25_code_search = AsyncMock(side_effect=asyncio.TimeoutError())
    response = await handler.handle_nl_query("test query", "test-repo")
    print(f"Degraded: {response.degraded}")


if __name__ == "__main__":
    asyncio.run(main())
