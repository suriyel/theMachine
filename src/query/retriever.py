"""Retriever — BM25 keyword search against Elasticsearch indices."""

from __future__ import annotations

from elasticsearch import (
    ConnectionError as ESConnectionError,
    NotFoundError,
    TransportError,
)

from src.query.exceptions import RetrievalError
from src.query.scored_chunk import ScoredChunk
from src.shared.clients.elasticsearch import ElasticsearchClient


class Retriever:
    """Executes BM25 keyword searches against Elasticsearch code and doc indices."""

    def __init__(
        self,
        es_client: ElasticsearchClient,
        code_index: str = "code_chunks",
        doc_index: str = "doc_chunks",
    ) -> None:
        self._es = es_client
        self._code_index = code_index
        self._doc_index = doc_index

    async def bm25_code_search(
        self,
        query: str,
        repo_id: str,
        languages: list[str] | None = None,
        top_k: int = 200,
    ) -> list[ScoredChunk]:
        """Execute BM25 keyword search on code_chunks index.

        Returns up to top_k ScoredChunks sorted by BM25 score descending.

        Raises:
            ValueError: If query is empty or whitespace-only.
            RetrievalError: If Elasticsearch is unreachable or query fails.
        """
        if not query or not query.strip():
            raise ValueError("query must not be empty")

        body = self._build_code_query(query, repo_id, languages, top_k)
        hits = await self._execute_search(self._code_index, body, top_k)
        return self._parse_code_hits(hits)

    async def bm25_doc_search(
        self,
        query: str,
        repo_id: str,
        top_k: int = 200,
    ) -> list[ScoredChunk]:
        """Execute BM25 keyword search on doc_chunks index.

        Returns up to top_k ScoredChunks sorted by BM25 score descending.

        Raises:
            ValueError: If query is empty or whitespace-only.
            RetrievalError: If Elasticsearch is unreachable or query fails.
        """
        if not query or not query.strip():
            raise ValueError("query must not be empty")

        body = self._build_doc_query(query, repo_id, top_k)
        hits = await self._execute_search(self._doc_index, body, top_k)
        return self._parse_doc_hits(hits)

    def _build_code_query(
        self,
        query: str,
        repo_id: str,
        languages: list[str] | None,
        top_k: int,
    ) -> dict:
        """Build ES query DSL for code_chunks multi-match search."""
        must_clause = {
            "multi_match": {
                "query": query,
                "fields": ["content", "symbol^2", "signature", "doc_comment"],
                "type": "best_fields",
            }
        }

        filter_clauses: list[dict] = [{"term": {"repo_id": repo_id}}]
        if languages and len(languages) > 0:
            filter_clauses.append({"terms": {"language": languages}})

        return {
            "query": {
                "bool": {
                    "must": [must_clause],
                    "filter": filter_clauses,
                }
            }
        }

    def _build_doc_query(self, query: str, repo_id: str, top_k: int) -> dict:
        """Build ES query DSL for doc_chunks match search."""
        return {
            "query": {
                "bool": {
                    "must": [{"match": {"content": query}}],
                    "filter": [{"term": {"repo_id": repo_id}}],
                }
            }
        }

    async def _execute_search(
        self, index: str, body: dict, size: int
    ) -> list[dict]:
        """Execute ES search and return raw hits, wrapping errors."""
        try:
            response = await self._es._client.search(
                index=index, body=body, size=size
            )
            return response["hits"]["hits"]
        except (ESConnectionError, TransportError, NotFoundError) as exc:
            raise RetrievalError(f"Elasticsearch search failed: {exc}") from exc

    def _parse_code_hits(self, hits: list[dict]) -> list[ScoredChunk]:
        """Parse ES code_chunks hits into ScoredChunk objects."""
        result: list[ScoredChunk] = []
        for hit in hits:
            src = hit["_source"]
            result.append(
                ScoredChunk(
                    chunk_id=hit["_id"],
                    content_type="code",
                    repo_id=src["repo_id"],
                    file_path=src["file_path"],
                    content=src["content"],
                    score=hit["_score"],
                    language=src.get("language"),
                    chunk_type=src.get("chunk_type"),
                    symbol=src.get("symbol"),
                    signature=src.get("signature"),
                    doc_comment=src.get("doc_comment"),
                    line_start=src.get("line_start"),
                    line_end=src.get("line_end"),
                    parent_class=src.get("parent_class"),
                )
            )
        return result

    def _parse_doc_hits(self, hits: list[dict]) -> list[ScoredChunk]:
        """Parse ES doc_chunks hits into ScoredChunk objects."""
        result: list[ScoredChunk] = []
        for hit in hits:
            src = hit["_source"]
            result.append(
                ScoredChunk(
                    chunk_id=hit["_id"],
                    content_type="doc",
                    repo_id=src["repo_id"],
                    file_path=src["file_path"],
                    content=src["content"],
                    score=hit["_score"],
                    breadcrumb=src.get("breadcrumb"),
                    heading_level=src.get("heading_level"),
                )
            )
        return result
