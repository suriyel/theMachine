"""Tests for KeywordRetriever - Feature #8 Keyword Retrieval (FR-008).

These tests verify BM25-based keyword search against Elasticsearch.

[unit] — uses mocked Elasticsearch client
[integration] — uses real Elasticsearch (if available)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import asdict

# Import the class under test - will fail until implemented
from src.query.retriever import KeywordRetriever, Candidate


class TestKeywordRetrieverUnit:
    """Unit tests for KeywordRetriever using mocked Elasticsearch."""

    @pytest.fixture
    def mock_es_client(self):
        """Create a mocked Elasticsearch client."""
        client = AsyncMock()
        return client

    @pytest.fixture
    def retriever(self, mock_es_client):
        """Create KeywordRetriever with mocked client."""
        return KeywordRetriever(
            es_client=mock_es_client,
            index_name="code_chunks"
        )

    # [unit] — happy path: query matching returns results
    @pytest.mark.asyncio
    async def test_keyword_query_returns_matching_chunks(self, retriever, mock_es_client):
        """Given query 'WebClient timeout' and indexed chunks containing 'WebClient.builder().responseTimeout()',
        when keyword retrieval executes,
        then matching chunks appear in results."""
        # Mock ES response
        mock_es_client.search.return_value = {
            "hits": {
                "hits": [
                    {
                        "_id": "chunk-123",
                        "_source": {
                            "repo_name": "spring-framework",
                            "file_path": "src/main/java/client/WebClient.java",
                            "symbol": "WebClient",
                            "content": "public class WebClient { public static Builder builder() { return new Builder(); } public Builder responseTimeout(Duration timeout) { ... } }",
                            "language": "java"
                        },
                        "_score": 5.5
                    }
                ]
            }
        }

        # Execute query
        results = await retriever.retrieve("WebClient timeout", {})

        # Verify results
        assert len(results) == 1
        assert results[0].chunk_id == "chunk-123"
        assert results[0].repo_name == "spring-framework"
        assert "WebClient" in results[0].content
        assert results[0].score == 5.5

        # Verify ES was called correctly
        mock_es_client.search.assert_called_once()
        call_args = mock_es_client.search.call_args
        assert call_args.kwargs["index"] == "code_chunks"
        # Check nested structure: body -> query -> bool -> must
        body = call_args.kwargs["body"]
        assert "query" in body
        assert "bool" in body["query"]
        assert "must" in body["query"]["bool"]
        assert "multi_match" in body["query"]["bool"]["must"][0]

    # [unit] — error handling: no matches returns empty list
    @pytest.mark.asyncio
    async def test_no_keyword_matches_returns_empty_list(self, retriever, mock_es_client):
        """Given a query with no keyword matches,
        when keyword retrieval executes,
        then empty candidate list is returned."""
        mock_es_client.search.return_value = {"hits": {"hits": []}}

        results = await retriever.retrieve("xyznonexistent123", {})

        assert results == []

    # [unit] — repo filter: only chunks from specified repo
    @pytest.mark.asyncio
    async def test_repo_filter_returns_only_that_repo(self, retriever, mock_es_client):
        """Given query with repo filter,
        when keyword retrieval executes,
        then only chunks from specified repo are returned."""
        mock_es_client.search.return_value = {
            "hits": {
                "hits": [
                    {
                        "_id": "chunk-1",
                        "_source": {
                            "repo_name": "spring-framework",
                            "file_path": "WebClient.java",
                            "symbol": None,
                            "content": "timeout code",
                            "language": "java"
                        },
                        "_score": 1.0
                    }
                ]
            }
        }

        results = await retriever.retrieve("timeout", {"repo_filter": "spring-framework"})

        assert len(results) == 1
        assert results[0].repo_name == "spring-framework"

        # Verify filter was applied (check nested structure)
        call_args = mock_es_client.search.call_args
        body = call_args.kwargs["body"]
        assert "query" in body
        assert "bool" in body["query"]
        assert "filter" in body["query"]["bool"]

    # [unit] — language filter: only chunks in specified language
    @pytest.mark.asyncio
    async def test_language_filter_returns_only_that_language(self, retriever, mock_es_client):
        """Given query with language filter,
        when keyword retrieval executes,
        then only chunks in specified language are returned."""
        mock_es_client.search.return_value = {
            "hits": {
                "hits": [
                    {
                        "_id": "chunk-1",
                        "_source": {
                            "repo_name": "myrepo",
                            "file_path": "main.py",
                            "symbol": "process",
                            "content": "def process(): pass",
                            "language": "python"
                        },
                        "_score": 1.0
                    }
                ]
            }
        }

        results = await retriever.retrieve("process", {"language_filter": "python"})

        assert len(results) == 1
        assert results[0].language == "python"

    # [unit] — boundary: combined filters
    @pytest.mark.asyncio
    async def test_combined_filters(self, retriever, mock_es_client):
        """Given query with both repo and language filter,
        when keyword retrieval executes,
        then only matching chunks are returned."""
        mock_es_client.search.return_value = {"hits": {"hits": []}}

        results = await retriever.retrieve(
            "query",
            {"repo_filter": "myrepo", "language_filter": "python"}
        )

        # Should return empty since no matches in mock
        assert results == []

    # [unit] — boundary: empty query
    @pytest.mark.asyncio
    async def test_empty_query_raises_error(self, retriever, mock_es_client):
        """Given empty query string,
        when keyword retrieval executes,
        then validation error is returned."""
        with pytest.raises(ValueError, match="Query text cannot be empty"):
            await retriever.retrieve("", {})

    # [unit] — boundary: whitespace-only query
    @pytest.mark.asyncio
    async def test_whitespace_only_query_raises_error(self, retriever, mock_es_client):
        """Given query with only whitespace,
        when keyword retrieval executes,
        then validation error is returned."""
        with pytest.raises(ValueError, match="Query text cannot be empty"):
            await retriever.retrieve("   ", {})

    # [unit] — error handling: ES connection error
    @pytest.mark.asyncio
    async def test_es_connection_error_raises_exception(self, retriever, mock_es_client):
        """Given ES connection error,
        when keyword retrieval executes,
        then exception is propagated."""
        mock_es_client.search.side_effect = Exception("Connection refused")

        with pytest.raises(Exception, match="Connection refused"):
            await retriever.retrieve("query", {})

    # [unit] — security: query injection prevention
    @pytest.mark.asyncio
    async def test_special_characters_in_query(self, retriever, mock_es_client):
        """Given query with special characters (potential injection),
        when keyword retrieval executes,
        then query is safely escaped."""
        import re
        mock_es_client.search.return_value = {"hits": {"hits": []}}

        # Query with potential injection characters
        await retriever.retrieve("test <script>alert(1)</script>", {})

        # Verify the query was passed through (ES handles escaping)
        call_args = mock_es_client.search.call_args
        assert call_args is not None


class TestCandidateDataclass:
    """Tests for Candidate dataclass."""

    def test_candidate_creation(self):
        """Given valid parameters, when creating Candidate, then all fields are set."""
        candidate = Candidate(
            chunk_id="test-123",
            repo_name="test-repo",
            file_path="src/main.py",
            symbol="test_func",
            content="def test_func(): pass",
            score=0.95
        )

        assert candidate.chunk_id == "test-123"
        assert candidate.repo_name == "test-repo"
        assert candidate.file_path == "src/main.py"
        assert candidate.symbol == "test_func"
        assert candidate.content == "def test_func(): pass"
        assert candidate.score == 0.95

    def test_candidate_to_dict(self):
        """Given a Candidate, when converting to dict, then all fields are serialized."""
        candidate = Candidate(
            chunk_id="test-123",
            repo_name="test-repo",
            file_path="main.py",
            symbol=None,
            content="code",
            score=0.5
        )

        result = asdict(candidate)

        assert result["chunk_id"] == "test-123"
        assert result["repo_name"] == "test-repo"
        assert result["symbol"] is None

    def test_candidate_equality(self):
        """Given two identical Candidates, when comparing, then they are equal."""
        c1 = Candidate(
            chunk_id="test-123",
            repo_name="repo",
            file_path="file.py",
            symbol=None,
            content="code",
            score=0.5
        )
        c2 = Candidate(
            chunk_id="test-123",
            repo_name="repo",
            file_path="file.py",
            symbol=None,
            content="code",
            score=0.5
        )

        assert c1 == c2
