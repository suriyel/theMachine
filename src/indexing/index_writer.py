"""IndexWriter — writes chunks and embeddings to Elasticsearch and Qdrant."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, Callable, Coroutine

import numpy as np
from qdrant_client.models import PointStruct

from src.indexing.chunker import CodeChunk
from src.indexing.doc_chunker import DocChunk
from src.indexing.exceptions import IndexWriteError
from src.indexing.rule_extractor import RuleChunk
from src.shared.clients.elasticsearch import ElasticsearchClient
from src.shared.clients.qdrant import QdrantClientWrapper


class IndexWriter:
    """Writes chunks + embeddings to Elasticsearch and Qdrant indices."""

    def __init__(
        self,
        es_client: ElasticsearchClient,
        qdrant_client: QdrantClientWrapper,
    ) -> None:
        self._es = es_client
        self._qdrant = qdrant_client

    async def write_code_chunks(
        self,
        chunks: list[CodeChunk],
        embeddings: list[np.ndarray],
        repo_id: str,
        *,
        es_index: str = "code_chunks",
        qdrant_collection: str = "code_embeddings",
    ) -> None:
        """Write code chunks to ES index and Qdrant collection.

        Args:
            es_index: Elasticsearch index name (default: "code_chunks").
            qdrant_collection: Qdrant collection name (default: "code_embeddings").

        Raises:
            ValueError: If chunks and embeddings have different lengths.
            IndexWriteError: If ES or Qdrant write fails after 3 retries.
        """
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have same length")
        if len(chunks) == 0:
            return

        # Write to Elasticsearch
        operations: list[Any] = []
        for chunk in chunks:
            operations.append({"index": {"_index": es_index, "_id": chunk.chunk_id}})
            operations.append({
                "repo_id": repo_id,
                "file_path": chunk.file_path,
                "language": chunk.language,
                "chunk_type": chunk.chunk_type,
                "symbol": chunk.symbol,
                "signature": chunk.signature,
                "doc_comment": chunk.doc_comment,
                "content": chunk.content,
                "line_start": chunk.line_start,
                "line_end": chunk.line_end,
                "parent_class": chunk.parent_class,
                "branch": chunk.branch,
            })
        await self._retry_write(
            lambda: self._es._client.bulk(operations=operations),
            f"ES {es_index}",
        )

        # Write to Qdrant (use UUID5 from chunk_id string — Qdrant requires UUID or uint)
        _NS = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        points = [
            PointStruct(
                id=str(uuid.uuid5(_NS, chunk.chunk_id)),
                vector=embedding.tolist(),
                payload={
                    "repo_id": repo_id,
                    "chunk_id": chunk.chunk_id,
                    "file_path": chunk.file_path,
                    "content": chunk.content,
                    "language": chunk.language,
                    "chunk_type": chunk.chunk_type,
                    "symbol": chunk.symbol,
                    "signature": chunk.signature,
                    "doc_comment": chunk.doc_comment,
                    "line_start": chunk.line_start,
                    "line_end": chunk.line_end,
                    "parent_class": chunk.parent_class,
                    "branch": chunk.branch,
                },
            )
            for chunk, embedding in zip(chunks, embeddings)
        ]
        await self._batch_qdrant_upsert(qdrant_collection, points)

    async def write_doc_chunks(
        self,
        chunks: list[DocChunk],
        embeddings: list[np.ndarray],
        repo_id: str,
    ) -> None:
        """Write doc chunks to ES doc_chunks index and Qdrant doc_embeddings collection.

        Raises:
            ValueError: If chunks and embeddings have different lengths.
            IndexWriteError: If ES or Qdrant write fails after 3 retries.
        """
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have same length")
        if len(chunks) == 0:
            return

        operations: list[Any] = []
        for chunk in chunks:
            operations.append({"index": {"_index": "doc_chunks", "_id": chunk.chunk_id}})
            operations.append({
                "repo_id": repo_id,
                "file_path": chunk.file_path,
                "breadcrumb": chunk.breadcrumb,
                "content": chunk.content,
                "heading_level": chunk.heading_level,
            })
        await self._retry_write(
            lambda: self._es._client.bulk(operations=operations),
            "ES doc_chunks",
        )

        _NS = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        points = [
            PointStruct(
                id=str(uuid.uuid5(_NS, chunk.chunk_id)),
                vector=embedding.tolist(),
                payload={
                    "repo_id": repo_id,
                    "chunk_id": chunk.chunk_id,
                    "file_path": chunk.file_path,
                    "content": chunk.content,
                    "breadcrumb": chunk.breadcrumb,
                    "heading_level": chunk.heading_level,
                },
            )
            for chunk, embedding in zip(chunks, embeddings)
        ]
        await self._batch_qdrant_upsert("doc_embeddings", points)

    async def write_rule_chunks(
        self, chunks: list[RuleChunk], repo_id: str
    ) -> None:
        """Write rule chunks to ES rule_chunks index only (no Qdrant per design).

        Raises:
            IndexWriteError: If ES write fails after 3 retries.
        """
        if len(chunks) == 0:
            return

        operations: list[Any] = []
        for chunk in chunks:
            operations.append({"index": {"_index": "rule_chunks", "_id": chunk.chunk_id}})
            operations.append({
                "repo_id": repo_id,
                "file_path": chunk.file_path,
                "rule_type": chunk.rule_type,
                "content": chunk.content,
            })
        await self._retry_write(
            lambda: self._es._client.bulk(operations=operations),
            "ES rule_chunks",
        )

    async def delete_repo_index(self, repo_id: str, branch: str) -> None:
        """Delete all chunks for a repo+branch from all ES indices and Qdrant collections.

        code_chunks and code_embeddings have a branch field → filter by repo_id + branch.
        doc_chunks, rule_chunks, and doc_embeddings have no branch field → filter by repo_id only.

        Raises:
            IndexWriteError: If ES or Qdrant delete fails after 3 retries.
        """
        repo_branch_query = {"query": {"bool": {"must": [
            {"term": {"repo_id": repo_id}},
            {"term": {"branch": branch}},
        ]}}}
        repo_only_query = {"query": {"bool": {"must": [
            {"term": {"repo_id": repo_id}},
        ]}}}

        # code_chunks has branch field
        await self._retry_write(
            lambda: self._es._client.delete_by_query(
                index="code_chunks", body=repo_branch_query
            ),
            "ES code_chunks",
        )
        # doc_chunks and rule_chunks have no branch field
        for index in ["doc_chunks", "rule_chunks"]:
            await self._retry_write(
                lambda idx=index: self._es._client.delete_by_query(
                    index=idx, body=repo_only_query
                ),
                f"ES {index}",
            )

        from qdrant_client.models import Filter, FieldCondition, MatchValue

        qdrant_branch_filter = Filter(must=[
            FieldCondition(key="repo_id", match=MatchValue(value=repo_id)),
            FieldCondition(key="branch", match=MatchValue(value=branch)),
        ])
        qdrant_repo_filter = Filter(must=[
            FieldCondition(key="repo_id", match=MatchValue(value=repo_id)),
        ])
        # code_embeddings has branch field
        await self._retry_write(
            lambda: self._qdrant._client.delete(
                collection_name="code_embeddings", points_selector=qdrant_branch_filter
            ),
            "Qdrant code_embeddings",
        )
        # doc_embeddings has no branch field
        await self._retry_write(
            lambda: self._qdrant._client.delete(
                collection_name="doc_embeddings", points_selector=qdrant_repo_filter
            ),
            "Qdrant doc_embeddings",
        )

    async def _batch_qdrant_upsert(
        self, collection_name: str, points: list[PointStruct], batch_size: int = 100
    ) -> None:
        """Upsert points to Qdrant in batches to avoid payload size limits."""
        for start in range(0, len(points), batch_size):
            batch = points[start : start + batch_size]
            await self._retry_write(
                lambda b=batch: self._qdrant._client.upsert(
                    collection_name=collection_name, points=b
                ),
                f"Qdrant {collection_name}[{start}:{start+len(batch)}]",
            )

    async def _retry_write(
        self,
        operation: Callable[[], Coroutine],
        target: str,
        max_retries: int = 3,
    ) -> None:
        """Execute an async write operation with exponential backoff retry.

        Raises:
            IndexWriteError: If all retries fail.
        """
        for attempt in range(1, max_retries + 1):
            try:
                await operation()
                return
            except Exception:
                if attempt == max_retries:
                    raise IndexWriteError(
                        f"{target} write failed after {max_retries} retries"
                    )
                await asyncio.sleep(2**attempt * 0.5)
