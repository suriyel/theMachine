"""Tests for Feature #14 — Symbol Query Handler.

Tests cover:
- detect_query_type() symbol detection heuristic
- handle_symbol_query() with ES term → fuzzy → NL fallback pipeline

Security: N/A — internal query routing, no direct user-facing input validation
  beyond length/empty checks (covered by boundary tests).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.query.query_handler import QueryHandler
from src.query.response_models import QueryResponse
from src.query.scored_chunk import ScoredChunk
from src.shared.exceptions import ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_handler(
    retriever=None, rank_fusion=None, reranker=None, response_builder=None
) -> QueryHandler:
    """Build a QueryHandler with optional mock dependencies."""
    return QueryHandler(
        retriever=retriever or MagicMock(),
        rank_fusion=rank_fusion or MagicMock(),
        reranker=reranker or MagicMock(),
        response_builder=response_builder or MagicMock(),
    )


def _make_es_hit(symbol: str, repo_id: str = "repo1") -> dict:
    """Build a fake ES hit dict matching Retriever._parse_code_hits format."""
    return {
        "_id": f"chunk-{symbol}",
        "_score": 5.0,
        "_source": {
            "repo_id": repo_id,
            "file_path": f"src/{symbol}.py",
            "content": f"class {symbol}: pass",
            "language": "python",
            "chunk_type": "class",
            "symbol": symbol,
            "signature": None,
            "doc_comment": None,
            "line_start": 1,
            "line_end": 10,
            "parent_class": None,
        },
    }


def _make_scored_chunk(symbol: str, repo_id: str = "repo1") -> ScoredChunk:
    """Build a ScoredChunk for test expectations."""
    return ScoredChunk(
        chunk_id=f"chunk-{symbol}",
        content_type="code",
        repo_id=repo_id,
        file_path=f"src/{symbol}.py",
        content=f"class {symbol}: pass",
        score=5.0,
        language="python",
        chunk_type="class",
        symbol=symbol,
    )


# ---------------------------------------------------------------------------
# A: detect_query_type — happy path classification
# [unit]
# ---------------------------------------------------------------------------

class TestDetectQueryType:
    """Tests A1, A3-A9, C5-C9: detect_query_type heuristic."""

    @pytest.mark.parametrize(
        "query, expected, reason",
        [
            # A1: dot notation
            ("UserService.getById", "symbol", "dot notation"),
            # A3: double-colon
            ("std::vector", "symbol", ":: notation"),
            # A7: hash notation
            ("Array#map", "symbol", "# notation"),
            # A4: camelCase
            ("getUserName", "symbol", "camelCase"),
            # A5: PascalCase
            ("UserService", "symbol", "PascalCase"),
            # A6: snake_case
            ("get_user_name", "symbol", "snake_case"),
            # A8: natural language with spaces
            ("how to handle errors", "nl", "spaces → NL"),
            # A8b: spaces with dot → still NL (spaces override dot)
            ("call user.save with retry", "nl", "spaces override dot"),
            # C5: minimal dot-separated
            ("a.b", "symbol", "minimal dot-separated"),
            # C6: minimal camelCase
            ("aB", "symbol", "minimal camelCase"),
            # C7: minimal snake_case
            ("a_b", "symbol", "minimal snake_case"),
            # C8: single lowercase word, no pattern
            ("hello", "nl", "single word, no pattern"),
            # C9: all uppercase, no underscores
            ("CONSTANT", "nl", "all-caps, no underscores → NL"),
        ],
        ids=[
            "A1-dot", "A3-doublecolon", "A7-hash",
            "A4-camelCase", "A5-PascalCase", "A6-snake_case",
            "A8-natural-language", "A8b-spaces-with-dot",
            "C5-minimal-dot", "C6-minimal-camelCase", "C7-minimal-snake",
            "C8-single-word", "C9-all-caps",
        ],
    )
    def test_detect_query_type(self, query: str, expected: str, reason: str):
        handler = _make_handler()
        result = handler.detect_query_type(query)
        assert result == expected, f"Expected '{expected}' for '{query}' ({reason}), got '{result}'"


# ---------------------------------------------------------------------------
# B: handle_symbol_query — ES term, fuzzy fallback, NL fallback
# [unit]
# ---------------------------------------------------------------------------

class TestHandleSymbolQuery:
    """Tests A2, B1, B2, D2: handle_symbol_query pipeline."""

    @pytest.mark.asyncio
    async def test_a2_term_hits_returns_symbol_response(self):
        """A2: ES term query returns hits → rerank → build response with query_type='symbol'."""
        retriever = MagicMock()
        reranker = MagicMock()
        response_builder = MagicMock()

        # Mock ES term query returning 2 hits
        term_hits = [_make_es_hit("vector"), _make_es_hit("vector_impl")]
        retriever._execute_search = AsyncMock(return_value=term_hits)
        retriever._code_index = "code_chunks"

        parsed_chunks = [_make_scored_chunk("vector"), _make_scored_chunk("vector_impl")]
        retriever._parse_code_hits = MagicMock(return_value=parsed_chunks)

        reranked = [_make_scored_chunk("vector")]
        reranker.rerank = MagicMock(return_value=reranked)

        expected_response = QueryResponse(
            query="std::vector", query_type="symbol", repo="repo1",
            code_results=[], doc_results=[],
        )
        response_builder.build = MagicMock(return_value=expected_response)

        handler = _make_handler(retriever, reranker=reranker, response_builder=response_builder)
        result = await handler.handle_symbol_query("std::vector", "repo1")

        assert result.query_type == "symbol"
        assert result.query == "std::vector"
        # Verify term query was called with correct structure
        retriever._execute_search.assert_called_once()
        call_args = retriever._execute_search.call_args
        query_body = call_args[0][1]  # second positional arg = body
        assert "term" in str(query_body), "Expected ES term query"
        # Verify reranker was called with parsed chunks
        reranker.rerank.assert_called_once_with("std::vector", parsed_chunks, top_k=6)
        # Verify response builder called with query_type="symbol"
        response_builder.build.assert_called_once()
        build_args = response_builder.build.call_args
        assert build_args[0][2] == "symbol"  # 3rd positional arg = query_type

    @pytest.mark.asyncio
    async def test_b2_fuzzy_fallback(self):
        """B2: term returns 0 hits, fuzzy returns hits → uses fuzzy results."""
        retriever = MagicMock()
        reranker = MagicMock()
        response_builder = MagicMock()

        # First call (term) → empty, second call (fuzzy) → hits
        fuzzy_hits = [_make_es_hit("vector")]
        retriever._execute_search = AsyncMock(side_effect=[[], fuzzy_hits])
        retriever._code_index = "code_chunks"

        parsed_chunks = [_make_scored_chunk("vector")]
        retriever._parse_code_hits = MagicMock(return_value=parsed_chunks)

        reranked = [_make_scored_chunk("vector")]
        reranker.rerank = MagicMock(return_value=reranked)

        expected_response = QueryResponse(
            query="vectr", query_type="symbol", repo="repo1",
        )
        response_builder.build = MagicMock(return_value=expected_response)

        handler = _make_handler(retriever, reranker=reranker, response_builder=response_builder)
        result = await handler.handle_symbol_query("vectr", "repo1")

        # Two ES calls: term then fuzzy
        assert retriever._execute_search.call_count == 2
        # Second call should be fuzzy query
        second_call_body = retriever._execute_search.call_args_list[1][0][1]
        assert "match" in str(second_call_body) or "fuzzy" in str(second_call_body).lower()
        assert result.query_type == "symbol"

    @pytest.mark.asyncio
    async def test_b1_nl_fallback(self):
        """B1: term and fuzzy both return 0 hits → falls back to NL pipeline."""
        retriever = MagicMock()
        reranker = MagicMock()
        response_builder = MagicMock()
        rank_fusion = MagicMock()

        # Both ES calls return empty
        retriever._execute_search = AsyncMock(return_value=[])
        retriever._code_index = "code_chunks"
        retriever._parse_code_hits = MagicMock(return_value=[])

        # Mock the NL pipeline path (bm25/vector searches)
        retriever.bm25_code_search = AsyncMock(return_value=[])
        retriever.vector_code_search = AsyncMock(return_value=[])
        retriever.bm25_doc_search = AsyncMock(return_value=[])
        retriever.vector_doc_search = AsyncMock(return_value=[])

        rank_fusion.fuse = MagicMock(return_value=[])
        reranker.rerank = MagicMock(return_value=[])

        nl_response = QueryResponse(
            query="nonExistentSymbol", query_type="nl", repo="repo1",
        )
        response_builder.build = MagicMock(return_value=nl_response)

        handler = _make_handler(retriever, rank_fusion, reranker, response_builder)
        result = await handler.handle_symbol_query("nonExistentSymbol", "repo1")

        # Should have fallen back to NL pipeline — verify it returned a response
        assert isinstance(result, QueryResponse)
        # The response from NL pipeline was returned
        assert result == nl_response

    @pytest.mark.asyncio
    async def test_d2_response_query_type_is_symbol(self):
        """D2: When term hits exist, response has query_type='symbol'."""
        retriever = MagicMock()
        reranker = MagicMock()
        response_builder = MagicMock()

        term_hits = [_make_es_hit("MyClass")]
        retriever._execute_search = AsyncMock(return_value=term_hits)
        retriever._code_index = "code_chunks"
        retriever._parse_code_hits = MagicMock(return_value=[_make_scored_chunk("MyClass")])
        reranker.rerank = MagicMock(return_value=[_make_scored_chunk("MyClass")])

        symbol_response = QueryResponse(
            query="MyClass.method", query_type="symbol", repo="repo1",
        )
        response_builder.build = MagicMock(return_value=symbol_response)

        handler = _make_handler(retriever, reranker=reranker, response_builder=response_builder)
        result = await handler.handle_symbol_query("MyClass.method", "repo1")

        # Verify build was called with query_type="symbol"
        build_call = response_builder.build.call_args
        assert build_call[0][2] == "symbol", "ResponseBuilder must be called with query_type='symbol'"


# ---------------------------------------------------------------------------
# C: Validation errors and boundary cases
# [unit]
# ---------------------------------------------------------------------------

class TestSymbolQueryValidation:
    """Tests C1-C4: validation and boundary tests for handle_symbol_query."""

    @pytest.mark.asyncio
    async def test_c1_exceeds_200_chars(self):
        """C1: query > 200 chars raises ValidationError."""
        handler = _make_handler()
        long_query = "a" * 201
        with pytest.raises(ValidationError, match="200 character"):
            await handler.handle_symbol_query(long_query, "repo1")

    @pytest.mark.asyncio
    async def test_c2_empty_query(self):
        """C2: empty query raises ValidationError."""
        handler = _make_handler()
        with pytest.raises(ValidationError, match="must not be empty"):
            await handler.handle_symbol_query("", "repo1")

    @pytest.mark.asyncio
    async def test_c3_whitespace_only(self):
        """C3: whitespace-only query raises ValidationError."""
        handler = _make_handler()
        with pytest.raises(ValidationError, match="must not be empty"):
            await handler.handle_symbol_query("   ", "repo1")

    @pytest.mark.asyncio
    async def test_c4_exactly_200_chars_no_error(self):
        """C4: query exactly 200 chars is accepted (no ValidationError)."""
        retriever = MagicMock()
        reranker = MagicMock()
        response_builder = MagicMock()
        rank_fusion = MagicMock()

        # Both ES calls return empty → NL fallback
        retriever._execute_search = AsyncMock(return_value=[])
        retriever._code_index = "code_chunks"
        retriever._parse_code_hits = MagicMock(return_value=[])
        retriever.bm25_code_search = AsyncMock(return_value=[])
        retriever.vector_code_search = AsyncMock(return_value=[])
        retriever.bm25_doc_search = AsyncMock(return_value=[])
        retriever.vector_doc_search = AsyncMock(return_value=[])
        rank_fusion.fuse = MagicMock(return_value=[])
        reranker.rerank = MagicMock(return_value=[])
        response_builder.build = MagicMock(
            return_value=QueryResponse(query="a" * 200, query_type="nl", repo="repo1")
        )

        handler = _make_handler(retriever, rank_fusion, reranker, response_builder)
        # Should NOT raise — exactly 200 is allowed
        result = await handler.handle_symbol_query("a" * 200, "repo1")
        assert isinstance(result, QueryResponse)


# ---------------------------------------------------------------------------
# D: Error propagation
# [unit]
# ---------------------------------------------------------------------------

class TestSymbolQueryErrorPropagation:
    """Test D1: ES error propagation."""

    @pytest.mark.asyncio
    async def test_d1_es_error_propagates(self):
        """D1: When ES raises RetrievalError on term query, it propagates."""
        from src.query.exceptions import RetrievalError

        retriever = MagicMock()
        retriever._execute_search = AsyncMock(
            side_effect=RetrievalError("Elasticsearch search failed")
        )
        retriever._code_index = "code_chunks"

        handler = _make_handler(retriever)
        with pytest.raises(RetrievalError, match="Elasticsearch search failed"):
            await handler.handle_symbol_query("MyClass", "repo1")


# ---------------------------------------------------------------------------
# Real tests — pure-function exemption
# [no integration test] — detect_query_type is a pure function with no
# external I/O. handle_symbol_query delegates to Retriever (ES) which is
# tested in Feature #8 integration tests. No new external dependency
# introduced by this feature.
# ---------------------------------------------------------------------------
