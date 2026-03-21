"""IndexWriter — writes chunks and embeddings to Elasticsearch and Qdrant."""

from __future__ import annotations

import asyncio
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
    ) -> None:
        """Write code chunks to ES code_chunks index and Qdrant code_embeddings collection.

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
            operations.append({"index": {"_index": "code_chunks", "_id": chunk.chunk_id}})
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
            "ES code_chunks",
        )

        # Write to Qdrant
        points = [
            PointStruct(
                id=chunk.chunk_id,
                vector=embedding.tolist(),
                payload={
                    "repo_id": repo_id,
                    "file_path": chunk.file_path,
                    "language": chunk.language,
                    "chunk_type": chunk.chunk_type,
                    "symbol": chunk.symbol,
                    "branch": chunk.branch,
                },
            )
            for chunk, embedding in zip(chunks, embeddings)
        ]
        await self._retry_write(
            lambda: self._qdrant._client.upsert(
                collection_name="code_embeddings", points=points
            ),
            "Qdrant code_embeddings",
        )

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

        points = [
            PointStruct(
                id=chunk.chunk_id,
                vector=embedding.tolist(),
                payload={
                    "repo_id": repo_id,
                    "file_path": chunk.file_path,
                    "breadcrumb": chunk.breadcrumb,
                },
            )
            for chunk, embedding in zip(chunks, embeddings)
        ]
        await self._retry_write(
            lambda: self._qdrant._client.upsert(
                collection_name="doc_embeddings", points=points
            ),
            "Qdrant doc_embeddings",
        )

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

        Raises:
            IndexWriteError: If ES or Qdrant delete fails after 3 retries.
        """
        query = {"query": {"bool": {"must": [
            {"term": {"repo_id": repo_id}},
            {"term": {"branch": branch}},
        ]}}}

        for index in ["code_chunks", "doc_chunks", "rule_chunks"]:
            await self._retry_write(
                lambda idx=index: self._es._client.delete_by_query(
                    index=idx, body=query
                ),
                f"ES {index}",
            )

        from qdrant_client.models import Filter, FieldCondition, MatchValue

        qdrant_filter = Filter(must=[
            FieldCondition(key="repo_id", match=MatchValue(value=repo_id)),
            FieldCondition(key="branch", match=MatchValue(value=branch)),
        ])
        for collection in ["code_embeddings", "doc_embeddings"]:
            await self._retry_write(
                lambda coll=collection: self._qdrant._client.delete(
                    collection_name=coll, points_selector=qdrant_filter
                ),
                f"Qdrant {collection}",
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
