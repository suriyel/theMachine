"""Example 13: Semantic Retrieval (Vector Search) — Feature #9

Demonstrates how the Retriever performs vector-based semantic search
using EmbeddingEncoder and Qdrant. This example uses mocked dependencies
to show the API without requiring running services.
"""

from unittest.mock import AsyncMock, MagicMock

import asyncio
import numpy as np
from qdrant_client.http.models import QueryResponse, ScoredPoint

from src.query.retriever import Retriever
from src.query.scored_chunk import ScoredChunk
from src.shared.clients.elasticsearch import ElasticsearchClient


def make_mock_encoder():
    """Create a mock EmbeddingEncoder returning a fixed 1024-dim vector."""
    encoder = MagicMock()
    encoder.encode_query = MagicMock(
        return_value=np.random.rand(1024).astype(np.float32)
    )
    return encoder


def make_mock_qdrant(points):
    """Create a mock QdrantClientWrapper returning pre-defined points."""
    wrapper = MagicMock()
    inner = AsyncMock()
    inner.query_points = AsyncMock(
        return_value=QueryResponse(points=points)
    )
    wrapper._client = inner
    return wrapper


async def main():
    # Simulate Qdrant returning code chunks about HTTP timeout configuration
    points = [
        ScoredPoint(
            id="chunk-001", version=1, score=0.92,
            payload={
                "repo_id": "repo-flask",
                "file_path": "src/http_client.py",
                "content": "class HttpClient:\n    def configure_timeout(self, timeout_ms: int):\n        self._timeout = timeout_ms / 1000",
                "language": "python",
                "chunk_type": "method",
                "symbol": "HttpClient.configure_timeout",
                "signature": "def configure_timeout(self, timeout_ms: int)",
                "doc_comment": "Set the HTTP request timeout in milliseconds.",
                "line_start": 15,
                "line_end": 17,
                "parent_class": "HttpClient",
            },
        ),
        ScoredPoint(
            id="chunk-002", version=1, score=0.85,
            payload={
                "repo_id": "repo-flask",
                "file_path": "src/web_client.py",
                "content": "def set_read_timeout(self, seconds: float):\n    self.session.timeout = aiohttp.ClientTimeout(total=seconds)",
                "language": "python",
                "chunk_type": "method",
                "symbol": "WebClient.set_read_timeout",
                "signature": "def set_read_timeout(self, seconds: float)",
                "doc_comment": None,
                "line_start": 42,
                "line_end": 43,
                "parent_class": "WebClient",
            },
        ),
    ]

    # Build retriever with mocked dependencies
    es_client = MagicMock(spec=ElasticsearchClient)
    encoder = make_mock_encoder()
    qdrant = make_mock_qdrant(points)

    retriever = Retriever(
        es_client=es_client,
        embedding_encoder=encoder,
        qdrant_client=qdrant,
    )

    # Perform semantic vector search
    print("=== Semantic Vector Search ===")
    print("Query: 'how to configure http client timeout'")
    print()

    results = await retriever.vector_code_search(
        query="how to configure http client timeout",
        repo_id="repo-flask",
        languages=["python"],
        top_k=10,
    )

    for i, chunk in enumerate(results, 1):
        print(f"Result #{i}:")
        print(f"  Score:    {chunk.score:.4f} (cosine similarity)")
        print(f"  Symbol:   {chunk.symbol}")
        print(f"  File:     {chunk.file_path}:{chunk.line_start}-{chunk.line_end}")
        print(f"  Language: {chunk.language}")
        print(f"  Type:     {chunk.content_type}")
        print(f"  Content:  {chunk.content[:80]}...")
        print()

    print(f"Total results: {len(results)}")
    print()

    # Demonstrate doc search
    doc_points = [
        ScoredPoint(
            id="doc-001", version=1, score=0.78,
            payload={
                "repo_id": "repo-flask",
                "file_path": "docs/configuration.md",
                "content": "## Timeout Configuration\n\nSet timeout via `HttpClient.configure_timeout(ms)`. Default: 30000ms.",
                "breadcrumb": "Configuration > Timeout",
                "heading_level": 2,
            },
        ),
    ]
    qdrant_doc = make_mock_qdrant(doc_points)
    retriever_doc = Retriever(
        es_client=es_client,
        embedding_encoder=encoder,
        qdrant_client=qdrant_doc,
    )

    print("=== Doc Vector Search ===")
    doc_results = await retriever_doc.vector_doc_search(
        query="timeout configuration", repo_id="repo-flask"
    )
    for chunk in doc_results:
        print(f"  [{chunk.content_type}] {chunk.file_path} (score={chunk.score:.2f})")
        print(f"  Breadcrumb: {chunk.breadcrumb}")
        print(f"  Content: {chunk.content[:80]}...")
    print()

    # Demonstrate branch-filtered vector search (Wave 5)
    branch_points = [
        ScoredPoint(
            id="chunk-003", version=1, score=0.90,
            payload={
                "repo_id": "repo-flask",
                "file_path": "src/http_client.py",
                "content": "def configure_timeout(self, timeout_ms: int, retry: bool = True):\n    ...",
                "language": "python",
                "chunk_type": "method",
                "symbol": "HttpClient.configure_timeout",
                "signature": "def configure_timeout(self, timeout_ms: int, retry: bool = True)",
                "doc_comment": "Set timeout with optional retry (feature branch).",
                "line_start": 15,
                "line_end": 18,
                "parent_class": "HttpClient",
                "branch": "feature/retry-support",
            },
        ),
    ]
    qdrant_branch = make_mock_qdrant(branch_points)
    retriever_branch = Retriever(
        es_client=es_client,
        embedding_encoder=encoder,
        qdrant_client=qdrant_branch,
    )

    print("=== Branch-Filtered Vector Search (Wave 5) ===")
    print("Query: 'configure timeout', Branch: 'feature/retry-support'")
    print()

    branch_results = await retriever_branch.vector_code_search(
        query="configure timeout",
        repo_id="repo-flask",
        branch="feature/retry-support",
    )

    for chunk in branch_results:
        print(f"  Score:  {chunk.score:.4f}")
        print(f"  Symbol: {chunk.symbol}")
        print(f"  Branch: {chunk.branch}")
        print(f"  File:   {chunk.file_path}:{chunk.line_start}-{chunk.line_end}")
        print(f"  Content: {chunk.content[:80]}...")
    print()

    print(f"Branch filter narrows results to branch 'feature/retry-support' only.")


if __name__ == "__main__":
    asyncio.run(main())
