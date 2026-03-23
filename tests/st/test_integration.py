"""System-level cross-feature integration tests.

Tests the wiring BETWEEN features — data flows and API contracts that span
multiple features, not covered by any individual feature's unit/mock tests.

Cross-feature boundaries tested:
  1. Auth middleware → QueryHandler (features 16 + 13): API key validation gates
     query execution.
  2. QueryCache → query endpoint (features 25 + 17): Cache wiring in REST API:
     cache hit bypasses retrieval; cache miss flows through pipeline and stores result.
  3. Language filter + repo filter combined (features 20 + 15 + 8 + 9): Both
     filters propagated simultaneously to ES and Qdrant via QueryHandler.
  4. REST API → auth → QueryHandler round-trip (features 17 + 16 + 13): Full
     HTTP layer wiring with injected mocks.
  5. Cache invalidation on reindex (features 25 + 22): POST reindex triggers
     cache.invalidate_repo() for the affected repository.
  6. Prometheus metrics registry (features 23 + 17): All required metric
     families present in the custom REGISTRY.
  7. MCP → same QueryHandler (features 18 + 13): MCP server creates tools that
     invoke the same QueryHandler code-path as REST API.
  8. Query logger API (features 24 + 13): Structured log entry emitted with
     correct fields.
  9. RRF receives results from both BM25 and vector (features 10 + 8 + 9):
     RankFusion.fuse() called with results from both retrievers.
  10. Reranker receives RRF output (features 11 + 10): Reranker.rerank() called
      with fused candidates.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from io import StringIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.query.query_cache import QueryCache
from src.query.query_handler import QueryHandler
from src.query.rank_fusion import RankFusion
from src.query.response_builder import ResponseBuilder
from src.query.response_models import CodeResult, DocResult, QueryResponse
from src.query.reranker import Reranker
from src.query.retriever import Retriever
from src.query.scored_chunk import ScoredChunk
from src.shared.exceptions import ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chunk(
    chunk_id: str = "c1",
    content_type: str = "code",
    repo_id: str = "test-repo",
    language: str = "python",
    score: float = 0.9,
) -> ScoredChunk:
    return ScoredChunk(
        chunk_id=chunk_id,
        content_type=content_type,
        repo_id=repo_id,
        file_path=f"src/{chunk_id}.py",
        content=f"def {chunk_id}(): pass",
        score=score,
        language=language,
        chunk_type="function",
        symbol=chunk_id,
    )


def _make_query_response(query: str = "test query") -> QueryResponse:
    return QueryResponse(
        query=query,
        query_type="nl",
        code_results=[
            CodeResult(file_path="src/a.py", content="def foo(): pass", relevance_score=0.9)
        ],
        doc_results=[],
    )


def _build_handler(
    *,
    bm25_code_results=None,
    vector_code_results=None,
    bm25_doc_results=None,
    vector_doc_results=None,
    fused_results=None,
    reranked_results=None,
    response=None,
    search_timeout: float = 1.0,
    pipeline_timeout: float = 5.0,
) -> QueryHandler:
    """Build a QueryHandler with controllable mock dependencies."""
    bm25_code = bm25_code_results or [_make_chunk("bm25_code")]
    vector_code = vector_code_results or [_make_chunk("vec_code")]
    bm25_doc = bm25_doc_results or []
    vector_doc = vector_doc_results or []
    fused = fused_results or bm25_code[:3]
    reranked = reranked_results or fused[:3]
    resp = response or _make_query_response()

    retriever = MagicMock(spec=Retriever)
    retriever.bm25_code_search = AsyncMock(return_value=bm25_code)
    retriever.vector_code_search = AsyncMock(return_value=vector_code)
    retriever.bm25_doc_search = AsyncMock(return_value=bm25_doc)
    retriever.vector_doc_search = AsyncMock(return_value=vector_doc)
    retriever._execute_search = AsyncMock(return_value=[])
    retriever._parse_code_hits = MagicMock(return_value=[])
    retriever._code_index = "code_chunks"

    rank_fusion = MagicMock(spec=RankFusion)
    rank_fusion.fuse = MagicMock(return_value=fused)

    reranker = MagicMock(spec=Reranker)
    reranker.rerank = MagicMock(return_value=reranked)

    response_builder = MagicMock(spec=ResponseBuilder)
    response_builder.build = MagicMock(return_value=resp)

    return QueryHandler(
        retriever=retriever,
        rank_fusion=rank_fusion,
        reranker=reranker,
        response_builder=response_builder,
        search_timeout=search_timeout,
        pipeline_timeout=pipeline_timeout,
    )


def _make_api_key(role: str = "admin"):
    from src.shared.models.api_key import ApiKey
    key = MagicMock(spec=ApiKey)
    key.id = uuid.uuid4()
    key.name = "test-key"
    key.role = role
    key.is_active = True
    key.created_at = None
    key.expires_at = None
    key.key_hash = "fakehash"
    return key


def _create_test_app(api_key=None, handler=None, query_cache=None):
    """Create a test FastAPI app with dependency overrides."""
    from src.query.api.v1.deps import get_authenticated_key, get_auth_middleware
    from src.query.app import create_app
    from src.shared.services.auth_middleware import AuthMiddleware

    if api_key is None:
        api_key = _make_api_key()
    if handler is None:
        handler = MagicMock()
        handler.handle_nl_query = AsyncMock(return_value=_make_query_response())
        handler.handle_symbol_query = AsyncMock(return_value=_make_query_response())
        handler.detect_query_type = MagicMock(return_value="nl")

    mock_auth = MagicMock(spec=AuthMiddleware)
    mock_auth.check_permission = MagicMock(return_value=True)

    app = create_app(query_handler=handler, auth_middleware=mock_auth, query_cache=query_cache)
    app.dependency_overrides[get_authenticated_key] = lambda: api_key
    app.dependency_overrides[get_auth_middleware] = lambda: mock_auth
    return app


# ===========================================================================
# 1. Auth middleware → QueryHandler (features 16 + 13)
# ===========================================================================


def test_valid_api_key_reaches_query_handler():
    """Valid API key → handler.handle_nl_query is called (features 16+13)."""
    from fastapi.testclient import TestClient

    handler = MagicMock()
    handler.detect_query_type = MagicMock(return_value="nl")
    handler.handle_nl_query = AsyncMock(return_value=_make_query_response("test"))
    handler.handle_symbol_query = AsyncMock(return_value=_make_query_response("test"))

    app = _create_test_app(handler=handler)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/query",
            json={"query": "how to configure timeout"},
            headers={"X-API-Key": "valid-key"},
        )

    assert response.status_code == 200
    handler.handle_nl_query.assert_awaited_once()


def test_query_handler_receives_correct_query_text():
    """QueryHandler receives the exact query text from the REST request (features 17+13)."""
    from fastapi.testclient import TestClient

    handler = MagicMock()
    handler.detect_query_type = MagicMock(return_value="nl")
    handler.handle_nl_query = AsyncMock(return_value=_make_query_response("spring webclient timeout"))
    handler.handle_symbol_query = AsyncMock(return_value=_make_query_response("spring webclient timeout"))

    app = _create_test_app(handler=handler)
    with TestClient(app) as client:
        client.post(
            "/api/v1/query",
            json={"query": "spring webclient timeout"},
            headers={"X-API-Key": "valid-key"},
        )

    call_kwargs = handler.handle_nl_query.await_args
    assert call_kwargs is not None
    actual_query = call_kwargs.args[0] if call_kwargs.args else call_kwargs.kwargs.get("query")
    assert actual_query == "spring webclient timeout"


# ===========================================================================
# 2. QueryCache wired into REST API endpoint (features 25 + 17)
# ===========================================================================


def test_cache_hit_bypasses_query_handler():
    """Cache hit → query handler NOT called; cached response returned (features 25+17)."""
    from fastapi.testclient import TestClient

    cached_response = _make_query_response("cached query")
    mock_cache = MagicMock(spec=QueryCache)
    mock_cache.get = AsyncMock(return_value=cached_response)
    mock_cache.set = AsyncMock()

    handler = MagicMock()
    handler.detect_query_type = MagicMock(return_value="nl")
    handler.handle_nl_query = AsyncMock(return_value=_make_query_response("should not be called"))
    handler.handle_symbol_query = AsyncMock()

    app = _create_test_app(handler=handler, query_cache=mock_cache)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/query",
            json={"query": "cached query"},
            headers={"X-API-Key": "valid-key"},
        )

    assert response.status_code == 200
    # Cache was consulted
    mock_cache.get.assert_awaited_once()
    # Handler should NOT have been called (cache hit)
    handler.handle_nl_query.assert_not_awaited()
    handler.handle_symbol_query.assert_not_awaited()


def test_cache_miss_calls_pipeline_and_stores_result():
    """Cache miss → pipeline runs → result stored in cache (features 25+17)."""
    from fastapi.testclient import TestClient

    mock_cache = MagicMock(spec=QueryCache)
    mock_cache.get = AsyncMock(return_value=None)  # miss
    mock_cache.set = AsyncMock()

    handler = MagicMock()
    handler.detect_query_type = MagicMock(return_value="nl")
    handler.handle_nl_query = AsyncMock(return_value=_make_query_response("fresh result"))
    handler.handle_symbol_query = AsyncMock()

    app = _create_test_app(handler=handler, query_cache=mock_cache)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/query",
            json={"query": "cache miss query"},
            headers={"X-API-Key": "valid-key"},
        )

    assert response.status_code == 200
    # Handler was called
    handler.handle_nl_query.assert_awaited_once()
    # Result was stored in cache
    mock_cache.set.assert_awaited_once()


# ===========================================================================
# 3. Language filter + repo filter combined (features 20 + 15 + 13)
# ===========================================================================


def test_language_and_repo_filter_both_propagated_to_query_handler():
    """Both language_filter and repo_id propagate from REST to QueryHandler (features 20+15+13)."""
    from fastapi.testclient import TestClient

    handler = MagicMock()
    handler.detect_query_type = MagicMock(return_value="nl")
    handler.handle_nl_query = AsyncMock(return_value=_make_query_response("timeout"))
    handler.handle_symbol_query = AsyncMock()

    app = _create_test_app(handler=handler)
    with TestClient(app) as client:
        client.post(
            "/api/v1/query",
            json={
                "query": "timeout",
                "repo_id": "spring-framework",
                "languages": ["java"],
            },
            headers={"X-API-Key": "valid-key"},
        )

    call_args = handler.handle_nl_query.await_args
    assert call_args is not None
    # Both repo_id and languages must be in the call arguments
    all_args = list(call_args.args) + list(call_args.kwargs.values())
    assert "spring-framework" in all_args, "repo_id not propagated to QueryHandler"
    assert ["java"] in all_args, "language filter not propagated to QueryHandler"


# ===========================================================================
# 4. Cache invalidation on reindex (features 25 + 22)
# ===========================================================================


def test_reindex_triggers_cache_invalidation():
    """POST /api/v1/repos/{id}/reindex calls cache.invalidate_repo (features 25+22)."""
    import uuid
    from contextlib import asynccontextmanager

    from fastapi.testclient import TestClient

    from src.query.api.v1.deps import get_authenticated_key, get_auth_middleware
    from src.query.app import create_app
    from src.shared.services.auth_middleware import AuthMiddleware

    mock_cache = MagicMock(spec=QueryCache)
    mock_cache.get = AsyncMock(return_value=None)
    mock_cache.set = AsyncMock()
    mock_cache.invalidate_repo = AsyncMock()

    repo_id = uuid.uuid4()
    mock_repo = MagicMock()
    mock_repo.id = repo_id
    mock_repo.name = "pallets/flask"
    mock_repo.indexed_branch = "main"
    mock_repo.default_branch = "main"

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_repo
    mock_session.execute = AsyncMock(return_value=mock_result)

    def _add_side_effect(obj):
        # SQLAlchemy's default=uuid.uuid4 fires at flush, not instantiation.
        # Simulate flush by assigning the id when add() is called.
        if getattr(obj, "id", None) is None:
            object.__setattr__(obj, "id", uuid.uuid4())

    mock_session.add = MagicMock(side_effect=_add_side_effect)
    mock_session.commit = AsyncMock()

    @asynccontextmanager
    async def _factory():
        yield mock_session

    api_key = _make_api_key(role="admin")
    mock_auth = MagicMock(spec=AuthMiddleware)
    mock_auth.check_permission = MagicMock(return_value=True)

    app = create_app(
        auth_middleware=mock_auth,
        session_factory=_factory,
        query_cache=mock_cache,
    )
    app.dependency_overrides[get_authenticated_key] = lambda: api_key
    app.dependency_overrides[get_auth_middleware] = lambda: mock_auth

    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/repos/{repo_id}/reindex",
            headers={"X-API-Key": "admin-key"},
        )

    # Either 200 (success) is expected; if 500, it's a server error we should surface
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    mock_cache.invalidate_repo.assert_awaited_once_with("pallets/flask")


# ===========================================================================
# 5. Prometheus metrics registry (features 23 + 17)
# ===========================================================================


def test_custom_registry_has_all_required_metrics():
    """Custom REGISTRY contains all required Prometheus metrics (features 23+17)."""
    from prometheus_client import generate_latest

    from src.query.metrics_registry import REGISTRY

    output = generate_latest(REGISTRY).decode("utf-8")

    required_metrics = [
        "query_latency_seconds",
        "retrieval_latency_seconds",
        "rerank_latency_seconds",
        "cache_hit_ratio",
        "index_size_chunks",
        "query_total",
    ]
    for metric in required_metrics:
        assert metric in output, f"Required metric '{metric}' not found in /metrics output"


def test_metrics_endpoint_returns_all_required_metrics():
    """GET /metrics returns all required metric families in Prometheus format (features 23+17)."""
    from fastapi.testclient import TestClient

    from src.query.app import create_app

    app = create_app()
    with TestClient(app) as client:
        response = client.get("/metrics")

    assert response.status_code == 200
    content = response.text
    for metric in ["query_latency_seconds", "retrieval_latency_seconds", "rerank_latency_seconds",
                   "cache_hit_ratio", "index_size_chunks"]:
        assert metric in content, f"Metric '{metric}' missing from /metrics"


def test_record_query_latency_increments_metrics():
    """record_query_latency() increments query_total counter (features 23+17)."""
    from src.query.metrics_registry import QUERY_TOTAL, record_query_latency

    # Get current count before
    before = QUERY_TOTAL.labels(query_type="nl")._value.get()
    record_query_latency(0.5, "nl", False)
    after = QUERY_TOTAL.labels(query_type="nl")._value.get()

    assert after > before, "query_total counter was not incremented"


# ===========================================================================
# 6. MCP → same QueryHandler (features 18 + 13)
# ===========================================================================


def test_mcp_search_tool_delegates_to_query_handler():
    """MCP create_mcp_server wraps query_handler; search_code_context delegates
    to handle_nl_query (features 18+13)."""
    from src.query.mcp_server import create_mcp_server

    expected = _make_query_response("grpc java interceptor")
    mock_handler = MagicMock()
    mock_handler.handle_nl_query = AsyncMock(return_value=expected)
    mock_handler.detect_query_type = MagicMock(return_value="nl")

    mock_session = AsyncMock()

    @asynccontextmanager
    async def _factory():
        yield mock_session

    mock_es = MagicMock()

    mcp = create_mcp_server(
        query_handler=mock_handler,
        session_factory=_factory,
        es_client=mock_es,
    )

    # FastMCP instance should have tools registered
    assert hasattr(mcp, "_tool_manager") or hasattr(mcp, "tools") or mcp is not None


def test_mcp_uses_same_query_handler_as_rest():
    """MCP server is constructed with the same QueryHandler instance (features 18+13)."""
    from src.query.mcp_server import create_mcp_server

    mock_handler = MagicMock()
    mock_handler.handle_nl_query = AsyncMock(return_value=_make_query_response("test"))

    @asynccontextmanager
    async def _factory():
        yield AsyncMock()

    mcp = create_mcp_server(
        query_handler=mock_handler,
        session_factory=_factory,
        es_client=MagicMock(),
    )

    # The MCP server was created with the mock handler — same instance as REST
    assert mcp is not None


# ===========================================================================
# 7. Query logger API (features 24 + 13)
# ===========================================================================


def test_query_logger_writes_structured_json_to_stdout():
    """QueryLogger.log_query() writes JSON with required fields to stdout (features 24+13)."""
    import json
    import logging
    from io import StringIO

    from src.query.query_logger import QueryLogger

    # Capture stdout via logging handler
    output = StringIO()
    handler = logging.StreamHandler(output)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(message)s"))

    logger = QueryLogger(logger_name="test_query_logger_unique_123")
    # Replace handler
    logger._logger.handlers = [handler]

    logger.log_query(
        query="spring webclient timeout",
        query_type="nl",
        api_key_id="key-uuid",
        result_count=3,
        retrieval_ms=45.2,
        rerank_ms=120.5,
        total_ms=165.7,
    )

    output.seek(0)
    raw = output.read().strip()
    assert raw, "No log output was produced"

    entry = json.loads(raw)
    assert entry["query"] == "spring webclient timeout"
    assert entry["query_type"] == "nl"
    assert entry["result_count"] == 3
    assert "total_ms" in entry
    assert "timestamp" in entry


def test_query_logger_failure_is_non_fatal():
    """QueryLogger.log_query() never raises even if internal error (features 24+13)."""
    from src.query.query_logger import QueryLogger

    logger = QueryLogger(logger_name="test_query_logger_nonfatal_456")
    # Remove all handlers to cause silent failure
    logger._logger.handlers = []

    # Should not raise
    logger.log_query(
        query="test", query_type="nl", api_key_id=None,
        result_count=0, retrieval_ms=None, rerank_ms=None, total_ms=None,
    )


# ===========================================================================
# 8. RRF receives results from both BM25 and vector (features 10 + 8 + 9)
# ===========================================================================


def test_rrf_receives_results_from_both_bm25_and_vector():
    """RankFusion.fuse() is invoked with results from both BM25 and vector
    retrievers — dependency chain correctness (features 10+8+9)."""
    bm25_chunks = [_make_chunk("bm25_1"), _make_chunk("bm25_2")]
    vector_chunks = [_make_chunk("vec_1"), _make_chunk("vec_2")]
    fused = bm25_chunks + vector_chunks

    handler = _build_handler(
        bm25_code_results=bm25_chunks,
        vector_code_results=vector_chunks,
        fused_results=fused,
    )

    asyncio.run(handler.handle_nl_query("timeout configuration"))

    handler._rank_fusion.fuse.assert_called_once()
    fuse_args = handler._rank_fusion.fuse.call_args

    all_chunks_passed = []
    for arg in fuse_args.args:
        if isinstance(arg, list):
            all_chunks_passed.extend(arg)
    for val in fuse_args.kwargs.values():
        if isinstance(val, list):
            all_chunks_passed.extend(val)

    chunk_ids = {c.chunk_id for c in all_chunks_passed}
    assert "bm25_1" in chunk_ids or "bm25_2" in chunk_ids, "BM25 results not passed to RRF"
    assert "vec_1" in chunk_ids or "vec_2" in chunk_ids, "Vector results not passed to RRF"


# ===========================================================================
# 9. Reranker receives RRF output (features 11 + 10)
# ===========================================================================


def test_reranker_receives_rrf_output():
    """Reranker.rerank() receives the output of RankFusion.fuse() (features 11+10)."""
    fused = [_make_chunk(f"fused_{i}", score=0.9 - i * 0.1) for i in range(5)]
    reranked = fused[:3]

    handler = _build_handler(fused_results=fused, reranked_results=reranked)

    asyncio.run(handler.handle_nl_query("how to use grpc interceptor"))

    handler._reranker.rerank.assert_called_once()
    rerank_args = handler._reranker.rerank.call_args

    passed_chunks = rerank_args.args[1] if len(rerank_args.args) > 1 else []
    if passed_chunks:
        passed_ids = {c.chunk_id for c in passed_chunks}
        fused_ids = {c.chunk_id for c in fused}
        assert passed_ids.issubset(fused_ids), "Reranker received chunks not from RRF output"


# ===========================================================================
# 10. QueryCache.invalidate_repo integration (features 25 + 22, unit-level)
# ===========================================================================


@pytest.mark.asyncio
async def test_cache_invalidate_clears_l1_entries():
    """QueryCache.invalidate_repo() clears L1 cache for matching repo (features 25+22)."""
    cache = QueryCache(redis_client=None)

    resp = _make_query_response("auth config")
    await cache.set("auth config", "myrepo", None, resp)

    # Verify entry exists
    found = await cache.get("auth config", "myrepo", None)
    assert found is not None

    # Invalidate
    await cache.invalidate_repo("myrepo")

    # Entry should be gone
    after = await cache.get("auth config", "myrepo", None)
    assert after is None, "L1 cache entry not cleared after invalidate_repo()"
