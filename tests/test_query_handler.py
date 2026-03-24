"""Tests for Natural Language Query Handler (Feature #13).

Categories:
  - Happy path: T1-T5, T17-T20, T25-T27
  - Error handling: T6-T8, T10-T13, T21, T24, T28
  - Boundary: T9, T14-T16, T19, T23
  - Security: N/A — input validation tested via error handling

# [no integration test] — QueryHandler orchestrates mocked Retriever/RankFusion/Reranker/ResponseBuilder;
# external dependencies (ES, Qdrant) are tested in Features #8/#9.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.query.exceptions import RetrievalError
from src.query.response_models import QueryResponse
from src.query.scored_chunk import ScoredChunk
from src.shared.exceptions import ValidationError


def _make_chunks(n: int, content_type: str = "code") -> list[ScoredChunk]:
    """Create n ScoredChunks with distinct IDs."""
    return [
        ScoredChunk(
            chunk_id=f"chunk-{content_type}-{i}",
            content_type=content_type,
            repo_id="test-repo",
            file_path=f"src/file_{i}.py",
            content=f"content {i}",
            score=float(10 - i),
            language="python" if content_type == "code" else None,
            chunk_type="function" if content_type == "code" else None,
            symbol=f"func_{i}" if content_type == "code" else None,
        )
        for i in range(n)
    ]


def _make_response(**kwargs) -> QueryResponse:
    """Create a basic QueryResponse."""
    defaults = dict(
        query="test",
        query_type="nl",
        repo="test-repo",
        code_results=[],
        doc_results=[],
    )
    defaults.update(kwargs)
    return QueryResponse(**defaults)


@pytest.fixture
def handler():
    """Build a QueryHandler with mocked dependencies."""
    from src.query.query_handler import QueryHandler

    retriever = MagicMock()
    retriever.bm25_code_search = AsyncMock(return_value=_make_chunks(5, "code"))
    retriever.vector_code_search = AsyncMock(return_value=_make_chunks(5, "code"))
    retriever.bm25_doc_search = AsyncMock(return_value=_make_chunks(3, "doc"))
    retriever.vector_doc_search = AsyncMock(return_value=_make_chunks(3, "doc"))
    retriever._execute_search = AsyncMock(return_value=[])
    retriever._parse_code_hits = MagicMock(return_value=[])
    retriever._code_index = "code_chunks"

    rank_fusion = MagicMock()
    rank_fusion.fuse = MagicMock(return_value=_make_chunks(6, "code"))

    reranker = MagicMock()
    reranker.rerank = MagicMock(return_value=_make_chunks(6, "code"))

    response_builder = MagicMock()
    response_builder.build = MagicMock(return_value=_make_response())

    qh = QueryHandler(
        retriever=retriever,
        rank_fusion=rank_fusion,
        reranker=reranker,
        response_builder=response_builder,
        search_timeout=0.2,
        pipeline_timeout=1.0,
    )
    return qh


# --- T1: Happy path — full pipeline ---

# [unit]
@pytest.mark.asyncio
async def test_handle_nl_query_full_pipeline(handler):
    """VS-1: NL query runs 4-way parallel retrieval, RRF fusion, rerank, build."""
    response = await handler.handle_nl_query("how to use grpc java interceptor", "test-repo")

    # Verify all 4 retrieval methods were called
    handler._retriever.bm25_code_search.assert_called_once()
    handler._retriever.vector_code_search.assert_called_once()
    handler._retriever.bm25_doc_search.assert_called_once()
    handler._retriever.vector_doc_search.assert_called_once()

    # Verify fusion, rerank, build were called
    handler._rank_fusion.fuse.assert_called_once()
    handler._reranker.rerank.assert_called_once()
    handler._response_builder.build.assert_called_once()


# --- T2: Happy path — no identifiers, only 4 lists ---

# [unit]
@pytest.mark.asyncio
async def test_handle_nl_query_no_identifiers(handler):
    """No identifiers in query → only 4 lists to fuse, no symbol boost."""
    await handler.handle_nl_query("how to configure timeout", "test-repo")

    # fuse should be called with exactly 4 lists (no 5th symbol boost)
    call_args = handler._rank_fusion.fuse.call_args
    # positional args are the result lists
    assert len(call_args.args) == 4


# --- T3: Happy path — extract PascalCase identifier ---

# [unit]
def test_extract_identifiers_pascal_case():
    """VS-3: 'AuthService' extracted from NL query."""
    from src.query.query_handler import QueryHandler

    qh = QueryHandler.__new__(QueryHandler)
    ids = qh._extract_identifiers("how does AuthService validate tokens")
    assert "AuthService" in ids


# --- T4: Happy path — symbol boost weight applied ---

# [unit]
@pytest.mark.asyncio
async def test_symbol_boost_weight_applied(handler):
    """VS-3: Symbol boost results scaled by weight 0.3 before RRF."""
    # Return chunks with score=10.0 from symbol boost
    boost_chunks = _make_chunks(2, "code")
    for c in boost_chunks:
        c.score = 10.0
    handler._retriever._execute_search = AsyncMock(
        return_value=[{"_id": "b1", "_score": 10.0, "_source": {
            "repo_id": "test-repo", "file_path": "f.py", "content": "x",
            "language": "python", "chunk_type": "function", "symbol": "AuthService",
        }}]
    )
    handler._retriever._parse_code_hits = MagicMock(return_value=boost_chunks)

    await handler.handle_nl_query("how does AuthService work", "test-repo")

    # fuse should be called with 5 lists (4 primary + 1 symbol boost)
    call_args = handler._rank_fusion.fuse.call_args
    assert len(call_args.args) == 5

    # The 5th list (symbol boost) should have scaled scores
    boosted_list = call_args.args[4]
    for chunk in boosted_list:
        assert chunk.score == pytest.approx(10.0 * 0.3)


# --- T5: Happy path — response query_type is "nl" ---

# [unit]
@pytest.mark.asyncio
async def test_response_query_type_nl(handler):
    """Response has query_type='nl' and repo matches input."""
    await handler.handle_nl_query("test query", "my-repo")

    build_call = handler._response_builder.build.call_args
    assert build_call.args[1] == "test query"  # query
    assert build_call.args[2] == "nl"  # query_type
    assert build_call.args[3] == "my-repo"  # repo


# --- T6: Error — empty query ---

# [unit]
@pytest.mark.asyncio
async def test_empty_query_raises_validation_error(handler):
    """VS-2: Empty string raises ValidationError."""
    with pytest.raises(ValidationError, match="empty"):
        await handler.handle_nl_query("", "test-repo")


# --- T7: Error — whitespace query ---

# [unit]
@pytest.mark.asyncio
async def test_whitespace_query_raises_validation_error(handler):
    """VS-2: Whitespace-only raises ValidationError."""
    with pytest.raises(ValidationError, match="empty"):
        await handler.handle_nl_query("   ", "test-repo")


# --- T8: Error — query exceeds 500 chars ---

# [unit]
@pytest.mark.asyncio
async def test_query_exceeds_500_chars_raises(handler):
    """FR-011 AC-3: Query >500 chars raises ValidationError."""
    with pytest.raises(ValidationError, match="500"):
        await handler.handle_nl_query("a" * 501, "test-repo")


# --- T9: Boundary — query exactly 500 chars ---

# [unit]
@pytest.mark.asyncio
async def test_query_exactly_500_chars_valid(handler):
    """Boundary: 500 chars accepted, no exception."""
    response = await handler.handle_nl_query("a" * 500, "test-repo")
    assert response is not None


# --- T10: Error — all 4 retrievals fail ---

# [unit]
@pytest.mark.asyncio
async def test_all_retrieval_fail_raises_retrieval_error(handler):
    """VS-4: All 4 primary searches fail → RetrievalError."""
    handler._retriever.bm25_code_search = AsyncMock(side_effect=RetrievalError("ES down"))
    handler._retriever.vector_code_search = AsyncMock(side_effect=RetrievalError("Qdrant down"))
    handler._retriever.bm25_doc_search = AsyncMock(side_effect=RetrievalError("ES down"))
    handler._retriever.vector_doc_search = AsyncMock(side_effect=RetrievalError("Qdrant down"))

    with pytest.raises(RetrievalError, match="all retrieval"):
        await handler.handle_nl_query("test query", "test-repo")


# --- T11: Error — 3 timeout, 1 succeeds → degraded ---

# [unit]
@pytest.mark.asyncio
async def test_three_fail_one_succeeds_degraded(handler):
    """VS-4: 3 of 4 timeout, 1 succeeds → degraded=True."""
    handler._retriever.bm25_code_search = AsyncMock(return_value=_make_chunks(3, "code"))
    handler._retriever.vector_code_search = AsyncMock(side_effect=asyncio.TimeoutError())
    handler._retriever.bm25_doc_search = AsyncMock(side_effect=asyncio.TimeoutError())
    handler._retriever.vector_doc_search = AsyncMock(side_effect=asyncio.TimeoutError())

    response = await handler.handle_nl_query("test query", "test-repo")
    assert response.degraded is True


# --- T12: Error — 1 timeout, 3 succeed → degraded ---

# [unit]
@pytest.mark.asyncio
async def test_one_timeout_sets_degraded(handler):
    """1 retrieval times out → degraded=True even though 3 succeed."""
    handler._retriever.bm25_code_search = AsyncMock(side_effect=asyncio.TimeoutError())

    response = await handler.handle_nl_query("test query", "test-repo")
    assert response.degraded is True


# --- T13: Error — symbol boost fails, still returns response ---

# [unit]
@pytest.mark.asyncio
async def test_symbol_boost_failure_ignored(handler):
    """Symbol boost exception doesn't crash pipeline."""
    handler._retriever._execute_search = AsyncMock(side_effect=RetrievalError("boom"))

    response = await handler.handle_nl_query("how does AuthService work", "test-repo")
    assert response is not None


# --- T14: Boundary — single char query ---

# [unit]
@pytest.mark.asyncio
async def test_single_char_query_valid(handler):
    """Boundary: 'a' is a valid query."""
    response = await handler.handle_nl_query("a", "test-repo")
    assert response is not None


# --- T15: Boundary — languages=None ---

# [unit]
@pytest.mark.asyncio
async def test_languages_none_accepted(handler):
    """Boundary: languages=None works."""
    await handler.handle_nl_query("test", "test-repo", languages=None)
    call = handler._retriever.bm25_code_search.call_args
    assert call.kwargs.get("languages") is None or (len(call.args) >= 3 and call.args[2] is None)


# --- T16: Boundary — languages=[] ---

# [unit]
@pytest.mark.asyncio
async def test_languages_empty_list_accepted(handler):
    """Boundary: languages=[] works."""
    await handler.handle_nl_query("test", "test-repo", languages=[])
    # Should not crash
    handler._retriever.bm25_code_search.assert_called_once()


# --- T17: Happy path — dot-separated identifier ---

# [unit]
def test_extract_dot_separated():
    """Extracts 'UserService.getById' from NL query."""
    from src.query.query_handler import QueryHandler

    qh = QueryHandler.__new__(QueryHandler)
    ids = qh._extract_identifiers("how does UserService.getById work")
    assert any("UserService.getById" in i for i in ids)


# --- T18: Happy path — snake_case identifier ---

# [unit]
def test_extract_snake_case():
    """Extracts 'get_user_name' from NL query."""
    from src.query.query_handler import QueryHandler

    qh = QueryHandler.__new__(QueryHandler)
    ids = qh._extract_identifiers("check the get_user_name function")
    assert "get_user_name" in ids


# --- T19: Boundary — no identifiers found ---

# [unit]
def test_no_identifiers_returns_empty():
    """No identifiers in query → empty list."""
    from src.query.query_handler import QueryHandler

    qh = QueryHandler.__new__(QueryHandler)
    ids = qh._extract_identifiers("how to configure timeout")
    assert ids == []


# --- T20: Happy path — detect_query_type stub ---

# [unit]
def test_detect_query_type_returns_nl():
    """Stub returns 'nl'."""
    from src.query.query_handler import QueryHandler

    qh = QueryHandler.__new__(QueryHandler)
    assert qh.detect_query_type("anything") == "nl"


# --- T21: Error — all primary fail, symbol boost succeeds → still raises ---

# [unit]
@pytest.mark.asyncio
async def test_all_primary_fail_symbol_succeeds_still_raises(handler):
    """Symbol boost success alone is insufficient — still raises RetrievalError."""
    handler._retriever.bm25_code_search = AsyncMock(side_effect=RetrievalError("fail"))
    handler._retriever.vector_code_search = AsyncMock(side_effect=RetrievalError("fail"))
    handler._retriever.bm25_doc_search = AsyncMock(side_effect=RetrievalError("fail"))
    handler._retriever.vector_doc_search = AsyncMock(side_effect=RetrievalError("fail"))
    # Symbol boost returns results
    handler._retriever._execute_search = AsyncMock(return_value=[])
    handler._retriever._parse_code_hits = MagicMock(return_value=_make_chunks(2))

    with pytest.raises(RetrievalError, match="all retrieval"):
        await handler.handle_nl_query("how does AuthService work", "test-repo")


# --- T22: Happy path — gather uses return_exceptions ---

# [unit]
@pytest.mark.asyncio
async def test_gather_handles_exceptions_without_crashing(handler):
    """Exceptions from individual searches don't abort the whole gather."""
    handler._retriever.bm25_code_search = AsyncMock(side_effect=RetrievalError("ES fail"))
    # Other 3 succeed
    response = await handler.handle_nl_query("test query", "test-repo")
    assert response is not None


# --- T23: Boundary — all 4 return empty lists ---

# [unit]
@pytest.mark.asyncio
async def test_all_retrieval_return_empty_lists(handler):
    """All 4 paths return empty [] → empty response, no error."""
    handler._retriever.bm25_code_search = AsyncMock(return_value=[])
    handler._retriever.vector_code_search = AsyncMock(return_value=[])
    handler._retriever.bm25_doc_search = AsyncMock(return_value=[])
    handler._retriever.vector_doc_search = AsyncMock(return_value=[])
    handler._rank_fusion.fuse = MagicMock(return_value=[])
    handler._reranker.rerank = MagicMock(return_value=[])

    response = await handler.handle_nl_query("test", "test-repo")
    assert response is not None


# --- T24: Error — 2 primary + symbol boost fail ---

# [unit]
@pytest.mark.asyncio
async def test_multiple_failures_with_symbol_boost_timeout(handler):
    """2 primary + boost fail → degraded response from remaining 2."""
    handler._retriever.bm25_code_search = AsyncMock(side_effect=asyncio.TimeoutError())
    handler._retriever.vector_code_search = AsyncMock(side_effect=asyncio.TimeoutError())
    handler._retriever._execute_search = AsyncMock(side_effect=RetrievalError("boom"))

    response = await handler.handle_nl_query("how does AuthService work", "test-repo")
    assert response.degraded is True


# --- T29: Error — pipeline_timeout enforced ---

# [unit]
@pytest.mark.asyncio
async def test_pipeline_timeout_returns_degraded():
    """VS-4: Pipeline exceeding pipeline_timeout returns degraded=True."""
    from src.query.query_handler import QueryHandler

    async def slow_search(*args, **kwargs):
        await asyncio.sleep(5)  # Much longer than pipeline_timeout
        return _make_chunks(3, "code")

    retriever = MagicMock()
    retriever.bm25_code_search = slow_search
    retriever.vector_code_search = slow_search
    retriever.bm25_doc_search = slow_search
    retriever.vector_doc_search = slow_search

    rank_fusion = MagicMock()
    rank_fusion.fuse = MagicMock(return_value=[])
    reranker = MagicMock()
    reranker.rerank = MagicMock(return_value=[])
    response_builder = MagicMock()
    response_builder.build = MagicMock(return_value=_make_response())

    qh = QueryHandler(
        retriever=retriever,
        rank_fusion=rank_fusion,
        reranker=reranker,
        response_builder=response_builder,
        search_timeout=10.0,  # Individual timeout high (won't trigger)
        pipeline_timeout=0.05,  # Overall pipeline very short
    )

    response = await qh.handle_nl_query("test query", "test-repo")
    assert response.degraded is True


# --- T25: Happy path — boost weight scaling value ---

# [unit]
def test_apply_boost_weight_scales_scores():
    """Chunk scores scaled by weight 0.3."""
    from src.query.query_handler import QueryHandler

    qh = QueryHandler.__new__(QueryHandler)
    chunks = _make_chunks(2, "code")
    chunks[0] = replace(chunks[0], score=10.0)
    chunks[1] = replace(chunks[1], score=5.0)

    scaled = qh._apply_boost_weight(chunks, weight=0.3)
    assert scaled[0].score == pytest.approx(3.0)
    assert scaled[1].score == pytest.approx(1.5)


# --- T26: Happy path — reranker called with top_k=6 ---

# [unit]
@pytest.mark.asyncio
async def test_reranker_called_with_topk_6(handler):
    """Reranker.rerank() called with top_k=6."""
    await handler.handle_nl_query("test", "test-repo")
    call = handler._reranker.rerank.call_args
    assert call.kwargs.get("top_k") == 6 or (len(call.args) >= 3 and call.args[2] == 6)


# --- T27: Happy path — fusion called with top_k=50 ---

# [unit]
@pytest.mark.asyncio
async def test_fusion_called_with_topk_50(handler):
    """RankFusion.fuse() called with top_k=50."""
    await handler.handle_nl_query("test", "test-repo")
    call = handler._rank_fusion.fuse.call_args
    assert call.kwargs.get("top_k") == 50


# --- T28: Error — ValueError from retriever handled ---

# [unit]
@pytest.mark.asyncio
async def test_value_error_from_retriever_handled(handler):
    """ValueError from retriever treated as failure, degraded=True."""
    handler._retriever.bm25_code_search = AsyncMock(side_effect=ValueError("bad query"))

    response = await handler.handle_nl_query("test query", "test-repo")
    assert response.degraded is True


# =============================================================================
# Wave 5: Branch parsing and forwarding tests (Feature #13 — VS-5, FR-011)
# =============================================================================


# --- T30: Happy path — branch parsed from repo and forwarded to retriever ---

# [unit]
@pytest.mark.asyncio
async def test_repo_branch_parsing_forwarded(handler):
    """VS-5: repo='google/gson@main' → branch='main' forwarded to all 4 retriever calls."""
    response = await handler.handle_nl_query("how to use grpc java interceptor", "google/gson@main")

    # Verify all 4 retriever calls received branch='main'
    for method_name in ("bm25_code_search", "vector_code_search", "bm25_doc_search", "vector_doc_search"):
        method = getattr(handler._retriever, method_name)
        method.assert_called_once()
        call_kwargs = method.call_args.kwargs
        assert call_kwargs.get("branch") == "main", (
            f"{method_name} was not called with branch='main', got kwargs={call_kwargs}"
        )

    # Verify repo_id was stripped of @branch — first positional arg to bm25_code_search is query, second is repo_id
    bm25_call = handler._retriever.bm25_code_search.call_args
    assert bm25_call.args[1] == "google/gson", (
        f"repo_id should be 'google/gson' without @branch, got {bm25_call.args[1]}"
    )


# --- T31: Happy path — no branch (no @) → branch=None forwarded ---

# [unit]
@pytest.mark.asyncio
async def test_repo_no_branch_forwards_none(handler):
    """repo='google/gson' (no @) → branch=None explicitly forwarded to all retriever calls."""
    await handler.handle_nl_query("test query", "google/gson")

    for method_name in ("bm25_code_search", "vector_code_search", "bm25_doc_search", "vector_doc_search"):
        method = getattr(handler._retriever, method_name)
        call_kwargs = method.call_args.kwargs
        # branch must be EXPLICITLY passed as a kwarg (not just absent)
        assert "branch" in call_kwargs, (
            f"{method_name} must explicitly pass branch= kwarg, got kwargs={call_kwargs}"
        )
        assert call_kwargs["branch"] is None


# --- T32: Error — empty repo raises ValidationError ---

# [unit]
@pytest.mark.asyncio
async def test_empty_repo_raises_validation_error(handler):
    """Empty repo string raises ValidationError."""
    with pytest.raises(ValidationError, match="repo"):
        await handler.handle_nl_query("valid query", "")


# --- T33: Error — whitespace-only repo raises ValidationError ---

# [unit]
@pytest.mark.asyncio
async def test_whitespace_repo_raises_validation_error(handler):
    """Whitespace-only repo string raises ValidationError."""
    with pytest.raises(ValidationError, match="repo"):
        await handler.handle_nl_query("valid query", "   ")


# --- T34: Boundary — repo with trailing @ → branch=None ---

# [unit]
@pytest.mark.asyncio
async def test_repo_trailing_at_branch_is_none(handler):
    """repo='google/gson@' → branch=None (empty branch treated as None)."""
    await handler.handle_nl_query("test query", "google/gson@")

    bm25_call = handler._retriever.bm25_code_search.call_args
    assert bm25_call.args[1] == "google/gson"
    assert bm25_call.kwargs.get("branch") is None


# --- T35: Boundary — repo with multiple @ splits on last ---

# [unit]
@pytest.mark.asyncio
async def test_repo_multiple_at_splits_on_last(handler):
    """repo='org/repo@feature@fix' → repo_id='org/repo@feature', branch='fix'."""
    await handler.handle_nl_query("test query", "org/repo@feature@fix")

    bm25_call = handler._retriever.bm25_code_search.call_args
    assert bm25_call.args[1] == "org/repo@feature"
    assert bm25_call.kwargs.get("branch") == "fix"


# --- T36: Happy path — _parse_repo returns correct tuple ---

# [unit]
def test_parse_repo_with_branch():
    """_parse_repo('owner/repo@main') returns ('owner/repo', 'main')."""
    from src.query.query_handler import QueryHandler

    qh = QueryHandler.__new__(QueryHandler)
    repo_id, branch = qh._parse_repo("owner/repo@main")
    assert repo_id == "owner/repo"
    assert branch == "main"


# [unit]
def test_parse_repo_without_branch():
    """_parse_repo('owner/repo') returns ('owner/repo', None)."""
    from src.query.query_handler import QueryHandler

    qh = QueryHandler.__new__(QueryHandler)
    repo_id, branch = qh._parse_repo("owner/repo")
    assert repo_id == "owner/repo"
    assert branch is None


# --- T37: Error — reranker failure with branch still falls back ---

# [unit]
@pytest.mark.asyncio
async def test_reranker_failure_with_branch_falls_back(handler):
    """Reranker failure with branch param → falls back to fused[:6], degraded=True, branch forwarded."""
    handler._reranker.rerank = MagicMock(side_effect=RuntimeError("model crash"))
    handler._rank_fusion.fuse = MagicMock(return_value=_make_chunks(10, "code"))

    response = await handler.handle_nl_query("test query", "google/gson@main")
    assert response.degraded is True

    # Also verify branch was forwarded (Wave 5)
    bm25_call = handler._retriever.bm25_code_search.call_args
    assert bm25_call.args[1] == "google/gson"
    assert bm25_call.kwargs.get("branch") == "main"


# --- T38: Happy path — language_filter.validate() is called when set ---

# [unit]
@pytest.mark.asyncio
async def test_language_filter_validate_called():
    """When language_filter is provided, validate() is called with the given languages."""
    from src.query.query_handler import QueryHandler

    retriever = MagicMock()
    retriever.bm25_code_search = AsyncMock(return_value=_make_chunks(5, "code"))
    retriever.vector_code_search = AsyncMock(return_value=_make_chunks(5, "code"))
    retriever.bm25_doc_search = AsyncMock(return_value=_make_chunks(3, "doc"))
    retriever.vector_doc_search = AsyncMock(return_value=_make_chunks(3, "doc"))
    retriever._execute_search = AsyncMock(return_value=[])
    retriever._parse_code_hits = MagicMock(return_value=[])
    retriever._code_index = "code_chunks"

    rank_fusion = MagicMock()
    rank_fusion.fuse = MagicMock(return_value=_make_chunks(6, "code"))

    reranker = MagicMock()
    reranker.rerank = MagicMock(return_value=_make_chunks(6, "code"))

    response_builder = MagicMock()
    response_builder.build = MagicMock(return_value=_make_response())

    language_filter = MagicMock()
    language_filter.validate = MagicMock(return_value=["python"])

    qh = QueryHandler(
        retriever=retriever,
        rank_fusion=rank_fusion,
        reranker=reranker,
        response_builder=response_builder,
        language_filter=language_filter,
        search_timeout=0.2,
        pipeline_timeout=1.0,
    )

    await qh.handle_nl_query("how to parse JSON", "test-repo", languages=["python"])
    language_filter.validate.assert_called_once_with(["python"])


# --- T39: Branch forwarded to symbol boost search ---

# [unit]
@pytest.mark.asyncio
async def test_symbol_boost_receives_branch(handler):
    """VS-5: Symbol boost search receives branch when repo has @branch."""
    # Make symbol boost return results so we can verify filter clauses
    handler._retriever._execute_search = AsyncMock(return_value=[
        {"_id": "b1", "_score": 5.0, "_source": {
            "repo_id": "google/gson", "file_path": "f.py", "content": "x",
            "language": "python", "chunk_type": "function", "symbol": "AuthService",
        }}
    ])
    handler._retriever._parse_code_hits = MagicMock(return_value=_make_chunks(1))

    await handler.handle_nl_query("how does AuthService work", "google/gson@main")

    # Verify _execute_search was called with branch filter in the ES query
    es_call = handler._retriever._execute_search.call_args
    query_body = es_call.args[1]
    filter_clauses = query_body["query"]["bool"].get("filter", [])
    branch_filters = [f for f in filter_clauses if "branch" in f.get("term", {})]
    assert len(branch_filters) == 1, f"Expected branch filter, got filters: {filter_clauses}"
    assert branch_filters[0]["term"]["branch"] == "main"


# --- T40: Security — malicious inputs handled safely ---

# [unit]
@pytest.mark.asyncio
async def test_security_malicious_inputs_handled(handler):
    """SEC: SQL injection, XSS, path traversal, null bytes handled safely."""
    malicious_inputs = [
        "'; DROP TABLE users; --",
        "<script>alert('xss')</script>",
        "../../etc/passwd",
        "query\x00injection",
        "query\r\nX-Injected: true",
    ]
    for payload in malicious_inputs:
        # Should not raise unexpected exceptions — only ValidationError or normal response
        try:
            response = await handler.handle_nl_query(payload, "test-repo")
            # If it returns a response, verify it's a valid QueryResponse
            assert response is not None
            assert response.query_type == "nl"
        except Exception as exc:
            # Only ValidationError is acceptable
            from src.shared.exceptions import ValidationError
            assert isinstance(exc, ValidationError), (
                f"Unexpected exception for payload {payload!r}: {type(exc).__name__}: {exc}"
            )
