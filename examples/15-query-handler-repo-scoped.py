"""Example: Query Handler - Repository Scoped Query (Feature #15).

This example demonstrates how to use the QueryHandler with repository filtering.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from src.query.handler import QueryHandler
from src.query.retriever import Candidate
from src.query.api.v1.endpoints.query import QueryRequest, ContextResult


async def main():
    """Demonstrate QueryHandler with repository-scoped queries using mocked dependencies."""

    # Create mock dependencies (in production, these would be real implementations)
    mock_keyword_retriever = AsyncMock()
    mock_keyword_retriever.retrieve = AsyncMock(return_value=[
        Candidate(
            chunk_id="kw_1",
            repo_name="spring-framework",
            file_path="src/web/client/RestTemplate.java",
            symbol="RestTemplate",
            content="public class RestTemplate extends HttpAccessor {...}",
            score=0.9,
            language="Java"
        ),
    ])

    mock_semantic_retriever = AsyncMock()
    mock_semantic_retriever.retrieve = AsyncMock(return_value=[
        Candidate(
            chunk_id="sem_1",
            repo_name="spring-framework",
            file_path="src/web/client/RestTemplate.java",
            symbol="RestTemplate",
            content="public class RestTemplate extends HttpAccessor {...}",
            score=0.85,
            language="Java"
        ),
    ])

    mock_rank_fusion = MagicMock()
    mock_rank_fusion.fuse = MagicMock(return_value=[
        Candidate(
            chunk_id="kw_1",
            repo_name="spring-framework",
            file_path="src/web/client/RestTemplate.java",
            symbol="RestTemplate",
            content="public class RestTemplate extends HttpAccessor {...}",
            score=0.9,
            language="Java"
        ),
    ])

    mock_reranker = MagicMock()
    mock_reranker.rerank = MagicMock(return_value=[
        Candidate(
            chunk_id="kw_1",
            repo_name="spring-framework",
            file_path="src/web/client/RestTemplate.java",
            symbol="RestTemplate",
            content="public class RestTemplate extends HttpAccessor {...}",
            score=0.95,
            language="Java"
        ),
    ])

    mock_response_builder = MagicMock()
    mock_response_builder._top_k = 3
    mock_response_builder.build = MagicMock(return_value=[
        ContextResult(
            repository='spring-framework',
            file_path='src/web/client/RestTemplate.java',
            symbol='RestTemplate',
            score=0.95,
            content='public class RestTemplate extends HttpAccessor {...}'
        ),
    ])

    # Create QueryHandler
    handler = QueryHandler(
        keyword_retriever=mock_keyword_retriever,
        semantic_retriever=mock_semantic_retriever,
        rank_fusion=mock_rank_fusion,
        reranker=mock_reranker,
        response_builder=mock_response_builder,
    )

    # Example 1: Query with repository filter
    print("=== Example 1: Repository-Scoped Query ===\n")
    request = QueryRequest(
        query="timeout",
        query_type="natural_language",
        repo="spring-framework",  # Filter to specific repository
        top_k=3
    )

    print(f"Processing query: '{request.query}'")
    print(f"Filtering to repository: {request.repo}")
    response = await handler.handle(request)

    print(f"\nQuery completed in {response.query_time_ms:.2f}ms")
    print(f"Returned {len(response.results)} results:\n")

    for i, result in enumerate(response.results, 1):
        print(f"Result {i}:")
        print(f"  Repository: {result.repository}")
        print(f"  File: {result.file_path}")
        print(f"  Symbol: {result.symbol}")
        print(f"  Score: {result.score:.2f}")
        print()

    # Example 2: Query with both repo and language filter
    print("\n=== Example 2: Repository + Language Filter ===\n")
    request2 = QueryRequest(
        query="WebClient configuration",
        query_type="natural_language",
        repo="spring-framework",
        language="Java",
        top_k=5
    )

    print(f"Processing query: '{request2.query}'")
    print(f"Filtering to repository: {request2.repo}, language: {request2.language}")
    response2 = await handler.handle(request2)

    print(f"\nQuery completed in {response2.query_time_ms:.2f}ms")
    print(f"Returned {len(response2.results)} results")

    # Example 3: Query for non-existent repository (returns empty, no error)
    print("\n=== Example 3: Non-Existent Repository ===\n")

    # Configure mocks to return empty for non-existent repo
    mock_keyword_retriever.retrieve.return_value = []
    mock_semantic_retriever.retrieve.return_value = []
    mock_response_builder.build.return_value = []

    request3 = QueryRequest(
        query="timeout",
        query_type="natural_language",
        repo="non-existent-repo-12345",
        top_k=3
    )

    print(f"Processing query: '{request3.query}'")
    print(f"Filtering to repository: {request3.repo}")
    response3 = await handler.handle(request3)

    print(f"\nQuery completed in {response3.query_time_ms:.2f}ms")
    print(f"Returned {len(response3.results)} results (empty, no error)")


if __name__ == "__main__":
    asyncio.run(main())
