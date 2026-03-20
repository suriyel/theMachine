"""Index writer for storing code chunks in Elasticsearch and Qdrant."""

import os
from typing import List

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from elasticsearch import AsyncElasticsearch

from src.indexing.models import CodeChunk


# Elasticsearch index name
ES_INDEX_NAME = "code_chunks"

# Qdrant collection name
QDRANT_COLLECTION_NAME = "code_chunks"


class IndexWriter:
    """Writes code chunks and embeddings to Elasticsearch and Qdrant.

    Attributes:
        es_index: Name of the Elasticsearch index
        qdrant_collection: Name of the Qdrant collection
    """

    def __init__(
        self,
        es_client: AsyncElasticsearch | None = None,
        qdrant_client: QdrantClient | None = None,
    ):
        """Initialize the index writer.

        Args:
            es_client: Optional Elasticsearch client (for testing)
            qdrant_client: Optional Qdrant client (for testing)
        """
        self._es_client = es_client
        self._qdrant_client = qdrant_client
        self._es_index = ES_INDEX_NAME
        self._qdrant_collection = QDRANT_COLLECTION_NAME
        self._es_initialized = False

    @property
    def es_index(self) -> str:
        """Get the Elasticsearch index name."""
        return self._es_index

    @property
    def qdrant_collection(self) -> str:
        """Get the Qdrant collection name."""
        return self._qdrant_collection

    def _get_es_client(self) -> AsyncElasticsearch:
        """Get or create Elasticsearch client."""
        if self._es_client is None:
            es_url = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
            self._es_client = AsyncElasticsearch([es_url])
        return self._es_client

    def _get_qdrant_client(self) -> QdrantClient:
        """Get or create Qdrant client."""
        if self._qdrant_client is None:
            qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
            self._qdrant_client = QdrantClient(url=qdrant_url)
        return self._qdrant_client

    async def _ensure_es_index(self):
        """Ensure Elasticsearch index exists with proper mappings."""
        if self._es_initialized:
            return

        client = self._get_es_client()

        # Create index if not exists
        if not await client.indices.exists(index=self._es_index):
            await client.indices.create(
                index=self._es_index,
                body={
                    "mappings": {
                        "properties": {
                            "chunk_id": {"type": "keyword"},
                            "repo_id": {"type": "keyword"},
                            "file_path": {"type": "keyword"},
                            "language": {"type": "keyword"},
                            "symbol_name": {"type": "keyword"},
                            "symbol_type": {"type": "keyword"},
                            "chunk_type": {"type": "keyword"},
                            "start_line": {"type": "integer"},
                            "end_line": {"type": "integer"},
                            "content": {"type": "text"},
                        }
                    }
                },
            )

        self._es_initialized = True

    async def _ensure_qdrant_collection(self, dimension: int = 1024):
        """Ensure Qdrant collection exists."""
        client = self._get_qdrant_client()

        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self._qdrant_collection not in collection_names:
            client.create_collection(
                collection_name=self._qdrant_collection,
                vectors_config=VectorParams(
                    size=dimension,
                    distance=Distance.COSINE,
                ),
            )

    def _generate_chunk_id(self, chunk: CodeChunk) -> str:
        """Generate a unique chunk ID."""
        return f"{chunk.repo_id}:{chunk.file_path}:{chunk.start_line}:{chunk.symbol_name or 'file'}"

    async def write_chunks(
        self,
        chunks: List[CodeChunk],
        embeddings: List[List[float]],
    ) -> None:
        """Write code chunks and their embeddings to both stores.

        Args:
            chunks: List of CodeChunk objects to write.
            embeddings: List of embedding vectors (one per chunk).
        """
        if not chunks or not embeddings:
            return

        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Number of chunks ({len(chunks)}) must match number of embeddings ({len(embeddings)})"
            )

        # Write to Elasticsearch
        await self._write_to_elasticsearch(chunks)

        # Write to Qdrant
        await self._write_to_qdrant(chunks, embeddings)

    async def _write_to_elasticsearch(self, chunks: List[CodeChunk]) -> None:
        """Write chunks to Elasticsearch."""
        if self._es_client is None:
            return
        await self._ensure_es_index()
        client = self._get_es_client()

        # Generate bulk index operations
        operations = []
        for chunk in chunks:
            chunk_id = self._generate_chunk_id(chunk)
            doc = {
                "chunk_id": chunk_id,
                "repo_id": chunk.repo_id,
                "file_path": str(chunk.file_path),
                "language": chunk.language,
                "symbol_name": chunk.symbol_name,
                "symbol_type": chunk.symbol_type,
                "chunk_type": chunk.chunk_type.value if hasattr(chunk.chunk_type, 'value') else str(chunk.chunk_type),
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "content": chunk.content,
            }
            operations.append({"index": {"_index": self._es_index, "_id": chunk_id}})
            operations.append(doc)

        if operations:
            await client.bulk(operations=operations)

    async def _write_to_qdrant(self, chunks: List[CodeChunk], embeddings: List[List[float]]) -> None:
        """Write vectors to Qdrant."""
        client = self._get_qdrant_client()

        # Ensure collection exists
        await self._ensure_qdrant_collection(dimension=len(embeddings[0]) if embeddings else 1024)

        # Generate points
        points = []
        for chunk, embedding in zip(chunks, embeddings):
            chunk_id = self._generate_chunk_id(chunk)
            point = PointStruct(
                id=chunk_id,
                vector=embedding,
                payload={
                    "repo_id": chunk.repo_id,
                    "file_path": str(chunk.file_path),
                    "language": chunk.language,
                    "symbol_name": chunk.symbol_name,
                    "chunk_type": chunk.chunk_type.value if hasattr(chunk.chunk_type, 'value') else str(chunk.chunk_type),
                },
            )
            points.append(point)

        if points:
            client.upsert(
                collection_name=self._qdrant_collection,
                points=points,
            )

    async def delete_by_repo(self, repo_id: str) -> None:
        """Delete all chunks for a specific repository.

        Args:
            repo_id: Repository ID to delete chunks for.
        """
        # Delete from Elasticsearch
        await self._delete_from_elasticsearch(repo_id)

        # Delete from Qdrant
        await self._delete_from_qdrant(repo_id)

    async def _delete_from_elasticsearch(self, repo_id: str) -> None:
        """Delete chunks from Elasticsearch by repo_id."""
        if self._es_client is None:
            return
        await self._ensure_es_index()
        client = self._get_es_client()

        try:
            await client.delete_by_query(
                index=self._es_index,
                body={
                    "query": {
                        "term": {"repo_id": repo_id}
                    }
                },
            )
        except Exception:
            # Index might not exist yet, which is fine
            pass

    async def _delete_from_qdrant(self, repo_id: str) -> None:
        """Delete vectors from Qdrant by repo_id filter."""
        client = self._get_qdrant_client()

        try:
            client.delete(
                collection_name=self._qdrant_collection,
                points_selector={
                    "filter": {
                        "must": [
                            {"key": "repo_id", "match": {"value": repo_id}}
                        ]
                    }
                },
            )
        except Exception:
            # Collection might not exist yet, which is fine
            pass

    async def close(self):
        """Close client connections."""
        if self._es_client:
            await self._es_client.close()
        if self._qdrant_client:
            self._qdrant_client.close()
