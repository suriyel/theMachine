"""Example: Query Handler - Natural Language Query (Feature #13).

This example demonstrates how to use the QueryHandler to process natural language queries.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from src.query.handler import QueryHandler
from src.query.retriever import Candidate
from src.query.api.v1.endpoints.query import QueryRequest, ContextResult


async def main():
    """Demonstrate QueryHandler with mocked dependencies."""

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
            file_path="src/web/client/WebClient.java",
            symbol="WebClient",
            content="public class WebClient extends RestClient {...}",
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
        Candidate(
            chunk_id="sem_1",
            repo_name="spring-framework",
            file_path="src/web/client/WebClient.java",
            symbol="WebClient",
            content="public class WebClient extends RestClient {...}",
            score=0.85,
            language="Java"
        ),
    ])

    mock_reranker = MagicMock()
    mock_reranker.rerank = MagicMock(return_value=[
        Candidate(
            chunk_id="sem_1",
            repo_name="spring-framework",
            file_path="src/web/client/WebClient.java",
            symbol="WebClient",
            content="public class WebClient extends RestClient {...}",
            score=0.95,  # Reranked score
            language="Java"
        ),
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

    mock_response_builder = MagicMock()
    mock_response_builder._top_k = 3
    mock_response_builder.build = MagicMock(return_value=[
        ContextResult(
            repository='spring-framework',
            file_path='src/web/client/WebClient.java',
            symbol='WebClient',
            score=0.95,
            content='public class WebClient extends RestClient {...}'
        ),
        ContextResult(
            repository='spring-framework',
            file_path='src/web/client/RestTemplate.java',
            symbol='RestTemplate',
            score=0.9,
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

    # Create a natural language query request
    request = QueryRequest(
        query="how to use spring WebClient timeout",
        query_type="natural_language",
        top_k=3
    )

    # Handle the query
    print(f"Processing query: {request.query}")
    response = await handler.handle(request)

    # Display results
    print(f"\nQuery completed in {response.query_time_ms:.2f}ms")
    print(f"Returned {len(response.results)} results:\n")

    for i, result in enumerate(response.results, 1):
        print(f"Result {i}:")
        print(f"  Repository: {result.repository}")
        print(f"  File: {result.file_path}")
        print(f"  Symbol: {result.symbol}")
        print(f"  Score: {result.score:.2f}")
        print(f"  Content: {result.content[:50]}...")
        print()


if __name__ == "__main__":
    asyncio.run(main())
