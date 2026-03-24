"""Tests for Repository-Scoped Query (Feature #15).

Feature #15 makes repo_id/repo optional: when None, searches span all repos.
When specified, results are restricted to that repository only.

Categories:
  - Happy path: A1-A8 — repo filtering applied/omitted correctly
  - Error handling: B1-B3 — non-existent repo returns empty results
  - Boundary: C1-C6 — query construction edge cases for None repo
  - Security: N/A — internal query component, no direct user-facing input

# [no integration test] — repo scoping is a query filter concern; ES/Qdrant
# connectivity is tested in Features #8/#9. All tests here verify filter
# construction logic with mocked backends.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, call

import pytest

from src.query.exceptions import RetrievalError
from src.query.response_models import QueryResponse
from src.query.scored_chunk import ScoredChunk
from src.shared.exceptions import ValidationError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_es_hit(chunk_id: str, score: float, source: dict) -> dict:
    """Build a single ES search hit dict."""
    return {"_id": chunk_id, "_score": score, "_source": source}


def _code_source(repo_id: str = "spring-framework", **overrides) -> dict:
    defaults = {
        "repo_id": repo_id,
        "file_path": "src/Main.java",
        "language": "java",
        "chunk_type": "function",
        "symbol": "handleTimeout",
        "signature": "void handleTimeout()",
        "doc_comment": "",
        "content": "void handleTimeout() { /* timeout logic */ }",
        "line_start": 10,
        "line_end": 15,
        "parent_class": "TimeoutHandler",
    }
    defaults.update(overrides)
    return defaults


def _doc_source(repo_id: str = "spring-framework", **overrides) -> dict:
    defaults = {
        "repo_id": repo_id,
        "file_path": "docs/README.md",
        "breadcrumb": "docs > Timeout",
        "content": "Timeout handling documentation.",
        "heading_level": 2,
    }
    defaults.update(overrides)
    return defaults


def _mock_es_response(hits: list[dict]) -> dict:
    return {"hits": {"hits": hits, "total": {"value": len(hits)}}}


def _make_chunks(
    n: int, content_type: str = "code", repo_id: str = "test-repo"
) -> list[ScoredChunk]:
    return [
        ScoredChunk(
            chunk_id=f"chunk-{content_type}-{i}",
            content_type=content_type,
            repo_id=repo_id,
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
    defaults = dict(
        query="test",
        query_type="nl",
        repo=None,
        code_results=[],
        doc_results=[],
    )
    defaults.update(kwargs)
    return QueryResponse(**defaults)


@pytest.fixture
def retriever():
    """Build a Retriever with a mocked ES client."""
    from src.query.retriever import Retriever
    from src.shared.clients.elasticsearch import ElasticsearchClient

    es = MagicMock(spec=ElasticsearchClient)
    es._client = AsyncMock()
    return Retriever(es_client=es)


@pytest.fixture
def handler():
    """Build a QueryHandler with mocked dependencies."""
    from src.query.query_handler import QueryHandler

    ret = MagicMock()
    ret.bm25_code_search = AsyncMock(return_value=_make_chunks(3, "code"))
    ret.vector_code_search = AsyncMock(return_value=_make_chunks(3, "code"))
    ret.bm25_doc_search = AsyncMock(return_value=_make_chunks(2, "doc"))
    ret.vector_doc_search = AsyncMock(return_value=_make_chunks(2, "doc"))
    ret._execute_search = AsyncMock(return_value=[])
    ret._parse_code_hits = MagicMock(return_value=[])
    ret._code_index = "code_chunks"

    rank_fusion = MagicMock()
    rank_fusion.fuse = MagicMock(return_value=_make_chunks(6, "code"))

    reranker = MagicMock()
    reranker.rerank = MagicMock(return_value=_make_chunks(6, "code"))

    response_builder = MagicMock()
    response_builder.build = MagicMock(return_value=_make_response())

    qh = QueryHandler(
        retriever=ret,
        rank_fusion=rank_fusion,
        reranker=reranker,
        response_builder=response_builder,
    )
    return qh


# ===========================================================================
# A: Happy Path — repo filtering applied correctly
# ===========================================================================


# [unit] A1: BM25 code search with specific repo — all results from that repo
@pytest.mark.asyncio
async def test_bm25_code_search_with_repo_filter(retriever):
    """VS-1: BM25 code search restricted to specified repo_id."""
    hits = [
        _make_es_hit("c1", 5.0, _code_source("spring-framework")),
        _make_es_hit("c2", 4.0, _code_source("spring-framework")),
    ]
    retriever._es._client.search = AsyncMock(
        return_value=_mock_es_response(hits)
    )

    results = await retriever.bm25_code_search(
        "timeout", repo_id="spring-framework"
    )

    assert len(results) == 2
    assert all(c.repo_id == "spring-framework" for c in results)
    # Verify the ES query body included repo_id filter
    call_body = retriever._es._client.search.call_args
    query_body = call_body.kwargs.get("body") or call_body[1].get("body")
    filter_clauses = query_body["query"]["bool"]["filter"]
    repo_filters = [f for f in filter_clauses if "term" in f and "repo_id" in f["term"]]
    assert len(repo_filters) == 1
    assert repo_filters[0]["term"]["repo_id"] == "spring-framework"


# [unit] A2: Vector code search with specific repo — Qdrant filter includes repo
@pytest.mark.asyncio
async def test_vector_code_search_with_repo_filter(retriever):
    """VS-1: Vector search restricted to specified repo_id via Qdrant filter."""
    from src.indexing.embedding_encoder import EmbeddingEncoder
    from src.shared.clients.qdrant import QdrantClientWrapper

    qdrant = MagicMock(spec=QdrantClientWrapper)
    mock_point = MagicMock()
    mock_point.id = "pt1"
    mock_point.score = 0.9
    mock_point.payload = _code_source("spring-framework")
    qdrant._client = AsyncMock()
    qdrant._client.query_points = AsyncMock(
        return_value=MagicMock(points=[mock_point])
    )

    encoder = MagicMock(spec=EmbeddingEncoder)
    import numpy as np
    encoder.encode_query = MagicMock(return_value=np.array([0.1] * 1024))

    from src.query.retriever import Retriever

    ret = Retriever(
        es_client=MagicMock(),
        qdrant_client=qdrant,
        embedding_encoder=encoder,
    )

    results = await ret.vector_code_search("timeout", repo_id="spring-framework")

    assert len(results) == 1
    assert results[0].repo_id == "spring-framework"
    # Verify Qdrant was called with a filter containing repo_id
    qdrant_call = qdrant._client.query_points.call_args
    qfilter = qdrant_call.kwargs.get("query_filter")
    assert qfilter is not None
    repo_conditions = [
        c for c in qfilter.must if c.key == "repo_id"
    ]
    assert len(repo_conditions) == 1


# [unit] A3: BM25 code search without repo — results from multiple repos
@pytest.mark.asyncio
async def test_bm25_code_search_without_repo_filter(retriever):
    """VS-3: BM25 search across all repos when repo_id=None."""
    hits = [
        _make_es_hit("c1", 5.0, _code_source("repo-a")),
        _make_es_hit("c2", 4.0, _code_source("repo-b")),
    ]
    retriever._es._client.search = AsyncMock(
        return_value=_mock_es_response(hits)
    )

    results = await retriever.bm25_code_search("timeout", repo_id=None)

    assert len(results) == 2
    repo_ids = {c.repo_id for c in results}
    assert repo_ids == {"repo-a", "repo-b"}
    # Verify no repo_id filter in ES query
    call_body = retriever._es._client.search.call_args
    query_body = call_body.kwargs.get("body") or call_body[1].get("body")
    bool_clause = query_body["query"]["bool"]
    filter_clauses = bool_clause.get("filter", [])
    repo_filters = [
        f for f in filter_clauses if isinstance(f, dict) and "term" in f and "repo_id" in f.get("term", {})
    ]
    assert len(repo_filters) == 0


# [unit] A4: Vector code search without repo — Qdrant called with filter=None
@pytest.mark.asyncio
async def test_vector_code_search_without_repo_filter(retriever):
    """VS-3: Vector search across all repos when repo_id=None."""
    from src.indexing.embedding_encoder import EmbeddingEncoder
    from src.shared.clients.qdrant import QdrantClientWrapper

    qdrant = MagicMock(spec=QdrantClientWrapper)
    mock_point = MagicMock()
    mock_point.id = "pt1"
    mock_point.score = 0.9
    mock_point.payload = _code_source("any-repo")
    qdrant._client = AsyncMock()
    qdrant._client.query_points = AsyncMock(
        return_value=MagicMock(points=[mock_point])
    )

    encoder = MagicMock(spec=EmbeddingEncoder)
    import numpy as np
    encoder.encode_query = MagicMock(return_value=np.array([0.1] * 1024))

    from src.query.retriever import Retriever

    ret = Retriever(
        es_client=MagicMock(),
        qdrant_client=qdrant,
        embedding_encoder=encoder,
    )

    results = await ret.vector_code_search("timeout", repo_id=None)

    assert len(results) == 1
    # Verify Qdrant was called with query_filter=None
    qdrant_call = qdrant._client.query_points.call_args
    qfilter = qdrant_call.kwargs.get("query_filter")
    assert qfilter is None


# [unit] A5: NL query end-to-end with repo filter
@pytest.mark.asyncio
async def test_handle_nl_query_with_repo(handler):
    """VS-1: NL pipeline passes repo through to retriever and response."""
    handler._response_builder.build.return_value = _make_response(
        repo="spring-framework"
    )

    response = await handler.handle_nl_query(
        "timeout handling", repo="spring-framework"
    )

    assert response.repo == "spring-framework"
    # Verify retriever methods were called with repo="spring-framework"
    handler._retriever.bm25_code_search.assert_called()
    bm25_call = handler._retriever.bm25_code_search.call_args
    assert bm25_call[0][1] == "spring-framework" or bm25_call.kwargs.get("repo_id") == "spring-framework"


# [unit] A6: NL query end-to-end without repo filter
@pytest.mark.asyncio
async def test_handle_nl_query_without_repo(handler):
    """Wave 5: repo=None raises ValidationError (repo is now required)."""
    with pytest.raises(ValidationError, match="repo"):
        await handler.handle_nl_query("timeout handling", repo=None)


# [unit] A7: Symbol query with repo filter
@pytest.mark.asyncio
async def test_handle_symbol_query_with_repo(handler):
    """VS-1: Symbol query includes repo filter in ES term query."""
    term_hits = [
        _make_es_hit("c1", 5.0, _code_source("spring-framework")),
    ]
    handler._retriever._execute_search = AsyncMock(return_value=term_hits)
    handler._retriever._parse_code_hits = MagicMock(
        return_value=_make_chunks(1, "code", "spring-framework")
    )
    handler._response_builder.build.return_value = _make_response(
        repo="spring-framework"
    )

    response = await handler.handle_symbol_query(
        "UserService.getById", repo="spring-framework"
    )

    # Verify ES query included repo filter
    es_call = handler._retriever._execute_search.call_args
    query_body = es_call[0][1]  # second positional arg is the body
    filter_clauses = query_body["query"]["bool"].get("filter", [])
    repo_filters = [f for f in filter_clauses if "term" in f and "repo_id" in f["term"]]
    assert len(repo_filters) == 1
    assert repo_filters[0]["term"]["repo_id"] == "spring-framework"


# [unit] A8: Symbol query without repo filter
@pytest.mark.asyncio
async def test_handle_symbol_query_without_repo(handler):
    """VS-3: Symbol query omits repo filter when repo=None."""
    term_hits = [
        _make_es_hit("c1", 5.0, _code_source("any-repo")),
    ]
    handler._retriever._execute_search = AsyncMock(return_value=term_hits)
    handler._retriever._parse_code_hits = MagicMock(
        return_value=_make_chunks(1, "code", "any-repo")
    )
    handler._response_builder.build.return_value = _make_response(repo=None)

    response = await handler.handle_symbol_query(
        "UserService.getById", repo=None
    )

    # Verify ES query has NO repo filter
    es_call = handler._retriever._execute_search.call_args
    query_body = es_call[0][1]
    filter_clauses = query_body["query"]["bool"].get("filter", [])
    repo_filters = [f for f in filter_clauses if "term" in f and "repo_id" in f.get("term", {})]
    assert len(repo_filters) == 0


# ===========================================================================
# B: Error handling — non-existent repo returns empty results
# ===========================================================================


# [unit] B1: BM25 search with non-existent repo returns empty list
@pytest.mark.asyncio
async def test_bm25_search_nonexistent_repo_returns_empty(retriever):
    """VS-2: Non-existent repo returns empty list, no exception."""
    retriever._es._client.search = AsyncMock(
        return_value=_mock_es_response([])
    )

    results = await retriever.bm25_code_search(
        "timeout", repo_id="nonexistent-repo"
    )

    assert results == []
    assert isinstance(results, list)


# [unit] B2: NL pipeline with non-existent repo returns empty response
@pytest.mark.asyncio
async def test_handle_nl_query_nonexistent_repo(handler):
    """VS-2: Non-existent repo produces empty response with degraded=False."""
    handler._retriever.bm25_code_search = AsyncMock(return_value=[])
    handler._retriever.vector_code_search = AsyncMock(return_value=[])
    handler._retriever.bm25_doc_search = AsyncMock(return_value=[])
    handler._retriever.vector_doc_search = AsyncMock(return_value=[])
    handler._rank_fusion.fuse.return_value = []
    handler._reranker.rerank.return_value = []
    handler._response_builder.build.return_value = _make_response(
        repo="nonexistent-repo", code_results=[], doc_results=[]
    )

    response = await handler.handle_nl_query(
        "timeout", repo="nonexistent-repo"
    )

    assert response.code_results == []
    assert response.doc_results == []
    assert response.degraded is False


# [unit] B3: Symbol pipeline with non-existent repo falls through to empty response
@pytest.mark.asyncio
async def test_handle_symbol_query_nonexistent_repo(handler):
    """VS-2: Non-existent repo in symbol query produces empty response."""
    handler._retriever._execute_search = AsyncMock(return_value=[])
    handler._retriever._parse_code_hits = MagicMock(return_value=[])
    handler._retriever.bm25_code_search = AsyncMock(return_value=[])
    handler._retriever.vector_code_search = AsyncMock(return_value=[])
    handler._retriever.bm25_doc_search = AsyncMock(return_value=[])
    handler._retriever.vector_doc_search = AsyncMock(return_value=[])
    handler._rank_fusion.fuse.return_value = []
    handler._reranker.rerank.return_value = []
    handler._response_builder.build.return_value = _make_response(
        repo="nonexistent-repo", code_results=[], doc_results=[]
    )

    response = await handler.handle_symbol_query(
        "getUserName", repo="nonexistent-repo"
    )

    assert response.code_results == []
    assert response.doc_results == []


# ===========================================================================
# C: Boundary — query construction edge cases
# ===========================================================================


# [unit] C1: _build_code_query with repo_id=None and languages=None → no filter key
def test_build_code_query_no_repo_no_lang(retriever):
    """Boundary: no filters when both repo and languages are None."""
    query_body = retriever._build_code_query("q", repo_id=None, languages=None, top_k=10)

    bool_clause = query_body["query"]["bool"]
    assert "must" in bool_clause
    # No filter key, or filter is empty
    filter_clauses = bool_clause.get("filter", [])
    assert len(filter_clauses) == 0


# [unit] C2: _build_code_query with repo_id=None but languages=["python"]
def test_build_code_query_no_repo_with_lang(retriever):
    """Boundary: language filter applied even when repo is None."""
    query_body = retriever._build_code_query(
        "q", repo_id=None, languages=["python"], top_k=10
    )

    bool_clause = query_body["query"]["bool"]
    filter_clauses = bool_clause.get("filter", [])
    # Should have language filter but no repo_id filter
    lang_filters = [f for f in filter_clauses if "terms" in f and "language" in f["terms"]]
    repo_filters = [f for f in filter_clauses if "term" in f and "repo_id" in f.get("term", {})]
    assert len(lang_filters) == 1
    assert lang_filters[0]["terms"]["language"] == ["python"]
    assert len(repo_filters) == 0


# [unit] C3: _build_qdrant_filter with None/None → returns None
def test_build_qdrant_filter_none_none(retriever):
    """Boundary: Qdrant filter is None when no repo and no languages."""
    result = retriever._build_qdrant_filter(repo_id=None, languages=None)

    assert result is None


# [unit] C4: _build_qdrant_filter with None repo but ["python"] languages
def test_build_qdrant_filter_no_repo_with_lang(retriever):
    """Boundary: Qdrant filter has language condition only."""
    result = retriever._build_qdrant_filter(
        repo_id=None, languages=["python"]
    )

    assert result is not None
    # Should have exactly 1 condition (language), no repo
    assert len(result.must) == 1
    assert result.must[0].key == "language"


# [unit] C5: BM25 doc search with repo_id=None
@pytest.mark.asyncio
async def test_bm25_doc_search_without_repo(retriever):
    """Boundary: doc search works without repo filter."""
    hits = [
        _make_es_hit("d1", 3.0, _doc_source("repo-a")),
    ]
    retriever._es._client.search = AsyncMock(
        return_value=_mock_es_response(hits)
    )

    results = await retriever.bm25_doc_search("timeout", repo_id=None)

    assert len(results) == 1
    # Verify no repo filter in query
    call_body = retriever._es._client.search.call_args
    query_body = call_body.kwargs.get("body") or call_body[1].get("body")
    bool_clause = query_body["query"]["bool"]
    filter_clauses = bool_clause.get("filter", [])
    repo_filters = [f for f in filter_clauses if "term" in f and "repo_id" in f.get("term", {})]
    assert len(repo_filters) == 0


# [unit] C6: _symbol_boost_search with repo=None
@pytest.mark.asyncio
async def test_symbol_boost_search_without_repo(handler):
    """Boundary: symbol boost queries omit repo filter when repo=None."""
    handler._retriever._execute_search = AsyncMock(return_value=[])

    await handler._symbol_boost_search(["getUserName"], repo=None)

    # Verify ES query has no repo filter
    es_call = handler._retriever._execute_search.call_args
    query_body = es_call[0][1]
    filter_clauses = query_body["query"]["bool"].get("filter", [])
    repo_filters = [f for f in filter_clauses if "term" in f and "repo_id" in f.get("term", {})]
    assert len(repo_filters) == 0
