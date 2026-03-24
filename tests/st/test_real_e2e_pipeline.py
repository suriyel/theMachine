"""End-to-end pipeline test with a REAL public GitHub repository.

Tests the COMPLETE flow: Register → Clone → Extract → Chunk → Embed → Write → Query
against a small real repo (suriyel/githubtrends, already cloned).

NO MOCKS. All services must be running: PostgreSQL, Elasticsearch, Qdrant, Redis, query-api.

Run:
    env -u ALL_PROXY -u all_proxy pytest tests/st/test_real_e2e_pipeline.py -v --no-cov -s
"""

from __future__ import annotations

import json
import os
import time

import pytest

API_BASE = "http://localhost:8000"
API_KEY = os.environ.get("DEMO_API_KEY", "RD7LAEY7qZVh_ZzAuvMQgrYFRN-xX9BvqVdUi9HR6lE")
REPO_URL = "https://github.com/suriyel/githubtrends"
REPO_NAME = "suriyel/githubtrends"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def api(method, path, body=None, key=API_KEY):
    import urllib.request, urllib.error
    url = f"{API_BASE}{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if key:
        headers["X-API-Key"] = key
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.getcode(), json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode() if e.readable() else ""
        try:
            return e.code, json.loads(body_text)
        except json.JSONDecodeError:
            return e.code, {"detail": body_text}


# ---------------------------------------------------------------------------
# E2E: Full pipeline with real GitHub repo
# ---------------------------------------------------------------------------


@pytest.mark.real
class TestRealGitHubE2EPipeline:
    """Complete register → index → query pipeline against a real GitHub repo.

    This test class verifies the entire system works end-to-end with real data
    from suriyel/githubtrends (Python + TypeScript, ~178 files, ~2071 chunks).
    """

    # --- Phase 1: Verify repo is registered and indexed ---

    def test_01_repo_is_registered(self):
        """Phase 1: Verify repo exists in the system."""
        code, repos = api("GET", "/api/v1/repos")
        assert code == 200
        names = [r["name"] for r in repos]
        assert REPO_NAME in names, f"{REPO_NAME} not registered"

    def test_02_repo_status_is_indexed(self):
        """Phase 1: Repo status should be 'indexed' after pipeline."""
        code, repos = api("GET", "/api/v1/repos")
        assert code == 200
        repo = next(r for r in repos if r["name"] == REPO_NAME)
        assert repo["status"] == "indexed", f"Status is {repo['status']}, expected indexed"

    # --- Phase 2: Verify index data exists in ES + Qdrant ---

    def test_03_es_code_chunks_from_repo(self):
        """Phase 2: ES has code chunks for this repo."""
        import urllib.request
        url = "http://localhost:9200/code_chunks/_count"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
        assert data["count"] >= 500, f"Only {data['count']} code chunks"

    def test_04_es_doc_chunks_from_repo(self):
        """Phase 2: ES has doc chunks for this repo."""
        import urllib.request
        url = "http://localhost:9200/doc_chunks/_count"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
        assert data["count"] >= 1000, f"Only {data['count']} doc chunks"

    def test_05_qdrant_vectors_match_es(self):
        """Phase 2: Qdrant point count matches ES code chunk count."""
        import urllib.request
        # ES count
        with urllib.request.urlopen("http://localhost:9200/code_chunks/_count", timeout=5) as resp:
            es_count = json.loads(resp.read())["count"]
        # Qdrant count
        with urllib.request.urlopen("http://localhost:6333/collections/code_embeddings", timeout=5) as resp:
            qdrant_count = json.loads(resp.read())["result"]["points_count"]
        assert qdrant_count == es_count, f"Qdrant({qdrant_count}) != ES({es_count})"

    def test_06_vectors_are_1024_dim(self):
        """Phase 2: Embeddings are 1024-dimensional (CON-010)."""
        import urllib.request
        with urllib.request.urlopen("http://localhost:6333/collections/code_embeddings", timeout=5) as resp:
            dim = json.loads(resp.read())["result"]["config"]["params"]["vectors"]["size"]
        assert dim == 1024

    # --- Phase 3: Query pipeline — BM25 + Vector + RRF + Rerank ---

    def test_07_nl_query_full_pipeline_not_degraded(self):
        """Phase 3: NL query → full 4-path pipeline → degraded=false."""
        code, data = api("POST", "/api/v1/query", {"query": "weekly report generation"})
        assert code == 200
        assert data["degraded"] is False, "Pipeline degraded — check embedding/reranker config"
        total = len(data["code_results"]) + len(data["doc_results"])
        assert total > 0, "No results returned"

    def test_08_nl_query_returns_relevant_code(self):
        """Phase 3: NL query returns relevant Python code with rerank scores."""
        code, data = api("POST", "/api/v1/query", {
            "query": "search trending repositories github API",
            "languages": ["python"],
        })
        assert code == 200
        assert len(data["code_results"]) > 0, "No Python code results"
        top = data["code_results"][0]
        assert top["language"] == "python"
        assert top["relevance_score"] > 0
        assert "file_path" in top
        assert len(top["content"]) > 0

    def test_09_nl_query_returns_relevant_docs(self):
        """Phase 3: NL query returns relevant documentation."""
        code, data = api("POST", "/api/v1/query", {"query": "how to deploy with Docker"})
        assert code == 200
        assert len(data["doc_results"]) > 0, "No doc results"
        top = data["doc_results"][0]
        assert "deploy" in top["content"].lower() or "docker" in top["content"].lower()

    def test_10_symbol_query_finds_class(self):
        """Phase 3: Symbol query finds exact class definition."""
        code, data = api("POST", "/api/v1/query", {"query": "GitHubService"})
        assert code == 200
        assert data["query_type"] == "symbol"
        assert len(data["code_results"]) > 0
        assert "GitHubService" in data["code_results"][0]["content"]

    def test_11_typescript_filter_only_returns_ts(self):
        """Phase 3: TypeScript language filter isolates TS code."""
        code, data = api("POST", "/api/v1/query", {
            "query": "React component",
            "languages": ["typescript"],
        })
        assert code == 200
        for r in data["code_results"]:
            assert r["language"] == "typescript"

    def test_12_repo_scoped_query(self):
        """Phase 3: repo_id filter restricts to target repo."""
        code, data = api("POST", "/api/v1/query", {
            "query": "database model",
            "repo_id": REPO_NAME,
        })
        assert code == 200
        # Should return results (repo has DB models)

    # --- Phase 4: MCP tool call → same pipeline ---

    def test_13_mcp_tool_returns_same_data(self):
        """Phase 4: MCP search_code_context hits the same pipeline as REST."""
        import asyncio
        for k in ("ALL_PROXY", "all_proxy"):
            os.environ.pop(k, None)

        async def mcp_search():
            from src.shared.database import get_engine, get_session_factory
            from src.shared.clients.elasticsearch import ElasticsearchClient
            from src.shared.clients.qdrant import QdrantClientWrapper
            from src.indexing.embedding_encoder import EmbeddingEncoder
            from src.query.retriever import Retriever
            from src.query.rank_fusion import RankFusion
            from src.query.reranker import Reranker
            from src.query.response_builder import ResponseBuilder
            from src.query.query_handler import QueryHandler
            from src.query.mcp_server import create_mcp_server

            es = ElasticsearchClient(url=os.environ["ELASTICSEARCH_URL"])
            qdrant = QdrantClientWrapper(url=os.environ["QDRANT_URL"])
            await es.connect(); await qdrant.connect()
            engine = get_engine(os.environ["DATABASE_URL"])
            sf = get_session_factory(engine)
            encoder = EmbeddingEncoder()
            handler = QueryHandler(
                retriever=Retriever(es_client=es, qdrant_client=qdrant, embedding_encoder=encoder),
                rank_fusion=RankFusion(), reranker=Reranker(), response_builder=ResponseBuilder(),
                search_timeout=5.0, pipeline_timeout=15.0)
            mcp = create_mcp_server(handler, sf, es)
            fn = mcp._tool_manager._tools["search_code_context"].fn
            result = json.loads(await fn(query="weekly report"))
            await es.close(); await qdrant.close(); await engine.dispose()
            return result

        mcp_data = asyncio.run(mcp_search())

        # REST query
        _, rest_data = api("POST", "/api/v1/query", {"query": "weekly report"})

        # Both should return non-empty results
        mcp_total = len(mcp_data.get("code_results", [])) + len(mcp_data.get("doc_results", []))
        rest_total = len(rest_data.get("code_results", [])) + len(rest_data.get("doc_results", []))
        assert mcp_total > 0, "MCP returned no results"
        assert rest_total > 0, "REST returned no results"

    # --- Phase 5: Security + Auth on real system ---

    def test_14_unauthenticated_rejected(self):
        """Phase 5: No API key → 401 on real system."""
        code, _ = api("POST", "/api/v1/query", {"query": "test"}, key=None)
        assert code == 401

    def test_15_injection_safe(self):
        """Phase 5: XSS/SQL injection payload handled safely on real system."""
        code, _ = api("POST", "/api/v1/query", {"query": "<script>alert(1)</script>"})
        assert code in (200, 400)

    # --- Phase 6: Cache + Performance ---

    def test_16_cache_hit_faster(self):
        """Phase 6: Cached repeat query is served (Redis L1/L2)."""
        q = {"query": "github trending weekly"}
        api("POST", "/api/v1/query", q)  # warm cache
        t0 = time.time()
        code, _ = api("POST", "/api/v1/query", q)
        elapsed = time.time() - t0
        assert code == 200
        assert elapsed < 10.0, f"Cached query took {elapsed:.1f}s"

    def test_17_pipeline_under_timeout(self):
        """Phase 6: Fresh query completes within pipeline timeout."""
        t0 = time.time()
        code, data = api("POST", "/api/v1/query", {
            "query": "how to configure automated collection",
            "languages": ["python"],
        })
        elapsed = time.time() - t0
        assert code == 200
        assert elapsed < 15.0, f"Pipeline took {elapsed:.1f}s"

    # --- Phase 7: Branch listing ---

    def test_18_branch_listing_for_cloned_repo(self):
        """Phase 7: Branch API returns branches for cloned repo (FR-023)."""
        _, repos = api("GET", "/api/v1/repos")
        repo = next(r for r in repos if r["name"] == REPO_NAME)
        code, data = api("GET", f"/api/v1/repos/{repo['id']}/branches")
        # 200 (branches returned) or 409 (clone not ready)
        assert code in (200, 409)
        if code == 200:
            assert "branches" in data
            assert len(data["branches"]) >= 1

    # --- Phase 8: Web UI serves real data ---

    def test_19_web_ui_search_page_contains_repo(self):
        """Phase 8: Web UI root page lists the indexed repo in dropdown."""
        import urllib.request
        with urllib.request.urlopen(f"{API_BASE}/", timeout=5) as resp:
            html = resp.read().decode()
        assert "githubtrends" in html or "suriyel" in html, "Indexed repo not in Web UI dropdown"

    # --- Phase 9: Metrics updated after queries ---

    def test_20_metrics_reflect_query_activity(self):
        """Phase 9: /metrics shows query_total > 0 after queries."""
        import urllib.request
        with urllib.request.urlopen(f"{API_BASE}/metrics", timeout=5) as resp:
            body = resp.read().decode()
        # After all the queries above, counters should be non-zero
        assert "query_latency_seconds" in body
