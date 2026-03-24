"""Tests for Language Filter (feature #20).

Categories:
  - Happy path: T_A1-T_A6 — valid language validation and normalization
  - Error handling: T_B1-T_B3 — unsupported language values raise ValidationError
  - Boundary: T_C1-T_C4 — None, empty list, whitespace, single-char language
  - Integration: T_D1-T_D3 — QueryHandler wiring, endpoint 400 response
  - Security: N/A — input sanitization tested via error handling category

# [no integration test] — LanguageFilter is a pure-function utility with no external I/O;
# it validates language strings against a hardcoded set. No DB, network, or file system access.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.query.language_filter import SUPPORTED_LANGUAGES, LanguageFilter
from src.shared.exceptions import ValidationError


@pytest.fixture
def lf() -> LanguageFilter:
    """Create a LanguageFilter instance."""
    return LanguageFilter()


# ---- Happy Path (A1-A6) ----


# [unit] — validates single supported language
def test_a1_single_language_java(lf: LanguageFilter) -> None:
    """VS-1: Given language_filter=['java'], validate returns ['java']."""
    result = lf.validate(["java"])
    assert result == ["java"]


# [unit] — validates multiple supported languages
def test_a2_multiple_languages(lf: LanguageFilter) -> None:
    """VS-2: Given ['java', 'python'], validate returns both."""
    result = lf.validate(["java", "python"])
    assert result == ["java", "python"]


# [unit] — normalizes uppercase to lowercase
def test_a3_case_normalization_mixed(lf: LanguageFilter) -> None:
    """VS-1: Given ['Java'], validate returns ['java'] (normalized)."""
    result = lf.validate(["Java"])
    assert result == ["java"]


# [unit] — normalizes fully uppercase
def test_a4_case_normalization_upper(lf: LanguageFilter) -> None:
    """Given ['TYPESCRIPT'], validate returns ['typescript']."""
    result = lf.validate(["TYPESCRIPT"])
    assert result == ["typescript"]


# [unit] — special character language c++
def test_a5_cpp_special_char(lf: LanguageFilter) -> None:
    """Given ['c++'], validate returns ['c++'] (not rejected by special chars)."""
    result = lf.validate(["c++"])
    assert result == ["c++"]


# [unit] — all 6 supported languages accepted
def test_a6_all_six_supported(lf: LanguageFilter) -> None:
    """Given all 6 supported languages, validate returns all 6."""
    all_langs = ["java", "python", "typescript", "javascript", "c", "c++"]
    result = lf.validate(all_langs)
    assert result == all_langs


# ---- Error Handling (B1-B3) ----


# [unit] — unsupported language raises ValidationError
def test_b1_unsupported_language_rust(lf: LanguageFilter) -> None:
    """VS-3: Given ['rust'], raises ValidationError mentioning 'rust' and supported languages."""
    with pytest.raises(ValidationError, match="rust"):
        lf.validate(["rust"])


# [unit] — error message lists supported languages
def test_b1_error_message_lists_supported(lf: LanguageFilter) -> None:
    """VS-3: Error message must list supported languages for user guidance."""
    with pytest.raises(ValidationError) as exc_info:
        lf.validate(["rust"])
    msg = str(exc_info.value)
    for lang in SUPPORTED_LANGUAGES:
        assert lang in msg, f"Supported language '{lang}' missing from error message"


# [unit] — mixed valid + invalid raises for the invalid one
def test_b2_mixed_valid_invalid(lf: LanguageFilter) -> None:
    """Given ['java', 'rust'], raises ValidationError mentioning 'rust'."""
    with pytest.raises(ValidationError, match="rust"):
        lf.validate(["java", "rust"])


# [unit] — multiple unsupported, all listed in error
def test_b3_multiple_unsupported(lf: LanguageFilter) -> None:
    """Given ['go', 'rust'], raises ValidationError mentioning both."""
    with pytest.raises(ValidationError) as exc_info:
        lf.validate(["go", "rust"])
    msg = str(exc_info.value)
    assert "go" in msg
    assert "rust" in msg


# ---- Boundary (C1-C4) ----


# [unit] — empty list treated as no filter
def test_c1_empty_list_returns_none(lf: LanguageFilter) -> None:
    """VS-4: Given [], validate returns None (no language filtering)."""
    result = lf.validate([])
    assert result is None


# [unit] — None input returns None
def test_c2_none_returns_none(lf: LanguageFilter) -> None:
    """VS-4: Given None, validate returns None."""
    result = lf.validate(None)
    assert result is None


# [unit] — whitespace-padded input is stripped
def test_c3_whitespace_stripped(lf: LanguageFilter) -> None:
    """Given ['  java  '], validate returns ['java'] (stripped)."""
    result = lf.validate(["  java  "])
    assert result == ["java"]


# [unit] — single-char language 'c' accepted
def test_c4_single_char_language_c(lf: LanguageFilter) -> None:
    """Given ['c'], validate returns ['c']."""
    result = lf.validate(["c"])
    assert result == ["c"]


# ---- apply_filter pass-through ----


# [unit] — apply_filter returns input unchanged
def test_apply_filter_passthrough(lf: LanguageFilter) -> None:
    """apply_filter returns validated languages unchanged."""
    result = lf.apply_filter(["java", "python"])
    assert result == ["java", "python"]


# [unit] — apply_filter with None returns None
def test_apply_filter_none(lf: LanguageFilter) -> None:
    """apply_filter with None returns None."""
    result = lf.apply_filter(None)
    assert result is None


# ---- Integration (D1-D3) ----


# [unit] — QueryHandler passes validated languages to Retriever
@pytest.mark.asyncio
async def test_d1_query_handler_passes_languages_to_retriever() -> None:
    """QueryHandler with languages=['java'] passes validated list to Retriever."""
    from src.query.query_handler import QueryHandler

    mock_retriever = MagicMock()
    mock_retriever.bm25_code_search = AsyncMock(return_value=[])
    mock_retriever.vector_code_search = AsyncMock(return_value=[])
    mock_retriever.bm25_doc_search = AsyncMock(return_value=[])
    mock_retriever.vector_doc_search = AsyncMock(return_value=[])

    mock_rank_fusion = MagicMock()
    mock_rank_fusion.fuse = MagicMock(return_value=[])

    mock_reranker = MagicMock()
    mock_reranker.rerank = MagicMock(return_value=[])

    mock_response_builder = MagicMock()
    from src.query.response_models import QueryResponse

    mock_response_builder.build = MagicMock(
        return_value=QueryResponse(
            query="timeout", query_type="nl", repo=None, code_results=[], doc_results=[]
        )
    )

    language_filter = LanguageFilter()
    handler = QueryHandler(
        retriever=mock_retriever,
        rank_fusion=mock_rank_fusion,
        reranker=mock_reranker,
        response_builder=mock_response_builder,
        language_filter=language_filter,
    )

    await handler.handle_nl_query("timeout", "test-repo", languages=["java"])

    # Verify retriever was called with validated languages
    mock_retriever.bm25_code_search.assert_called_once()
    call_kwargs = mock_retriever.bm25_code_search.call_args
    assert call_kwargs.kwargs.get("languages") == ["java"] or (
        len(call_kwargs.args) > 2 and call_kwargs.args[2] == ["java"]
    )


# [unit] — QueryHandler with empty languages passes None to Retriever
@pytest.mark.asyncio
async def test_d2_query_handler_empty_languages_passes_none() -> None:
    """QueryHandler with languages=[] → Retriever receives languages=None."""
    from src.query.query_handler import QueryHandler

    mock_retriever = MagicMock()
    mock_retriever.bm25_code_search = AsyncMock(return_value=[])
    mock_retriever.vector_code_search = AsyncMock(return_value=[])
    mock_retriever.bm25_doc_search = AsyncMock(return_value=[])
    mock_retriever.vector_doc_search = AsyncMock(return_value=[])

    mock_rank_fusion = MagicMock()
    mock_rank_fusion.fuse = MagicMock(return_value=[])

    mock_reranker = MagicMock()
    mock_reranker.rerank = MagicMock(return_value=[])

    mock_response_builder = MagicMock()
    from src.query.response_models import QueryResponse

    mock_response_builder.build = MagicMock(
        return_value=QueryResponse(
            query="timeout", query_type="nl", repo=None, code_results=[], doc_results=[]
        )
    )

    language_filter = LanguageFilter()
    handler = QueryHandler(
        retriever=mock_retriever,
        rank_fusion=mock_rank_fusion,
        reranker=mock_reranker,
        response_builder=mock_response_builder,
        language_filter=language_filter,
    )

    await handler.handle_nl_query("timeout", "test-repo", languages=[])

    # Verify retriever was called with languages=None (no filter)
    call_kwargs = mock_retriever.bm25_code_search.call_args
    langs_arg = call_kwargs.kwargs.get("languages")
    if langs_arg is None and len(call_kwargs.args) > 2:
        langs_arg = call_kwargs.args[2]
    assert langs_arg is None


# [unit] — Symbol query with unsupported language raises ValidationError
@pytest.mark.asyncio
async def test_d2b_symbol_query_validates_languages() -> None:
    """Symbol query with languages=['rust'] raises ValidationError."""
    from src.query.query_handler import QueryHandler

    mock_retriever = MagicMock()
    mock_retriever._code_index = "code_chunks"
    mock_retriever._execute_search = AsyncMock(return_value=[])

    mock_reranker = MagicMock()
    mock_response_builder = MagicMock()

    language_filter = LanguageFilter()
    handler = QueryHandler(
        retriever=mock_retriever,
        rank_fusion=MagicMock(),
        reranker=mock_reranker,
        response_builder=mock_response_builder,
        language_filter=language_filter,
    )

    with pytest.raises(ValidationError, match="rust"):
        await handler.handle_symbol_query("getUserName", languages=["rust"])


# [unit] — Symbol query with valid language adds ES filter clause
@pytest.mark.asyncio
async def test_d2c_symbol_query_passes_language_filter() -> None:
    """Symbol query with languages=['java'] adds language terms filter to ES query."""
    from src.query.query_handler import QueryHandler
    from src.query.response_models import QueryResponse
    from src.query.scored_chunk import ScoredChunk

    # Return a hit for the term query so we don't fall through to NL
    fake_hit = [{"_id": "c1", "_score": 5.0, "_source": {
        "repo_id": "r1", "file_path": "Foo.java", "content": "code",
        "language": "java", "chunk_type": "function", "symbol": "getUserName",
    }}]

    mock_retriever = MagicMock()
    mock_retriever._code_index = "code_chunks"
    mock_retriever._execute_search = AsyncMock(return_value=fake_hit)
    mock_retriever._parse_code_hits = MagicMock(return_value=[
        ScoredChunk(chunk_id="c1", content_type="code", repo_id="r1",
                    file_path="Foo.java", content="code", score=5.0,
                    language="java", symbol="getUserName")
    ])

    mock_reranker = MagicMock()
    mock_reranker.rerank = MagicMock(return_value=[])
    mock_response_builder = MagicMock()
    mock_response_builder.build = MagicMock(
        return_value=QueryResponse(
            query="getUserName", query_type="symbol", repo=None, code_results=[], doc_results=[]
        )
    )

    language_filter = LanguageFilter()
    handler = QueryHandler(
        retriever=mock_retriever,
        rank_fusion=MagicMock(),
        reranker=mock_reranker,
        response_builder=mock_response_builder,
        language_filter=language_filter,
    )

    await handler.handle_symbol_query("getUserName", languages=["java"])

    # The term query should include language filter in filter clauses
    first_call = mock_retriever._execute_search.call_args_list[0]
    es_body = first_call.args[1]
    filter_clauses = es_body["query"]["bool"].get("filter", [])
    lang_filter = [f for f in filter_clauses if "terms" in f and "language" in f["terms"]]
    assert len(lang_filter) == 1
    assert lang_filter[0]["terms"]["language"] == ["java"]


# [unit] — POST /query with unsupported language returns 400
@pytest.mark.asyncio
async def test_d3_endpoint_returns_400_for_unsupported_language() -> None:
    """POST /api/v1/query with languages=['rust'] returns HTTP 400."""
    from fastapi.testclient import TestClient

    from src.query.app import create_app
    from src.query.query_handler import QueryHandler
    from src.query.response_models import QueryResponse

    mock_retriever = MagicMock()
    mock_retriever.bm25_code_search = AsyncMock(return_value=[])
    mock_retriever.vector_code_search = AsyncMock(return_value=[])
    mock_retriever.bm25_doc_search = AsyncMock(return_value=[])
    mock_retriever.vector_doc_search = AsyncMock(return_value=[])

    mock_rank_fusion = MagicMock()
    mock_rank_fusion.fuse = MagicMock(return_value=[])
    mock_reranker = MagicMock()
    mock_reranker.rerank = MagicMock(return_value=[])
    mock_response_builder = MagicMock()
    mock_response_builder.build = MagicMock(
        return_value=QueryResponse(
            query="timeout", query_type="nl", repo=None, code_results=[], doc_results=[]
        )
    )

    language_filter = LanguageFilter()
    handler = QueryHandler(
        retriever=mock_retriever,
        rank_fusion=mock_rank_fusion,
        reranker=mock_reranker,
        response_builder=mock_response_builder,
        language_filter=language_filter,
    )

    # Mock auth to bypass authentication (AsyncMock needed for await)
    mock_auth = AsyncMock()
    mock_auth.return_value = MagicMock(role="admin")
    mock_auth.check_permission = MagicMock(return_value=True)

    app = create_app(query_handler=handler, auth_middleware=mock_auth)

    client = TestClient(app)
    response = client.post(
        "/api/v1/query",
        json={"query": "timeout", "repo_id": "test/repo", "languages": ["rust"]},
        headers={"Authorization": "Bearer test-key"},
    )

    assert response.status_code == 400
    assert "rust" in response.json()["detail"].lower()
