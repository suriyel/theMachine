"""Example: Keyword Retrieval (Feature #8)

Demonstrates BM25-based keyword search using Elasticsearch.

This example shows how to use the KeywordRetriever class to search
for code chunks using lexical (keyword) matching.
"""
import asyncio
from elasticsearch import AsyncElasticsearch

from src.query.retriever import KeywordRetriever


async def main():
    """Run keyword retrieval examples."""

    # Connect to Elasticsearch
    es = AsyncElasticsearch(["http://localhost:9200"])

    # Create KeywordRetriever instance
    retriever = KeywordRetriever(es, index_name="code_chunks")

    # Example 1: Basic keyword search
    print("=== Example 1: Basic Keyword Search ===")
    results = await retriever.retrieve("WebClient timeout", {})
    print(f"Query: 'WebClient timeout'")
    print(f"Results: {len(results)}")
    for r in results:
        print(f"  - {r (score: {r.score:.2f})")
        print(f"   .file_path} {r.content[:80]}...")
    print()

    # Example 2: Keyword search with no matches
    print("=== Example 2: No Matches ===")
    results = await retriever.retrieve("xyznonexistent123", {})
    print(f"Query: 'xyznonexistent123'")
    print(f"Results: {len(results)} (empty list)")
    print()

    # Example 3: Keyword search with repo filter
    print("=== Example 3: Repo Filter ===")
    results = await retriever.retrieve("timeout", {"repo_filter": "spring-framework"})
    print(f"Query: 'timeout' with repo_filter='spring-framework'")
    print(f"Results: {len(results)}")
    for r in results:
        print(f"  - {r.repo_name}:{r.file_path}")
    print()

    # Example 4: Keyword search with language filter
    print("=== Example 4: Language Filter ===")
    results = await retriever.retrieve("function", {"language_filter": "python"})
    print(f"Query: 'function' with language_filter='python'")
    print(f"Results: {len(results)}")
    for r in results:
        print(f"  - {r.language}:{r.file_path}")
    print()

    # Example 5: Combined filters
    print("=== Example 5: Combined Filters ===")
    results = await retriever.retrieve(
        "class",
        {"repo_filter": "myrepo", "language_filter": "python"}
    )
    print(f"Query: 'class' with repo_filter='myrepo' and language_filter='python'")
    print(f"Results: {len(results)}")
    print()

    # Clean up
    await es.close()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
