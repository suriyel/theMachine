"""Retriever — BM25 keyword + vector semantic search."""

from __future__ import annotations

import logging

from elasticsearch import (
    ConnectionError as ESConnectionError,
    NotFoundError,
    TransportError,
)
from grpc import RpcError
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import (
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
)

from src.indexing.embedding_encoder import EmbeddingEncoder
from src.indexing.exceptions import EmbeddingModelError
from src.query.exceptions import RetrievalError
from src.query.scored_chunk import ScoredChunk
from src.shared.clients.elasticsearch import ElasticsearchClient
from src.shared.clients.qdrant import QdrantClientWrapper


logger = logging.getLogger(__name__)


class Retriever:
    """Executes BM25 keyword and vector semantic searches."""

    def __init__(
        self,
        es_client: ElasticsearchClient,
        code_index: str = "code_chunks",
        doc_index: str = "doc_chunks",
        embedding_encoder: EmbeddingEncoder | None = None,
        qdrant_client: QdrantClientWrapper | None = None,
        code_collection: str = "code_embeddings",
        doc_collection: str = "doc_embeddings",
    ) -> None:
        self._es = es_client
        self._code_index = code_index
        self._doc_index = doc_index
        self._embedding_encoder = embedding_encoder
        self._qdrant = qdrant_client
        self._code_collection = code_collection
        self._doc_collection = doc_collection

    # ------------------------------------------------------------------
    # BM25 search (Feature #8)
    # ------------------------------------------------------------------

    async def bm25_code_search(
        self,
        query: str,
        repo_id: str | None = None,
        languages: list[str] | None = None,
        top_k: int = 200,
        branch: str | None = None,
    ) -> list[ScoredChunk]:
        """Execute BM25 keyword search on code_chunks index.

        Returns up to top_k ScoredChunks sorted by BM25 score descending.

        Raises:
            ValueError: If query is empty or whitespace-only.
            RetrievalError: If Elasticsearch is unreachable or query fails.
        """
        if not query or not query.strip():
            raise ValueError("query must not be empty")

        body = self._build_code_query(query, repo_id, languages, top_k, branch)
        hits = await self._execute_search(self._code_index, body, top_k)
        return self._parse_code_hits(hits)

    async def bm25_doc_search(
        self,
        query: str,
        repo_id: str | None = None,
        top_k: int = 200,
        branch: str | None = None,
    ) -> list[ScoredChunk]:
        """Execute BM25 keyword search on doc_chunks index.

        Returns up to top_k ScoredChunks sorted by BM25 score descending.

        Raises:
            ValueError: If query is empty or whitespace-only.
            RetrievalError: If Elasticsearch is unreachable or query fails.
        """
        if not query or not query.strip():
            raise ValueError("query must not be empty")

        body = self._build_doc_query(query, repo_id, top_k, branch)
        hits = await self._execute_search(self._doc_index, body, top_k)
        return self._parse_doc_hits(hits)

    # ------------------------------------------------------------------
    # Vector search (Feature #9)
    # ------------------------------------------------------------------

    async def vector_code_search(
        self,
        query: str,
        repo_id: str | None = None,
        languages: list[str] | None = None,
        top_k: int = 200,
        branch: str | None = None,
    ) -> list[ScoredChunk]:
        """Execute vector similarity search on code_embeddings Qdrant collection.

        Encodes the query via EmbeddingEncoder, then searches Qdrant for top_k
        nearest neighbors filtered by repo_id, languages, and/or branch.

        Raises:
            ValueError: If query is empty or whitespace-only.
            RetrievalError: If embedding or Qdrant search fails.
        """
        if not query or not query.strip():
            raise ValueError("query must not be empty")

        query_vector = self._encode_query(query)
        qfilter = self._build_qdrant_filter(repo_id, languages, branch)
        points = await self._execute_qdrant_search(
            self._code_collection, query_vector, qfilter, top_k
        )
        return self._parse_qdrant_code_hits(points)

    async def vector_doc_search(
        self,
        query: str,
        repo_id: str | None = None,
        top_k: int = 200,
        branch: str | None = None,
    ) -> list[ScoredChunk]:
        """Execute vector similarity search on doc_embeddings Qdrant collection.

        Raises:
            ValueError: If query is empty or whitespace-only.
            RetrievalError: If embedding or Qdrant search fails.
        """
        if not query or not query.strip():
            raise ValueError("query must not be empty")

        query_vector = self._encode_query(query)
        qfilter = self._build_qdrant_filter(repo_id, None, branch)
        points = await self._execute_qdrant_search(
            self._doc_collection, query_vector, qfilter, top_k
        )
        return self._parse_qdrant_doc_hits(points)

    # ------------------------------------------------------------------
    # ES internal helpers
    # ------------------------------------------------------------------

    def _build_code_query(
        self,
        query: str,
        repo_id: str | None,
        languages: list[str] | None,
        top_k: int,
        branch: str | None = None,
    ) -> dict:
        """Build ES query DSL for code_chunks multi-match search."""
        must_clause = {
            "multi_match": {
                "query": query,
                "fields": ["content", "symbol^2", "signature", "doc_comment"],
                "type": "best_fields",
            }
        }

        filter_clauses: list[dict] = []
        if repo_id is not None:
            filter_clauses.append({"term": {"repo_id": repo_id}})
        if languages and len(languages) > 0:
            filter_clauses.append({"terms": {"language": languages}})
        if branch is not None:
            filter_clauses.append({"term": {"branch": branch}})

        bool_clause: dict = {"must": [must_clause]}
        if filter_clauses:
            bool_clause["filter"] = filter_clauses

        return {"query": {"bool": bool_clause}}

    def _build_doc_query(
        self, query: str, repo_id: str | None, top_k: int, branch: str | None = None
    ) -> dict:
        """Build ES query DSL for doc_chunks match search."""
        bool_clause: dict = {"must": [{"match": {"content": query}}]}
        filter_clauses: list[dict] = []
        if repo_id is not None:
            filter_clauses.append({"term": {"repo_id": repo_id}})
        if branch is not None:
            filter_clauses.append({"term": {"branch": branch}})
        if filter_clauses:
            bool_clause["filter"] = filter_clauses
        return {"query": {"bool": bool_clause}}

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
                    branch=src.get("branch"),
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
                    branch=src.get("branch"),
                )
            )
        return result

    # ------------------------------------------------------------------
    # Qdrant internal helpers
    # ------------------------------------------------------------------

    def _encode_query(self, query: str) -> list[float]:
        """Encode query string to a dense vector via EmbeddingEncoder."""
        try:
            vector = self._embedding_encoder.encode_query(query)
            return vector.tolist()
        except EmbeddingModelError as exc:
            raise RetrievalError(f"Embedding failed: {exc}") from exc

    def _build_qdrant_filter(
        self,
        repo_id: str | None,
        languages: list[str] | None,
        branch: str | None = None,
    ) -> Filter | None:
        """Build a Qdrant filter for optional repo_id, language, and branch restriction."""
        conditions: list[FieldCondition] = []
        if repo_id is not None:
            conditions.append(
                FieldCondition(key="repo_id", match=MatchValue(value=repo_id))
            )
        if languages and len(languages) > 0:
            conditions.append(
                FieldCondition(key="language", match=MatchAny(any=languages))
            )
        if branch is not None:
            conditions.append(
                FieldCondition(key="branch", match=MatchValue(value=branch))
            )
        if not conditions:
            return None
        return Filter(must=conditions)

    async def _execute_qdrant_search(
        self,
        collection: str,
        query_vector: list[float],
        qfilter: Filter | None,
        limit: int,
    ) -> list:
        """Execute Qdrant vector search, wrapping errors into RetrievalError."""
        try:
            response = await self._qdrant._client.query_points(
                collection_name=collection,
                query=query_vector,
                query_filter=qfilter,
                limit=limit,
                with_payload=True,
            )
            return response.points
        except (UnexpectedResponse, RpcError, ConnectionError, OSError) as exc:
            logger.warning("Qdrant unreachable, caller should fall back to BM25-only: %s", exc)
            raise RetrievalError(f"Qdrant search failed: {exc}") from exc

    def _parse_qdrant_code_hits(self, points: list) -> list[ScoredChunk]:
        """Parse Qdrant ScoredPoints from code_embeddings into ScoredChunks."""
        result: list[ScoredChunk] = []
        for pt in points:
            p = pt.payload
            result.append(
                ScoredChunk(
                    chunk_id=str(pt.id),
                    content_type="code",
                    repo_id=p["repo_id"],
                    file_path=p["file_path"],
                    content=p["content"],
                    score=pt.score,
                    language=p.get("language"),
                    chunk_type=p.get("chunk_type"),
                    symbol=p.get("symbol"),
                    signature=p.get("signature"),
                    doc_comment=p.get("doc_comment"),
                    line_start=p.get("line_start"),
                    line_end=p.get("line_end"),
                    parent_class=p.get("parent_class"),
                    branch=p.get("branch"),
                )
            )
        return result

    def _parse_qdrant_doc_hits(self, points: list) -> list[ScoredChunk]:
        """Parse Qdrant ScoredPoints from doc_embeddings into ScoredChunks."""
        result: list[ScoredChunk] = []
        for pt in points:
            p = pt.payload
            result.append(
                ScoredChunk(
                    chunk_id=str(pt.id),
                    content_type="doc",
                    repo_id=p["repo_id"],
                    file_path=p["file_path"],
                    content=p["content"],
                    score=pt.score,
                    breadcrumb=p.get("breadcrumb"),
                    heading_level=p.get("heading_level"),
                    branch=p.get("branch"),
                )
            )
        return result
