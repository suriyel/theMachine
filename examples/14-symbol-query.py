#!/usr/bin/env python3
"""Example: Symbol Query Handler (Feature #14).

Demonstrates:
- detect_query_type() heuristic for symbol vs NL classification
- handle_symbol_query() pipeline: ES term → fuzzy → NL fallback
- Doc BM25 search parallel to code search (design §4.2.5)
- Branch parsing from owner/repo@branch format
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from src.query.query_handler import QueryHandler
from src.query.response_models import QueryResponse
from src.query.scored_chunk import ScoredChunk


def demo_detect_query_type():
    """Show how detect_query_type classifies various queries."""
    handler = QueryHandler(
        retriever=MagicMock(),
        rank_fusion=MagicMock(),
        reranker=MagicMock(),
        response_builder=MagicMock(),
    )

    examples = [
        ("UserService.getById", "dot notation"),
        ("std::vector", "C++ scope"),
        ("Array#map", "Ruby/JS hash"),
        ("getUserName", "camelCase"),
        ("UserService", "PascalCase"),
        ("get_user_name", "snake_case"),
        ("how to handle errors", "natural language"),
        ("hello", "single word"),
    ]

    print("=== detect_query_type ===")
    for query, desc in examples:
        result = handler.detect_query_type(query)
        print(f"  {query:40s} → {result:6s}  ({desc})")


async def demo_handle_symbol_query():
    """Show handle_symbol_query with mocked ES returning term hits."""
    retriever = MagicMock()
    reranker = MagicMock()
    response_builder = MagicMock()

    # Simulate ES returning a term hit
    retriever._code_index = "code_chunks"
    retriever._execute_search = AsyncMock(return_value=[
        {
            "_id": "chunk-1",
            "_score": 8.5,
            "_source": {
                "repo_id": "my-repo",
                "file_path": "src/vector.cpp",
                "content": "template<class T> class vector { ... }",
                "language": "cpp",
                "chunk_type": "class",
                "symbol": "std::vector",
                "signature": "template<class T> class vector",
                "doc_comment": "Dynamic array container",
                "line_start": 1,
                "line_end": 200,
                "parent_class": None,
            },
        }
    ])

    parsed = [ScoredChunk(
        chunk_id="chunk-1", content_type="code", repo_id="my-repo",
        file_path="src/vector.cpp", content="template<class T> class vector { ... }",
        score=8.5, language="cpp", chunk_type="class", symbol="std::vector",
    )]
    retriever._parse_code_hits = MagicMock(return_value=parsed)
    # Doc BM25 search returns related documentation (design §4.2.5)
    retriever.bm25_doc_search = AsyncMock(return_value=[])
    reranker.rerank = MagicMock(return_value=parsed)
    response_builder.build = MagicMock(return_value=QueryResponse(
        query="std::vector", query_type="symbol", repo="my-repo",
    ))

    handler = QueryHandler(
        retriever=retriever,
        rank_fusion=MagicMock(),
        reranker=reranker,
        response_builder=response_builder,
    )

    print("\n=== handle_symbol_query ===")
    result = await handler.handle_symbol_query("std::vector", "my-repo")
    print(f"  Query:      {result.query}")
    print(f"  Query Type: {result.query_type}")
    print(f"  Repo:       {result.repo}")
    print(f"  ES calls:   {retriever._execute_search.call_count} (term hit found, no fuzzy needed)")
    print(f"  Doc search: {retriever.bm25_doc_search.call_count} call(s) (parallel doc BM25)")

    # Demo branch parsing
    print("\n=== Branch parsing ===")
    repo_id, branch = handler._parse_repo("owner/repo@main")
    print(f"  'owner/repo@main' → repo_id='{repo_id}', branch='{branch}'")
    repo_id2, branch2 = handler._parse_repo("owner/repo")
    print(f"  'owner/repo'      → repo_id='{repo_id2}', branch={branch2}")


if __name__ == "__main__":
    demo_detect_query_type()
    asyncio.run(demo_handle_symbol_query())
