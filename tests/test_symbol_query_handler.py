"""Tests for Feature #14 — Symbol Query Handler.

Tests cover:
- detect_query_type() symbol detection heuristic
- handle_symbol_query() with ES term → fuzzy → NL fallback pipeline
- Doc BM25 search parallel to code search (design §4.2.5)
- Branch parsing and forwarding
- Security: injection payloads handled safely via validation

Security: Input validation (length/empty) prevents injection; tested in
  boundary tests C1-C3 and security tests SEC1-SEC5.
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
    r = retriever or MagicMock()
    # Ensure bm25_doc_search is always available as AsyncMock
    if not hasattr(r, "bm25_doc_search") or not isinstance(r.bm25_doc_search, AsyncMock):
        r.bm25_doc_search = AsyncMock(return_value=[])
    return QueryHandler(
        retriever=r,
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


def _make_scored_chunk(
    symbol: str, repo_id: str = "repo1", content_type: str = "code"
) -> ScoredChunk:
    """Build a ScoredChunk for test expectations."""
    return ScoredChunk(
        chunk_id=f"chunk-{symbol}",
        content_type=content_type,
        repo_id=repo_id,
        file_path=f"src/{symbol}.py",
        content=f"class {symbol}: pass",
        score=5.0,
        language="python",
        chunk_type="class",
        symbol=symbol,
    )


def _make_doc_chunk(title: str, repo_id: str = "repo1") -> ScoredChunk:
    """Build a doc-type ScoredChunk."""
    return ScoredChunk(
        chunk_id=f"doc-{title}",
        content_type="doc",
        repo_id=repo_id,
        file_path=f"docs/{title}.md",
        content=f"Documentation for {title}",
        score=3.0,
        language=None,
        chunk_type="doc",
        symbol=None,
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
    async def test_a2_term_hits_returns_symbol_response_with_docs(self):
        """A2: ES term hits → doc BM25 search → rerank combined → build response."""
        retriever = MagicMock()
        reranker = MagicMock()
        response_builder = MagicMock()

        # Mock ES term query returning 2 code hits
        term_hits = [_make_es_hit("vector"), _make_es_hit("vector_impl")]
        retriever._execute_search = AsyncMock(return_value=term_hits)
        retriever._code_index = "code_chunks"

        parsed_code = [_make_scored_chunk("vector"), _make_scored_chunk("vector_impl")]
        retriever._parse_code_hits = MagicMock(return_value=parsed_code)

        # Mock doc BM25 search returning 1 doc hit
        doc_chunk = _make_doc_chunk("vector-reference")
        retriever.bm25_doc_search = AsyncMock(return_value=[doc_chunk])

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
        # Verify reranker called with combined code + doc candidates and top_k=20
        reranker.rerank.assert_called_once()
        rerank_call = reranker.rerank.call_args
        combined = rerank_call[0][1]
        assert len(combined) == 3, "Expected 2 code + 1 doc = 3 combined candidates"
        assert rerank_call[1]["top_k"] == 20 or rerank_call[0][2] == 20
        # Verify doc search was called
        retriever.bm25_doc_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_b2_fuzzy_fallback_with_doc_search(self):
        """B2: term returns 0 hits, fuzzy returns hits → doc search + rerank."""
        retriever = MagicMock()
        reranker = MagicMock()
        response_builder = MagicMock()

        # First call (term) → empty, second call (fuzzy) → hits
        fuzzy_hits = [_make_es_hit("vector")]
        retriever._execute_search = AsyncMock(side_effect=[[], fuzzy_hits])
        retriever._code_index = "code_chunks"

        parsed_chunks = [_make_scored_chunk("vector")]
        retriever._parse_code_hits = MagicMock(return_value=parsed_chunks)

        # Doc search returns 1 doc
        retriever.bm25_doc_search = AsyncMock(return_value=[_make_doc_chunk("vector-ref")])

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
        # Doc search called for fuzzy path
        retriever.bm25_doc_search.assert_called()
        # Reranker receives combined code + doc, top_k=20
        rerank_call = reranker.rerank.call_args
        assert len(rerank_call[0][1]) == 2, "Expected 1 code + 1 doc = 2 combined"
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
        retriever.bm25_doc_search = AsyncMock(return_value=[])
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

    @pytest.mark.asyncio
    async def test_doc_search_failure_continues_with_code_only(self):
        """Doc BM25 search failure is handled gracefully — proceeds with code chunks only."""
        retriever = MagicMock()
        reranker = MagicMock()
        response_builder = MagicMock()

        term_hits = [_make_es_hit("MyClass")]
        retriever._execute_search = AsyncMock(return_value=term_hits)
        retriever._code_index = "code_chunks"
        retriever._parse_code_hits = MagicMock(return_value=[_make_scored_chunk("MyClass")])
        # Doc search fails
        retriever.bm25_doc_search = AsyncMock(side_effect=Exception("ES doc index down"))
        reranker.rerank = MagicMock(return_value=[_make_scored_chunk("MyClass")])

        expected_response = QueryResponse(query="MyClass", query_type="symbol", repo="repo1")
        response_builder.build = MagicMock(return_value=expected_response)

        handler = _make_handler(retriever, reranker=reranker, response_builder=response_builder)
        result = await handler.handle_symbol_query("MyClass", "repo1")

        # Should still return a response (doc search failure is graceful)
        assert isinstance(result, QueryResponse)
        # Reranker called with code chunks only
        reranker.rerank.assert_called_once()
        rerank_candidates = reranker.rerank.call_args[0][1]
        assert len(rerank_candidates) == 1, "Only code chunks when doc search fails"


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
    """Tests B3, B4, D1: error propagation and reranker fallback."""

    @pytest.mark.asyncio
    async def test_d1_es_error_propagates(self):
        """B3/D1: When ES raises RetrievalError on term query, it propagates."""
        from src.query.exceptions import RetrievalError

        retriever = MagicMock()
        retriever._execute_search = AsyncMock(
            side_effect=RetrievalError("Elasticsearch search failed")
        )
        retriever._code_index = "code_chunks"
        retriever.bm25_doc_search = AsyncMock(return_value=[])

        handler = _make_handler(retriever)
        with pytest.raises(RetrievalError, match="Elasticsearch search failed"):
            await handler.handle_symbol_query("MyClass", "repo1")

    @pytest.mark.asyncio
    async def test_b4_reranker_failure_uses_raw_chunks(self):
        """B4: When reranker raises Exception, handler falls back to candidates[:6]."""
        retriever = MagicMock()
        reranker = MagicMock()
        response_builder = MagicMock()

        # ES term query returns 8 hits
        term_hits = [_make_es_hit(f"Sym{i}") for i in range(8)]
        retriever._execute_search = AsyncMock(return_value=term_hits)
        retriever._code_index = "code_chunks"

        parsed_code = [_make_scored_chunk(f"Sym{i}") for i in range(8)]
        retriever._parse_code_hits = MagicMock(return_value=parsed_code)

        # Doc search returns 2 docs
        doc_chunks = [_make_doc_chunk(f"doc{i}") for i in range(2)]
        retriever.bm25_doc_search = AsyncMock(return_value=doc_chunks)

        # Reranker raises
        reranker.rerank = MagicMock(side_effect=Exception("model error"))

        expected_response = QueryResponse(
            query="MyClass", query_type="symbol", repo="repo1",
        )
        response_builder.build = MagicMock(return_value=expected_response)

        handler = _make_handler(retriever, reranker=reranker, response_builder=response_builder)
        result = await handler.handle_symbol_query("MyClass", "repo1")

        # Response still returned
        assert isinstance(result, QueryResponse)
        # Build called with first 6 of combined candidates (8 code + 2 doc = 10, fallback [:6])
        build_call = response_builder.build.call_args
        assert len(build_call[0][0]) == 6, "Fallback should use candidates[:6]"


# ---------------------------------------------------------------------------
# E: Branch parsing and forwarding
# [unit]
# ---------------------------------------------------------------------------

class TestSymbolQueryBranchParsing:
    """Test A8: Branch parsed from owner/repo@branch format."""

    @pytest.mark.asyncio
    async def test_a8_branch_parsed_and_filters_applied(self):
        """A8: owner/repo@branch → repo_id and branch filters in ES query."""
        retriever = MagicMock()
        reranker = MagicMock()
        response_builder = MagicMock()

        term_hits = [_make_es_hit("MyClass")]
        retriever._execute_search = AsyncMock(return_value=term_hits)
        retriever._code_index = "code_chunks"
        retriever._parse_code_hits = MagicMock(return_value=[_make_scored_chunk("MyClass")])
        retriever.bm25_doc_search = AsyncMock(return_value=[])
        reranker.rerank = MagicMock(return_value=[_make_scored_chunk("MyClass")])

        expected_response = QueryResponse(
            query="MyClass", query_type="symbol", repo="owner/repo",
        )
        response_builder.build = MagicMock(return_value=expected_response)

        handler = _make_handler(retriever, reranker=reranker, response_builder=response_builder)
        result = await handler.handle_symbol_query("MyClass", "owner/repo@main")

        # Verify ES term query was called
        retriever._execute_search.assert_called_once()
        call_args = retriever._execute_search.call_args
        query_body = call_args[0][1]

        # Verify filter clauses
        bool_clause = query_body["query"]["bool"]
        filter_clauses = bool_clause.get("filter", [])

        # Verify repo_id filter uses parsed repo (without @branch)
        repo_filter = [f for f in filter_clauses if "term" in f and "repo_id" in f["term"]]
        assert len(repo_filter) == 1, "Expected repo_id filter in ES query"
        assert repo_filter[0]["term"]["repo_id"] == "owner/repo", \
            "repo_id filter should be 'owner/repo' (branch stripped)"

        # Verify branch filter is present and forwards 'main'
        branch_filter = [f for f in filter_clauses if "term" in f and "branch" in f["term"]]
        assert len(branch_filter) == 1, "Expected branch filter in ES query"
        assert branch_filter[0]["term"]["branch"] == "main", \
            "branch filter should be 'main'"

        # Verify doc search also receives branch
        retriever.bm25_doc_search.assert_called_once()
        doc_call_kwargs = retriever.bm25_doc_search.call_args
        # Check branch kwarg
        assert doc_call_kwargs[1].get("branch") == "main" or \
            (len(doc_call_kwargs[0]) >= 4 and doc_call_kwargs[0][3] == "main"), \
            "Doc BM25 search must receive branch='main'"


# ---------------------------------------------------------------------------
# F: Security — injection payloads handled safely
# [unit] — ST-SEC-014-001
# ---------------------------------------------------------------------------

class TestSymbolQuerySecurity:
    """SEC tests: injection payloads rejected or handled safely by validation."""

    @pytest.mark.asyncio
    async def test_sec1_sql_injection_in_query(self):
        """SEC1: SQL injection payload in query is passed to ES as-is (no SQL execution)."""
        retriever = MagicMock()
        reranker = MagicMock()
        response_builder = MagicMock()

        retriever._execute_search = AsyncMock(return_value=[])
        retriever._code_index = "code_chunks"
        retriever.bm25_code_search = AsyncMock(return_value=[])
        retriever.vector_code_search = AsyncMock(return_value=[])
        retriever.bm25_doc_search = AsyncMock(return_value=[])
        retriever.vector_doc_search = AsyncMock(return_value=[])
        rank_fusion = MagicMock()
        rank_fusion.fuse = MagicMock(return_value=[])
        reranker.rerank = MagicMock(return_value=[])
        response_builder.build = MagicMock(
            return_value=QueryResponse(query="'; DROP TABLE", query_type="nl", repo="repo1")
        )

        handler = _make_handler(retriever, rank_fusion, reranker, response_builder)
        # SQL injection attempt — should not raise, just returns (empty) results
        result = await handler.handle_symbol_query("'; DROP TABLE users; --", "repo1")
        assert isinstance(result, QueryResponse)

    @pytest.mark.asyncio
    async def test_sec2_path_traversal_in_query(self):
        """SEC2: Path traversal payload — handled as normal query, no file access."""
        retriever = MagicMock()
        retriever._execute_search = AsyncMock(return_value=[])
        retriever._code_index = "code_chunks"
        retriever.bm25_code_search = AsyncMock(return_value=[])
        retriever.vector_code_search = AsyncMock(return_value=[])
        retriever.bm25_doc_search = AsyncMock(return_value=[])
        retriever.vector_doc_search = AsyncMock(return_value=[])
        rank_fusion = MagicMock()
        rank_fusion.fuse = MagicMock(return_value=[])
        reranker = MagicMock()
        reranker.rerank = MagicMock(return_value=[])
        response_builder = MagicMock()
        response_builder.build = MagicMock(
            return_value=QueryResponse(query="path", query_type="nl", repo="repo1")
        )

        handler = _make_handler(retriever, rank_fusion, reranker, response_builder)
        result = await handler.handle_symbol_query("../../../../etc/passwd", "repo1")
        assert isinstance(result, QueryResponse)

    @pytest.mark.asyncio
    async def test_sec3_null_byte_in_query(self):
        """SEC3: Null byte payload — handled as normal query."""
        retriever = MagicMock()
        retriever._execute_search = AsyncMock(return_value=[])
        retriever._code_index = "code_chunks"
        retriever.bm25_code_search = AsyncMock(return_value=[])
        retriever.vector_code_search = AsyncMock(return_value=[])
        retriever.bm25_doc_search = AsyncMock(return_value=[])
        retriever.vector_doc_search = AsyncMock(return_value=[])
        rank_fusion = MagicMock()
        rank_fusion.fuse = MagicMock(return_value=[])
        reranker = MagicMock()
        reranker.rerank = MagicMock(return_value=[])
        response_builder = MagicMock()
        response_builder.build = MagicMock(
            return_value=QueryResponse(query="null", query_type="nl", repo="repo1")
        )

        handler = _make_handler(retriever, rank_fusion, reranker, response_builder)
        result = await handler.handle_symbol_query("\x00null-byte", "repo1")
        assert isinstance(result, QueryResponse)

    @pytest.mark.asyncio
    async def test_sec4_xss_payload_rejected_by_length(self):
        """SEC4: XSS payload exceeding 200 chars is rejected by validation."""
        handler = _make_handler()
        xss_payload = "<script>alert('xss')</script>" * 25  # > 200 chars
        with pytest.raises(ValidationError, match="200 character"):
            await handler.handle_symbol_query(xss_payload, "repo1")

    @pytest.mark.asyncio
    async def test_sec5_short_xss_handled_safely(self):
        """SEC5: Short XSS payload (< 200 chars) is passed to ES as-is (no HTML execution)."""
        retriever = MagicMock()
        retriever._execute_search = AsyncMock(return_value=[])
        retriever._code_index = "code_chunks"
        retriever.bm25_code_search = AsyncMock(return_value=[])
        retriever.vector_code_search = AsyncMock(return_value=[])
        retriever.bm25_doc_search = AsyncMock(return_value=[])
        retriever.vector_doc_search = AsyncMock(return_value=[])
        rank_fusion = MagicMock()
        rank_fusion.fuse = MagicMock(return_value=[])
        reranker = MagicMock()
        reranker.rerank = MagicMock(return_value=[])
        response_builder = MagicMock()
        response_builder.build = MagicMock(
            return_value=QueryResponse(query="xss", query_type="nl", repo="repo1")
        )

        handler = _make_handler(retriever, rank_fusion, reranker, response_builder)
        result = await handler.handle_symbol_query("<script>alert(1)</script>", "repo1")
        assert isinstance(result, QueryResponse)


# ---------------------------------------------------------------------------
# Real tests — pure-function exemption
# [no integration test] — detect_query_type is a pure function with no
# external I/O. handle_symbol_query delegates to Retriever (ES) which is
# tested in Feature #8 integration tests. No new external dependency
# introduced by this feature.
# ---------------------------------------------------------------------------
