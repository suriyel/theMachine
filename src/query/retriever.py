"""Query retriever module - Keyword and Semantic retrieval.

This module provides retrieval classes for keyword (BM25) and semantic (vector) search.
"""
from dataclasses import dataclass
from typing import Any


@dataclass
class Candidate:
    """A candidate chunk retrieved from search.

    Attributes:
        chunk_id: Unique identifier for the chunk
        repo_name: Name of the repository
        file_path: Path to the source file
        symbol: Symbol name if applicable (function, class, etc.)
        content: The actual code content
        score: Relevance score from search
        language: Programming language of the chunk
    """
    chunk_id: str
    repo_name: str
    file_path: str
    symbol: str | None
    content: str
    score: float
    language: str | None = None


class KeywordRetriever:
    """Keyword retrieval using BM25 via Elasticsearch.

    Performs lexical search using Elasticsearch's multi_match query with BM25.
    """

    def __init__(self, es_client: Any, index_name: str = "code_chunks"):
        """Initialize KeywordRetriever.

        Args:
            es_client: AsyncElasticsearch client
            index_name: Name of the Elasticsearch index
        """
        self._es = es_client
        self._index_name = index_name

    async def retrieve(self, query: str, filters: dict) -> list[Candidate]:
        """Retrieve candidate chunks using keyword search.

        Args:
            query: Search query text
            filters: Dictionary with optional filters:
                - repo_filter: Filter by repository name
                - language_filter: Filter by programming language

        Returns:
            List of Candidate objects

        Raises:
            ValueError: If query is empty or whitespace-only
        """
        # Validate query
        if not query or not query.strip():
            raise ValueError("Query text cannot be empty")

        # Build search query
        must_clauses = [
            {
                "multi_match": {
                    "query": query,
                    "fields": ["content^2", "symbol^1.5", "file_path"],
                    "type": "best_fields"
                }
            }
        ]

        # Build filter clauses
        filter_clauses = []
        if filters.get("repo_filter"):
            filter_clauses.append({
                "term": {"repo_name": filters["repo_filter"]}
            })
        if filters.get("language_filter"):
            filter_clauses.append({
                "term": {"language": filters["language_filter"]}
            })

        # Build final query
        body = {
            "query": {
                "bool": {
                    "must": must_clauses
                }
            },
            "size": 100  # Get top 100 candidates
        }

        if filter_clauses:
            body["query"]["bool"]["filter"] = filter_clauses

        # Execute search
        response = await self._es.search(
            index=self._index_name,
            body=body
        )

        # Parse results
        candidates = []
        for hit in response.get("hits", {}).get("hits", []):
            source = hit["_source"]
            candidates.append(Candidate(
                chunk_id=hit["_id"],
                repo_name=source.get("repo_name", ""),
                file_path=source.get("file_path", ""),
                symbol=source.get("symbol"),
                content=source.get("content", ""),
                score=hit.get("_score", 0.0),
                language=source.get("language")
            ))

        return candidates
