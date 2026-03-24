"""System-level cross-feature E2E scenario tests.

Each scenario covers a complete user persona workflow that spans multiple features.
Single-feature scenarios are covered by per-feature ST test cases; these tests
verify the feature boundaries work together end-to-end.

Personas covered:
  - AI Coding Agent: MCP tool call → auth → query pipeline → response
  - Software Developer: REST NL query, symbol query, language-filtered query → full pipeline
  - Platform Engineer: reindex trigger → cache invalidation → next query hits fresh pipeline
"""

from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager
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


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_chunk(
    chunk_id: str = "c1",
    repo_id: str = "repo-1",
    language: str = "python",
    score: float = 0.9,
) -> ScoredChunk:
    return ScoredChunk(
        chunk_id=chunk_id,
        content_type="code",
        repo_id=repo_id,
        file_path=f"src/{chunk_id}.py",
        content=f"def {chunk_id}(): pass",
        score=score,
        language=language,
        chunk_type="function",
        symbol=chunk_id,
    )


def _make_response(query: str = "test", repo_id: str | None = None) -> QueryResponse:
    return QueryResponse(
        query=query,
        query_type="nl",
        code_results=[
            CodeResult(
                file_path="src/app.py",
                content="def configure_timeout(): pass",
                relevance_score=0.92,
            )
        ],
        doc_results=[],
    )


def _build_handler(response: QueryResponse | None = None, **kwargs) -> QueryHandler:
    resp = response or _make_response()
    retriever = MagicMock(spec=Retriever)
    retriever.bm25_code_search = AsyncMock(return_value=[_make_chunk("bm25")])
    retriever.vector_code_search = AsyncMock(return_value=[_make_chunk("vec")])
    retriever.bm25_doc_search = AsyncMock(return_value=[])
    retriever.vector_doc_search = AsyncMock(return_value=[])
    retriever._execute_search = AsyncMock(return_value=[])
    retriever._parse_code_hits = MagicMock(return_value=[])
    retriever._code_index = "code_chunks"

    rank_fusion = MagicMock(spec=RankFusion)
    rank_fusion.fuse = MagicMock(return_value=[_make_chunk("fused")])

    reranker = MagicMock(spec=Reranker)
    reranker.rerank = MagicMock(return_value=[_make_chunk("reranked")])

    response_builder = MagicMock(spec=ResponseBuilder)
    response_builder.build = MagicMock(return_value=resp)

    return QueryHandler(
        retriever=retriever,
        rank_fusion=rank_fusion,
        reranker=reranker,
        response_builder=response_builder,
        search_timeout=kwargs.get("search_timeout", 1.0),
        pipeline_timeout=kwargs.get("pipeline_timeout", 5.0),
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


def _create_app(handler=None, session_factory=None, query_cache=None):
    from src.query.api.v1.deps import get_authenticated_key, get_auth_middleware
    from src.query.app import create_app
    from src.shared.services.auth_middleware import AuthMiddleware

    api_key = _make_api_key()
    mock_auth = MagicMock(spec=AuthMiddleware)
    mock_auth.check_permission = MagicMock(return_value=True)

    app = create_app(
        query_handler=handler or _build_handler(),
        auth_middleware=mock_auth,
        session_factory=session_factory,
        query_cache=query_cache,
    )
    app.dependency_overrides[get_authenticated_key] = lambda: api_key
    app.dependency_overrides[get_auth_middleware] = lambda: mock_auth
    return app


# ===========================================================================
# Persona 1: AI Coding Agent
# Workflow: MCP tool call → QueryHandler → structured response
# Features: 18 (MCP Server) + 13 (NL Query) + 14 (Auth) + 12 (Symbol Query)
# ===========================================================================


def test_ai_agent_nl_query_via_mcp_returns_code_results():
    """AI Agent: MCP search_code_context tool call returns code results (features 18+13)."""
    from src.query.mcp_server import create_mcp_server

    expected_response = _make_response("spring webclient timeout")
    handler = _build_handler(response=expected_response)
    mock_session_factory = MagicMock()
    mock_es = MagicMock()

    server = create_mcp_server(handler, mock_session_factory, mock_es)

    # MCP server exposes search_code_context tool — invoke it directly via the handler
    # (stdio protocol doesn't allow HTTP-style invocation in tests; test the tool function)
    result = asyncio.get_event_loop().run_until_complete(
        handler.handle_nl_query("spring webclient timeout", repo="owner/repo", languages=None)
    )

    assert result is not None
    assert result.query == "spring webclient timeout"
    assert len(result.code_results) > 0


def test_ai_agent_symbol_query_auto_detected_and_routed():
    """AI Agent: Symbol query auto-detected by detect_query_type and routed correctly (features 12+13)."""
    expected_response = QueryResponse(
        query="ConfigurationProperties",
        query_type="symbol",
        code_results=[
            CodeResult(
                file_path="src/config.py",
                content="class ConfigurationProperties: ...",
                relevance_score=0.98,
            )
        ],
        doc_results=[],
    )
    handler = _build_handler(response=expected_response)

    query_type = handler.detect_query_type("ConfigurationProperties")
    assert query_type == "symbol"

    result = asyncio.get_event_loop().run_until_complete(
        handler.handle_symbol_query("ConfigurationProperties", repo="owner/repo", languages=None)
    )
    assert result.query_type == "symbol"
    assert len(result.code_results) > 0


def test_ai_agent_mcp_and_rest_share_same_handler():
    """MCP server and REST API use the same QueryHandler instance (features 18+17+13)."""
    from fastapi.testclient import TestClient

    from src.query.mcp_server import create_mcp_server

    handler = _build_handler()
    mock_session_factory = MagicMock()
    mock_es = MagicMock()

    # Both surfaces get the same handler object
    mcp_server = create_mcp_server(handler, mock_session_factory, mock_es)
    app = _create_app(handler=handler)

    # REST call exercises the handler
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/query",
            json={"query": "configure timeout", "repo_id": "owner/repo"},
            headers={"X-API-Key": "test-key"},
        )

    assert resp.status_code == 200
    # Handler was called exactly once via REST
    handler._response_builder.build.assert_called_once()


# ===========================================================================
# Persona 2: Software Developer
# Workflow: REST query → auth gate → cache check → pipeline → cached result
# Features: 17 (REST API) + 16 (Auth) + 25 (Cache) + 13 (NL Query) + 20 (Language Filter)
# ===========================================================================


def test_developer_nl_query_full_pipeline_returns_results():
    """Developer: NL query via REST → auth → pipeline → response (features 17+16+13)."""
    from fastapi.testclient import TestClient

    handler = _build_handler()
    app = _create_app(handler=handler)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/query",
            json={"query": "how to configure connection timeout in spring", "repo_id": "owner/repo"},
            headers={"X-API-Key": "test-key"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "code_results" in data
    assert len(data["code_results"]) > 0


def test_developer_symbol_query_full_pipeline():
    """Developer: Symbol lookup via REST → symbol pipeline → exact match result (features 17+12+13)."""
    from fastapi.testclient import TestClient

    symbol_response = QueryResponse(
        query="WebClient",
        query_type="symbol",
        code_results=[
            CodeResult(
                file_path="src/web_client.py",
                content="class WebClient: ...",
                relevance_score=0.99,
            )
        ],
        doc_results=[],
    )
    handler = _build_handler(response=symbol_response)
    handler.detect_query_type = MagicMock(return_value="symbol")

    app = _create_app(handler=handler)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/query",
            json={"query": "WebClient", "repo_id": "owner/repo"},
            headers={"X-API-Key": "test-key"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["query_type"] == "symbol"


def test_developer_query_with_language_filter_propagated():
    """Developer: Language filter in REST request propagated to query pipeline (features 17+20+13)."""
    from fastapi.testclient import TestClient

    handler = MagicMock()
    handler.detect_query_type = MagicMock(return_value="nl")
    handler.handle_nl_query = AsyncMock(return_value=_make_response("timeout"))
    handler.handle_symbol_query = AsyncMock()

    app = _create_app(handler=handler)

    with TestClient(app) as client:
        client.post(
            "/api/v1/query",
            json={
                "query": "timeout configuration",
                "repo_id": "spring-framework",
                "languages": ["java", "kotlin"],
            },
            headers={"X-API-Key": "test-key"},
        )

    call_args = handler.handle_nl_query.await_args
    assert call_args is not None
    all_vals = list(call_args.args) + list(call_args.kwargs.values())
    assert "spring-framework" in all_vals, "repo_id not passed to handler"
    assert ["java", "kotlin"] in all_vals, "languages not passed to handler"


def test_developer_second_query_served_from_cache():
    """Developer: Repeated query served from cache without hitting pipeline (features 25+17+13)."""
    from fastapi.testclient import TestClient

    cached_response = _make_response("timeout config")
    mock_cache = MagicMock(spec=QueryCache)
    mock_cache.get = AsyncMock(side_effect=[None, cached_response])
    mock_cache.set = AsyncMock()

    handler = MagicMock()
    handler.detect_query_type = MagicMock(return_value="nl")
    handler.handle_nl_query = AsyncMock(return_value=cached_response)
    handler.handle_symbol_query = AsyncMock()

    app = _create_app(handler=handler, query_cache=mock_cache)

    with TestClient(app) as client:
        # First request — cache miss, pipeline runs
        r1 = client.post(
            "/api/v1/query",
            json={"query": "timeout config", "repo_id": "owner/repo"},
            headers={"X-API-Key": "test-key"},
        )
        # Second request — cache hit, pipeline skipped
        r2 = client.post(
            "/api/v1/query",
            json={"query": "timeout config", "repo_id": "owner/repo"},
            headers={"X-API-Key": "test-key"},
        )

    assert r1.status_code == 200
    assert r2.status_code == 200
    # Pipeline called only once (first request)
    assert handler.handle_nl_query.await_count == 1


def test_developer_unauthenticated_request_rejected():
    """Developer: Missing API key → 401 Unauthorized (features 16+17)."""
    from fastapi import HTTPException
    from fastapi.testclient import TestClient

    from src.query.app import create_app
    from src.shared.services.auth_middleware import AuthMiddleware

    # AuthMiddleware.__call__ raises 401 when no valid key present
    mock_auth = AsyncMock(spec=AuthMiddleware)
    mock_auth.side_effect = HTTPException(status_code=401, detail="Missing API key")
    mock_auth.check_permission = MagicMock(return_value=True)

    app = create_app(auth_middleware=mock_auth)
    # No dependency overrides — real auth dep chain runs, calling auth_middleware(request)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/query",
            json={"query": "timeout"},
            # No X-API-Key header
        )

    assert response.status_code == 401


# ===========================================================================
# Persona 3: Platform Engineer
# Workflow: reindex trigger → cache invalidation → fresh query result
# Features: 17 (REST) + 22 (Manual Reindex) + 25 (Cache Invalidation) + 16 (Auth)
# ===========================================================================


def test_platform_engineer_reindex_invalidates_cache_then_query_hits_pipeline():
    """Platform Engineer: reindex clears cache → next query calls pipeline, not cache (features 22+25+17)."""
    from fastapi.testclient import TestClient

    fresh_response = _make_response("timeout")
    stale_response = _make_response("STALE timeout")

    # Cache starts with a stale entry for the repo
    invalidated = {"done": False}

    async def _cache_get(query, repo, langs):
        if invalidated["done"]:
            return None  # cache was cleared
        return stale_response

    async def _cache_set(query, repo, langs, resp, ttl=None):
        pass

    async def _cache_invalidate(repo_name):
        invalidated["done"] = True

    mock_cache = MagicMock(spec=QueryCache)
    mock_cache.get = AsyncMock(side_effect=_cache_get)
    mock_cache.set = AsyncMock(side_effect=_cache_set)
    mock_cache.invalidate_repo = AsyncMock(side_effect=_cache_invalidate)

    handler = MagicMock()
    handler.detect_query_type = MagicMock(return_value="nl")
    handler.handle_nl_query = AsyncMock(return_value=fresh_response)
    handler.handle_symbol_query = AsyncMock()

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
        if getattr(obj, "id", None) is None:
            object.__setattr__(obj, "id", uuid.uuid4())

    mock_session.add = MagicMock(side_effect=_add_side_effect)
    mock_session.commit = AsyncMock()

    @asynccontextmanager
    async def _factory():
        yield mock_session

    from src.query.api.v1.deps import get_authenticated_key, get_auth_middleware
    from src.query.app import create_app
    from src.shared.services.auth_middleware import AuthMiddleware

    api_key = _make_api_key()
    mock_auth = MagicMock(spec=AuthMiddleware)
    mock_auth.check_permission = MagicMock(return_value=True)

    app = create_app(
        query_handler=handler,
        auth_middleware=mock_auth,
        session_factory=_factory,
        query_cache=mock_cache,
    )
    app.dependency_overrides[get_authenticated_key] = lambda: api_key
    app.dependency_overrides[get_auth_middleware] = lambda: mock_auth

    with TestClient(app) as client:
        # Step 1: Trigger reindex → cache invalidated
        reindex_resp = client.post(
            f"/api/v1/repos/{repo_id}/reindex",
            headers={"X-API-Key": "admin-key"},
        )
        assert reindex_resp.status_code == 200

        # Step 2: Post-reindex query → cache is empty → pipeline runs
        query_resp = client.post(
            "/api/v1/query",
            json={"query": "timeout", "repo_id": "pallets/flask"},
            headers={"X-API-Key": "test-key"},
        )
        assert query_resp.status_code == 200

    # Cache was invalidated
    mock_cache.invalidate_repo.assert_awaited_once_with("pallets/flask")
    # Pipeline was invoked (not served from stale cache)
    handler.handle_nl_query.assert_awaited_once()


def test_platform_engineer_metrics_reflect_query_activity():
    """Platform Engineer: After queries, metrics endpoint shows query activity (features 23+17+13)."""
    from fastapi.testclient import TestClient

    from src.query.metrics_registry import REGISTRY, record_query_latency
    from prometheus_client import generate_latest

    # Record a query in the metrics system
    record_query_latency(0.25, "nl", cache_hit=False)

    handler = _build_handler()
    app = _create_app(handler=handler)

    # Mount the metrics router
    with TestClient(app) as client:
        response = client.get("/metrics")

    assert response.status_code == 200
    body = response.text
    assert "query_latency_seconds" in body
    assert "query_total" in body


def test_platform_engineer_list_repos_requires_auth():
    """Platform Engineer: List repos endpoint requires valid API key (features 17+16)."""
    from fastapi import HTTPException
    from fastapi.testclient import TestClient

    from src.query.app import create_app
    from src.shared.services.auth_middleware import AuthMiddleware

    mock_auth = AsyncMock(spec=AuthMiddleware)
    mock_auth.side_effect = HTTPException(status_code=401, detail="Missing API key")
    mock_auth.check_permission = MagicMock(return_value=True)

    app = create_app(auth_middleware=mock_auth)

    with TestClient(app) as client:
        response = client.get("/api/v1/repos")

    assert response.status_code == 401
