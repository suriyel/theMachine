"""Example 12: Keyword Retrieval (BM25) — Feature #8.

Demonstrates BM25 keyword search against Elasticsearch code_chunks
and doc_chunks indices using the Retriever class.

Usage:
    python examples/12-keyword-retrieval.py

Prerequisites:
    - Elasticsearch running at ELASTICSEARCH_URL (default http://localhost:9200)
    - Code chunks indexed in code_chunks index
"""

from __future__ import annotations

import asyncio
import os

from src.query.exceptions import RetrievalError
from src.query.retriever import Retriever
from src.shared.clients.elasticsearch import ElasticsearchClient


async def main() -> None:
    es_url = os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200")
    es_client = ElasticsearchClient(es_url)
    await es_client.connect()

    try:
        retriever = Retriever(es_client)

        # --- BM25 code search ---
        print("=== BM25 Code Search ===")
        try:
            results = await retriever.bm25_code_search(
                query="getUserName",
                repo_id="example-repo",
                top_k=5,
            )
            print(f"Found {len(results)} code chunks:")
            for chunk in results:
                print(f"  [{chunk.score:.2f}] {chunk.symbol} in {chunk.file_path}")
        except RetrievalError as e:
            print(f"Search failed (ES may not be running): {e}")

        # --- BM25 code search with language filter ---
        print("\n=== BM25 Code Search (Python only) ===")
        try:
            results = await retriever.bm25_code_search(
                query="parse config",
                repo_id="example-repo",
                languages=["python"],
                top_k=3,
            )
            print(f"Found {len(results)} Python code chunks:")
            for chunk in results:
                print(f"  [{chunk.score:.2f}] {chunk.symbol} ({chunk.language})")
        except RetrievalError as e:
            print(f"Search failed: {e}")

        # --- BM25 doc search ---
        print("\n=== BM25 Doc Search ===")
        try:
            results = await retriever.bm25_doc_search(
                query="timeout configuration",
                repo_id="example-repo",
                top_k=3,
            )
            print(f"Found {len(results)} doc chunks:")
            for chunk in results:
                print(f"  [{chunk.score:.2f}] {chunk.breadcrumb}")
        except RetrievalError as e:
            print(f"Search failed: {e}")

        # --- BM25 code search with branch filter (Wave 5) ---
        print("\n=== BM25 Code Search (branch filter) ===")
        try:
            results = await retriever.bm25_code_search(
                query="getUserName",
                repo_id="example-repo",
                branch="main",
                top_k=5,
            )
            print(f"Found {len(results)} code chunks on branch 'main':")
            for chunk in results:
                print(f"  [{chunk.score:.2f}] {chunk.symbol} (branch={chunk.branch})")
        except RetrievalError as e:
            print(f"Search failed: {e}")

        # --- BM25 doc search with branch filter (Wave 5) ---
        print("\n=== BM25 Doc Search (branch filter) ===")
        try:
            results = await retriever.bm25_doc_search(
                query="timeout configuration",
                repo_id="example-repo",
                branch="main",
                top_k=3,
            )
            print(f"Found {len(results)} doc chunks on branch 'main':")
            for chunk in results:
                print(f"  [{chunk.score:.2f}] {chunk.breadcrumb} (branch={chunk.branch})")
        except RetrievalError as e:
            print(f"Search failed: {e}")

        # --- Empty result handling ---
        print("\n=== Empty Result (no match) ===")
        try:
            results = await retriever.bm25_code_search(
                query="nonexistent_symbol_xyz_999",
                repo_id="example-repo",
            )
            print(f"Results: {results}  (empty list, no error)")
        except RetrievalError as e:
            print(f"Search failed: {e}")

    finally:
        await es_client.close()


if __name__ == "__main__":
    asyncio.run(main())
