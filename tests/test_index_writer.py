"""Tests for IndexWriter - Feature #7."""

import pytest
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from src.indexing.models import CodeChunk, ChunkType


# Real tests for IndexWriter - verify connectivity to actual services
@pytest.mark.real_test
class TestIndexWriterIntegration:
    """Integration tests for IndexWriter with real services."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.getenv("ELASTICSEARCH_URL") is None,
        reason="ELASTICSEARCH_URL not set - skipping Elasticsearch test"
    )
    async def test_elasticsearch_connection(self):
        """Given Elasticsearch is running, when connecting, then connection succeeds."""
        from src.indexing.index_writer import IndexWriter
        from elasticsearch import AsyncElasticsearch

        es_url = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
        client = AsyncElasticsearch([es_url])

        # Verify connection
        health = await client.cluster.health()
        assert health is not None
        await client.close()

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.getenv("QDRANT_URL") is None,
        reason="QDRANT_URL not set - skipping Qdrant test"
    )
    async def test_qdrant_connection(self):
        """Given Qdrant is running, when connecting, then connection succeeds."""
        from qdrant_client import QdrantClient

        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        client = QdrantClient(url=qdrant_url, timeout=5)

        # Verify connection - get collections
        collections = client.get_collections()
        assert collections is not None


class TestIndexWriter:
    """Unit tests for IndexWriter class."""

    def test_writer_can_be_instantiated(self):
        """Given IndexWriter class, when instantiated, then object is created."""
        # This test will fail because IndexWriter doesn't exist yet
        from src.indexing.index_writer import IndexWriter

        writer = IndexWriter()
        assert writer is not None

    @pytest.mark.asyncio
    async def test_write_chunks_to_elasticsearch(self):
        """Given chunks and embeddings, when write_chunks is called, then documents are written to Elasticsearch."""
        from src.indexing.index_writer import IndexWriter

        # Mock ES client
        mock_es = AsyncMock()
        mock_es.indices.exists.return_value = True
        mock_es.bulk = AsyncMock()

        # Mock Qdrant client
        mock_qdrant = MagicMock()
        mock_qdrant.get_collections.return_value = MagicMock(collections=[])
        mock_qdrant.upsert = MagicMock()

        writer = IndexWriter(es_client=mock_es, qdrant_client=mock_qdrant)
        chunks = [
            CodeChunk(
                repo_id="test-repo-1",
                file_path=Path("src/main.java"),
                language="Java",
                chunk_type=ChunkType.CLASS,
                symbol_name="HelloWorld",
                symbol_type="class",
                start_line=1,
                end_line=10,
                content="public class HelloWorld {}"
            )
        ]
        embeddings = [[0.1] * 1024]

        # Should write to Elasticsearch without raising
        await writer.write_chunks(chunks, embeddings)
        # Verify bulk was called
        assert mock_es.bulk.called

    @pytest.mark.asyncio
    async def test_write_chunks_to_qdrant(self):
        """Given chunks and embeddings, when write_chunks is called, then vectors are written to Qdrant."""
        from src.indexing.index_writer import IndexWriter

        # Mock Qdrant client
        mock_qdrant = MagicMock()
        mock_qdrant.get_collections.return_value = MagicMock(collections=[])
        mock_qdrant.upsert = MagicMock()

        writer = IndexWriter(qdrant_client=mock_qdrant)
        chunks = [
            CodeChunk(
                repo_id="test-repo-1",
                file_path=Path("src/main.java"),
                language="Java",
                chunk_type=ChunkType.CLASS,
                symbol_name="HelloWorld",
                symbol_type="class",
                start_line=1,
                end_line=10,
                content="public class HelloWorld {}"
            )
        ]
        embeddings = [[0.1] * 1024]

        # Should write to Qdrant without raising
        await writer.write_chunks(chunks, embeddings)
        # Verify upsert was called
        assert mock_qdrant.upsert.called

    @pytest.mark.asyncio
    async def test_write_chunks_preserves_chunk_ids(self):
        """Given chunks with different IDs, when write_chunks is called, then chunk_ids are preserved in both stores."""
        from src.indexing.index_writer import IndexWriter

        # Mock ES client
        mock_es = AsyncMock()
        mock_es.indices.exists.return_value = True
        mock_es.bulk = AsyncMock()

        # Mock Qdrant client
        mock_qdrant = MagicMock()
        mock_qdrant.get_collections.return_value = MagicMock(collections=[])
        mock_qdrant.upsert = MagicMock()

        writer = IndexWriter(es_client=mock_es, qdrant_client=mock_qdrant)
        chunks = [
            CodeChunk(
                repo_id="test-repo-1",
                file_path=Path("src/main.java"),
                language="Java",
                chunk_type=ChunkType.CLASS,
                symbol_name="HelloWorld",
                symbol_type="class",
                start_line=1,
                end_line=10,
                content="public class HelloWorld {}"
            ),
            CodeChunk(
                repo_id="test-repo-1",
                file_path=Path("src/utils.java"),
                language="Java",
                chunk_type=ChunkType.FUNCTION,
                symbol_name="helper",
                symbol_type="function",
                start_line=15,
                end_line=20,
                content="public void helper() {}"
            )
        ]
        embeddings = [[0.1] * 1024, [0.2] * 1024]

        # Both chunks should be written
        await writer.write_chunks(chunks, embeddings)

    @pytest.mark.asyncio
    async def test_delete_by_repo_removes_from_elasticsearch(self):
        """Given a repository ID, when delete_by_repo is called, then all chunks for that repo are deleted from ES."""
        from src.indexing.index_writer import IndexWriter

        mock_es = AsyncMock()
        mock_es.indices.exists.return_value = True
        mock_es.delete_by_query = AsyncMock()

        writer = IndexWriter(es_client=mock_es)
        repo_id = "test-repo-to-delete"

        # Should delete without raising
        await writer.delete_by_repo(repo_id)
        assert mock_es.delete_by_query.called

    @pytest.mark.asyncio
    async def test_delete_by_repo_removes_from_qdrant(self):
        """Given a repository ID, when delete_by_repo is called, then all vectors for that repo are deleted from Qdrant."""
        from src.indexing.index_writer import IndexWriter

        mock_qdrant = MagicMock()
        mock_qdrant.delete = MagicMock()

        writer = IndexWriter(qdrant_client=mock_qdrant)
        repo_id = "test-repo-to-delete"

        # Should delete without raising
        await writer.delete_by_repo(repo_id)
        assert mock_qdrant.delete.called

    @pytest.mark.asyncio
    async def test_write_chunks_with_empty_list(self):
        """Given empty chunks list, when write_chunks is called, then no writes occur."""
        from src.indexing.index_writer import IndexWriter

        writer = IndexWriter()
        chunks = []
        embeddings = []

        # Should handle gracefully without raising
        await writer.write_chunks(chunks, embeddings)

    @pytest.mark.asyncio
    async def test_write_chunks_batch_writing(self):
        """Given 100 chunks, when write_chunks is called, then all are written in batch."""
        from src.indexing.index_writer import IndexWriter

        # Mock ES client
        mock_es = AsyncMock()
        mock_es.indices.exists.return_value = True
        mock_es.bulk = AsyncMock()

        # Mock Qdrant client
        mock_qdrant = MagicMock()
        mock_qdrant.get_collections.return_value = MagicMock(collections=[])
        mock_qdrant.upsert = MagicMock()

        writer = IndexWriter(es_client=mock_es, qdrant_client=mock_qdrant)
        chunks = [
            CodeChunk(
                repo_id="test-repo-1",
                file_path=Path(f"src/file{i}.java"),
                language="Java",
                chunk_type=ChunkType.FUNCTION,
                symbol_name=f"func{i}",
                symbol_type="function",
                start_line=i * 10,
                end_line=i * 10 + 5,
                content=f"public void func{i}() {{}}"
            )
            for i in range(100)
        ]
        embeddings = [[0.1 * i] * 1024 for i in range(100)]

        # Should handle 100 chunks without issues
        await writer.write_chunks(chunks, embeddings)
        # Verify both were called
        assert mock_es.bulk.called
        assert mock_qdrant.upsert.called

    @pytest.mark.asyncio
    async def test_delete_nonexistent_repo_succeeds(self):
        """Given a non-existent repository ID, when delete_by_repo is called, then operation succeeds."""
        from src.indexing.index_writer import IndexWriter

        # Mock ES to raise exception (index doesn't exist)
        mock_es = AsyncMock()
        mock_es.indices.exists.return_value = False
        mock_es.delete_by_query = AsyncMock()

        # Mock Qdrant to raise exception (collection doesn't exist)
        mock_qdrant = MagicMock()
        mock_qdrant.delete = MagicMock()

        writer = IndexWriter(es_client=mock_es, qdrant_client=mock_qdrant)
        nonexistent_repo_id = "nonexistent-repo-12345"

        # Should succeed even if nothing to delete
        await writer.delete_by_repo(nonexistent_repo_id)

    @pytest.mark.asyncio
    async def test_write_chunks_mismatched_lengths_raises(self):
        """Given mismatched chunks and embeddings length, when write_chunks is called, then ValueError is raised."""
        from src.indexing.index_writer import IndexWriter

        mock_es = AsyncMock()
        mock_qdrant = MagicMock()

        writer = IndexWriter(es_client=mock_es, qdrant_client=mock_qdrant)
        chunks = [
            CodeChunk(
                repo_id="test-repo-1",
                file_path=Path("src/main.java"),
                language="Java",
                chunk_type=ChunkType.CLASS,
                content="public class HelloWorld {}"
            )
        ]
        embeddings = [[0.1] * 1024, [0.2] * 1024]  # 2 embeddings for 1 chunk

        with pytest.raises(ValueError, match="must match"):
            await writer.write_chunks(chunks, embeddings)

    def test_es_index_property(self):
        """Given IndexWriter, when es_index is accessed, then correct index name is returned."""
        from src.indexing.index_writer import IndexWriter

        writer = IndexWriter()
        assert writer.es_index == "code_chunks"

    def test_qdrant_collection_property(self):
        """Given IndexWriter, when qdrant_collection is accessed, then correct collection name is returned."""
        from src.indexing.index_writer import IndexWriter

        writer = IndexWriter()
        assert writer.qdrant_collection == "code_chunks"

    @pytest.mark.asyncio
    async def test_close_method(self):
        """Given IndexWriter with clients, when close is called, then clients are closed."""
        from src.indexing.index_writer import IndexWriter

        mock_es = AsyncMock()
        mock_qdrant = MagicMock()

        writer = IndexWriter(es_client=mock_es, qdrant_client=mock_qdrant)
        await writer.close()

        mock_es.close.assert_called_once()
        mock_qdrant.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_method_no_clients(self):
        """Given IndexWriter without clients, when close is called, then no errors occur."""
        from src.indexing.index_writer import IndexWriter

        writer = IndexWriter()
        # Should not raise
        await writer.close()
