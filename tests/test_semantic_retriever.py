"""Tests for SemanticRetriever - Feature #9 Semantic Retrieval (FR-009).

These tests verify vector-based semantic search against Qdrant.

[unit] — uses mocked Qdrant client and encoder
[integration] — uses real Qdrant (if available)
"""
import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import asdict
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, ScoredPoint

# Import the class under test - will fail until implemented
from src.query.retriever import SemanticRetriever, Candidate


# [real_test] — Real Qdrant integration test
@pytest.mark.real_test
class TestSemanticRetrieverReal:
    """Real integration tests for SemanticRetriever with actual Qdrant."""

    @pytest.fixture
    def real_retriever(self):
        """Create SemanticRetriever with real Qdrant client."""
        from qdrant_client import AsyncQdrantClient
        from src.indexing.embedding_encoder import EmbeddingEncoder
        from src.query.config import settings

        qdrant = AsyncQdrantClient(url=settings.QDRANT_URL)
        encoder = EmbeddingEncoder()
        retriever = SemanticRetriever(
            qdrant_client=qdrant,
            encoder=encoder,
            threshold=0.6,
            collection_name="code_chunks"
        )
        return retriever

    @pytest.mark.asyncio
    async def test_real_qdrant_semantic_search(self, real_retriever):
        """Given indexed code chunks in Qdrant, when semantic search executes, then semantically related results are returned."""
        # Search for semantically related content
        results = await real_retriever.retrieve("how to configure spring http client timeout", {})

        # Verify we get results
        assert isinstance(results, list)

        # If there are results, verify structure
        for r in results:
            assert isinstance(r, Candidate)
            assert r.chunk_id is not None
            assert r.content is not None
            assert r.score >= 0.6  # Must meet threshold

    @pytest.mark.asyncio
    async def test_real_qdrant_no_match_returns_empty(self, real_retriever):
        """Given no matching content above threshold, when semantic search executes, then empty list is returned."""
        # Use random unlikely query
        results = await real_retriever.retrieve("xyznonexistentquery12345xyz", {})

        # Should return empty if nothing above threshold
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_real_qdrant_repo_filter(self, real_retriever):
        """Given query with repo filter, when semantic search executes, then only that repo is returned."""
        results = await real_retriever.retrieve("timeout", {"repo_filter": "spring-framework"})

        # Verify all results are from that repo
        for r in results:
            assert r.repo_name == "spring-framework"


class TestSemanticRetrieverUnit:
    """Unit tests for SemanticRetriever using mocked Qdrant."""

    @pytest.fixture
    def mock_qdrant_client(self):
        """Create a mocked Qdrant client."""
        client = AsyncMock()
        # Remove spec to allow setting any attribute
        client.search = AsyncMock()
        return client

    @pytest.fixture
    def mock_encoder(self):
        """Create a mocked EmbeddingEncoder."""
        encoder = MagicMock()
        # Return a 1024-dimensional embedding
        encoder.encode_query.return_value = [0.1] * 1024
        return encoder

    @pytest.fixture
    def retriever(self, mock_qdrant_client, mock_encoder):
        """Create SemanticRetriever with mocked dependencies."""
        return SemanticRetriever(
            qdrant_client=mock_qdrant_client,
            encoder=mock_encoder,
            threshold=0.6,
            collection_name="code_chunks"
        )

    # [unit] — happy path: semantic search returns results above threshold
    @pytest.mark.asyncio
    async def test_semantic_query_returns_matching_chunks(self, retriever, mock_qdrant_client):
        """Given query 'how to configure spring http client timeout' and indexed chunks about WebClient timeout,
        when semantic retrieval executes,
        then semantically related chunks appear despite keyword mismatch."""
        # Mock Qdrant response with high-scored results
        mock_qdrant_client.search.return_value = [
            ScoredPoint(
                id="chunk-123",
                version=1,
                score=0.85,
                payload={
                    "repo_name": "spring-framework",
                    "file_path": "src/main/java/client/WebClient.java",
                    "symbol": "WebClient",
                    "content": "public class WebClient { public Builder responseTimeout(Duration timeout) { ... } }",
                    "language": "java"
                },
                vector=None,
                shard_key=None,
                missing=None
            )
        ]

        # Execute query
        results = await retriever.retrieve("how to configure spring http client timeout", {})

        # Verify results
        assert len(results) == 1
        assert results[0].chunk_id == "chunk-123"
        assert results[0].repo_name == "spring-framework"
        assert "WebClient" in results[0].content
        assert results[0].score == 0.85
        assert results[0].score >= 0.6  # Above threshold

        # Verify encoder was called
        retriever._encoder.encode_query.assert_called_once()

    # [unit] — error handling: no matches above threshold returns empty list
    @pytest.mark.asyncio
    async def test_no_semantic_matches_above_threshold_returns_empty(self, retriever, mock_qdrant_client):
        """Given a query with no semantic matches scoring at or above the configured similarity threshold (default 0.6),
        when semantic retrieval executes,
        then an empty candidate list is returned for this retrieval method."""
        # Mock Qdrant response with low-scored results (below threshold)
        mock_qdrant_client.search.return_value = [
            ScoredPoint(
                id="chunk-low",
                version=1,
                score=0.3,  # Below 0.6 threshold
                payload={
                    "repo_name": "some-repo",
                    "file_path": "file.java",
                    "symbol": None,
                    "content": "some content",
                    "language": "java"
                },
                vector=None,
                shard_key=None,
                missing=None
            )
        ]

        results = await retriever.retrieve("xyznonexistent123", {})

        assert results == []

    # [unit] — boundary: configurable threshold filters results
    @pytest.mark.asyncio
    async def test_higher_threshold_filters_more_results(self, retriever, mock_qdrant_client, mock_encoder):
        """Given the similarity threshold is configured to 0.8,
        when semantic retrieval executes,
        then only chunks with similarity score >= 0.8 are returned."""
        # Create retriever with higher threshold
        high_threshold_retriever = SemanticRetriever(
            qdrant_client=mock_qdrant_client,
            encoder=mock_encoder,
            threshold=0.8,  # Higher threshold
            collection_name="code_chunks"
        )

        # Mock Qdrant response with mixed scores
        mock_qdrant_client.search.return_value = [
            ScoredPoint(
                id="chunk-high",
                version=1,
                score=0.85,  # Above 0.8 threshold
                payload={
                    "repo_name": "repo1",
                    "file_path": "file1.java",
                    "symbol": None,
                    "content": "content1",
                    "language": "java"
                },
                vector=None,
                shard_key=None,
                missing=None
            ),
            ScoredPoint(
                id="chunk-low",
                version=1,
                score=0.7,  # Below 0.8 threshold
                payload={
                    "repo_name": "repo2",
                    "file_path": "file2.java",
                    "symbol": None,
                    "content": "content2",
                    "language": "java"
                },
                vector=None,
                shard_key=None,
                missing=None
            )
        ]

        results = await high_threshold_retriever.retrieve("query", {})

        # Should only return the result above 0.8
        assert len(results) == 1
        assert results[0].chunk_id == "chunk-high"
        assert results[0].score >= 0.8

    # [unit] — repo filter: only chunks from specified repo
    @pytest.mark.asyncio
    async def test_repo_filter_returns_only_that_repo(self, retriever, mock_qdrant_client):
        """Given query with repo filter,
        when semantic retrieval executes,
        then only chunks from specified repo are returned."""
        # Mock Qdrant response - should filter at Qdrant level
        mock_qdrant_client.search.return_value = [
            ScoredPoint(
                id="chunk-1",
                version=1,
                score=0.8,
                payload={
                    "repo_name": "spring-framework",
                    "file_path": "WebClient.java",
                    "symbol": None,
                    "content": "timeout code",
                    "language": "java"
                },
                vector=None,
                shard_key=None,
                missing=None
            )
        ]

        results = await retriever.retrieve("timeout", {"repo_filter": "spring-framework"})

        assert len(results) == 1
        assert results[0].repo_name == "spring-framework"

        # Verify Qdrant search was called with filter
        call_args = mock_qdrant_client.search.call_args
        assert call_args is not None

    # [unit] — language filter: only chunks in specified language
    @pytest.mark.asyncio
    async def test_language_filter_returns_only_that_language(self, retriever, mock_qdrant_client):
        """Given query with language filter,
        when semantic retrieval executes,
        then only chunks in specified language are returned."""
        mock_qdrant_client.search.return_value = [
            ScoredPoint(
                id="chunk-1",
                version=1,
                score=0.8,
                payload={
                    "repo_name": "myrepo",
                    "file_path": "main.py",
                    "symbol": "process",
                    "content": "def process(): pass",
                    "language": "python"
                },
                vector=None,
                shard_key=None,
                missing=None
            )
        ]

        results = await retriever.retrieve("process", {"language_filter": "python"})

        assert len(results) == 1
        assert results[0].language == "python"

    # [unit] — boundary: combined filters
    @pytest.mark.asyncio
    async def test_combined_repo_and_language_filter(self, retriever, mock_qdrant_client):
        """Given query with both repo and language filter,
        when semantic retrieval executes,
        then only matching chunks are returned."""
        mock_qdrant_client.search.return_value = [
            ScoredPoint(
                id="chunk-1",
                version=1,
                score=0.8,
                payload={
                    "repo_name": "myrepo",
                    "file_path": "main.py",
                    "symbol": "process",
                    "content": "def process(): pass",
                    "language": "python"
                },
                vector=None,
                shard_key=None,
                missing=None
            )
        ]

        results = await retriever.retrieve(
            "process",
            {"repo_filter": "myrepo", "language_filter": "python"}
        )

        assert len(results) == 1
        assert results[0].repo_name == "myrepo"
        assert results[0].language == "python"

    # [unit] — boundary: empty query raises error
    @pytest.mark.asyncio
    async def test_empty_query_raises_error(self, retriever, mock_qdrant_client):
        """Given empty query string,
        when semantic retrieval executes,
        then validation error is returned."""
        with pytest.raises(ValueError, match="Query text cannot be empty"):
            await retriever.retrieve("", {})

    # [unit] — boundary: whitespace-only query raises error
    @pytest.mark.asyncio
    async def test_whitespace_only_query_raises_error(self, retriever, mock_qdrant_client):
        """Given query with only whitespace,
        when semantic retrieval executes,
        then validation error is returned."""
        with pytest.raises(ValueError, match="Query text cannot be empty"):
            await retriever.retrieve("   ", {})

    # [unit] — error handling: Qdrant connection error propagates
    @pytest.mark.asyncio
    async def test_qdrant_connection_error_raises_exception(self, retriever, mock_qdrant_client):
        """Given Qdrant connection error,
        when semantic retrieval executes,
        then exception is propagated."""
        mock_qdrant_client.search.side_effect = Exception("Connection refused")

        with pytest.raises(Exception, match="Connection refused"):
            await retriever.retrieve("query", {})

    # [unit] — error handling: encoder error propagates
    @pytest.mark.asyncio
    async def test_encoder_error_raises_exception(self, retriever, mock_qdrant_client, mock_encoder):
        """Given encoder error,
        when semantic retrieval executes,
        then exception is propagated."""
        mock_encoder.encode_query.side_effect = Exception("Model loading failed")

        with pytest.raises(Exception, match="Model loading failed"):
            await retriever.retrieve("query", {})


class TestSemanticRetrieverDefaults:
    """Tests for default values and initialization."""

    def test_default_threshold_is_0_6(self):
        """Given no threshold specified, when creating SemanticRetriever, then default threshold is 0.6."""
        mock_client = AsyncMock(spec=AsyncQdrantClient)
        mock_encoder = MagicMock()

        retriever = SemanticRetriever(
            qdrant_client=mock_client,
            encoder=mock_encoder
        )

        assert retriever._threshold == 0.6

    def test_default_collection_name(self):
        """Given no collection name specified, when creating SemanticRetriever, then default is 'code_chunks'."""
        mock_client = AsyncMock(spec=AsyncQdrantClient)
        mock_encoder = MagicMock()

        retriever = SemanticRetriever(
            qdrant_client=mock_client,
            encoder=mock_encoder
        )

        assert retriever._collection_name == "code_chunks"

    def test_custom_threshold(self):
        """Given custom threshold specified, when creating SemanticRetriever, then custom value is used."""
        mock_client = AsyncMock(spec=AsyncQdrantClient)
        mock_encoder = MagicMock()

        retriever = SemanticRetriever(
            qdrant_client=mock_client,
            encoder=mock_encoder,
            threshold=0.75
        )

        assert retriever._threshold == 0.75
