"""Example: Semantic Retrieval (Feature #9)

Demonstrates vector-based semantic search using Qdrant.

This example shows how to use the SemanticRetriever class to search
for code chunks using semantic (embedding-based) similarity search.
"""
import asyncio
from qdrant_client import AsyncQdrantClient

from src.query.retriever import SemanticRetriever
from src.indexing.embedding_encoder import EmbeddingEncoder


async def main():
    """Run semantic retrieval examples."""

    # Connect to Qdrant
    qdrant = AsyncQdrantClient(url="http://localhost:6333")

    # Create EmbeddingEncoder (loads the model)
    encoder = EmbeddingEncoder()

    # Create SemanticRetriever with default threshold (0.6)
    retriever = SemanticRetriever(qdrant, encoder, threshold=0.6)

    # Example 1: Basic semantic search
    print("=== Example 1: Basic Semantic Search ===")
    results = await retriever.retrieve(
        "how to configure spring http client timeout",
        {}
    )
    print(f"Query: 'how to configure spring http client timeout'")
    print(f"Results: {len(results)}")
    for r in results:
        print(f"  - {r.file_path} (score: {r.score:.2f})")
        print(f"    {r.content[:80]}...")
    print()

    # Example 2: Semantic search with no matches above threshold
    print("=== Example 2: No Matches Above Threshold ===")
    results = await retriever.retrieve("xyznonexistentquery12345xyz", {})
    print(f"Query: 'xyznonexistentquery12345xyz'")
    print(f"Results: {len(results)} (empty - nothing above threshold)")
    print()

    # Example 3: Higher threshold (stricter filtering)
    print("=== Example 3: Higher Threshold ===")
    strict_retriever = SemanticRetriever(qdrant, encoder, threshold=0.8)
    results = await strict_retriever.retrieve("timeout configuration", {})
    print(f"Query: 'timeout configuration' with threshold=0.8")
    print(f"Results: {len(results)} (only highly similar results)")
    for r in results:
        print(f"  - {r.file_path} (score: {r.score:.2f})")
    print()

    # Example 4: Semantic search with repo filter
    print("=== Example 4: Repo Filter ===")
    results = await retriever.retrieve(
        "timeout",
        {"repo_filter": "spring-framework"}
    )
    print(f"Query: 'timeout' with repo_filter='spring-framework'")
    print(f"Results: {len(results)}")
    for r in results:
        print(f"  - {r.repo_name}:{r.file_path}")
    print()

    # Example 5: Semantic search with language filter
    print("=== Example 5: Language Filter ===")
    results = await retriever.retrieve(
        "function",
        {"language_filter": "python"}
    )
    print(f"Query: 'function' with language_filter='python'")
    print(f"Results: {len(results)}")
    for r in results:
        print(f"  - {r.language}:{r.file_path}")
    print()

    # Example 6: Combined filters
    print("=== Example 6: Combined Filters ===")
    results = await retriever.retrieve(
        "class definition",
        {"repo_filter": "myrepo", "language_filter": "java"}
    )
    print(f"Query: 'class definition' with repo_filter='myrepo' and language_filter='java'")
    print(f"Results: {len(results)}")
    print()

    # Clean up
    await qdrant.close()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
