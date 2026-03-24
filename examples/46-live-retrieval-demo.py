#!/usr/bin/env python3
"""Live retrieval demo — full BM25 + Vector + RRF + Neural Rerank pipeline.

Demonstrates the Code Context Retrieval system against a real indexed repository
(suriyel/githubtrends), exercising all four retrieval paths and the qwen3-rerank
neural reranker.

Prerequisites:
    1. Services running: PostgreSQL, Elasticsearch, Qdrant, Redis
    2. Query API started: uvicorn --factory src.query.main:build_app --port 8000
    3. Repository indexed: suriyel/githubtrends (2071 chunks)
    4. API key created via APIKeyManager

Pipeline:
    Query ──> BM25 (Elasticsearch) ──┐
                                     ├── RRF Fusion ──> qwen3-rerank ──> Top results
    Query ──> Vector (Qdrant)    ────┘
              (text-embedding-v3, 1024-dim)

Configuration (.env):
    EMBEDDING_MODEL=text-embedding-v3
    EMBEDDING_API_KEY=<dashscope-key>
    EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
    RERANKER_MODEL=qwen3-rerank
    RERANKER_API_KEY=<dashscope-key>
    RERANKER_BASE_URL=https://dashscope.aliyuncs.com/compatible-api/v1
    RERANKER_THRESHOLD=0.3
    SEARCH_TIMEOUT=5.0
    PIPELINE_TIMEOUT=15.0

Usage:
    # Via REST API (requires running query-api + API key)
    python examples/46-live-retrieval-demo.py

    # Via MCP (programmatic, same pipeline)
    python examples/46-live-retrieval-demo.py --mcp
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
import urllib.error

API_BASE = os.environ.get("API_BASE", "http://localhost:8000")
API_KEY = os.environ.get("DEMO_API_KEY", "")


# ---------------------------------------------------------------------------
# REST API demo
# ---------------------------------------------------------------------------

QUERIES = [
    {
        "title": "Natural Language: weekly report generation",
        "body": {"query": "weekly report generation"},
        "expect": "code: _generate_report() + doc: Feature 5 design doc",
    },
    {
        "title": "Python filter: GitHub API rate limit handling",
        "body": {"query": "github API rate limit retry", "languages": ["python"]},
        "expect": "code: test_rate_limit_triggers_retry + doc: error handling spec",
    },
    {
        "title": "TypeScript filter: React dashboard component",
        "body": {"query": "React dashboard component", "languages": ["typescript"]},
        "expect": "code: TypeScript components + doc: Dashboard feature plans",
    },
    {
        "title": "Symbol query: GitHubService (auto-detected)",
        "body": {"query": "GitHubService"},
        "expect": "code: class GitHubService definition with high BM25 score",
    },
    {
        "title": "Documentation: how to deploy with Docker",
        "body": {"query": "how to deploy with Docker"},
        "expect": "doc: Feature 29 Docker deployment plan",
    },
    {
        "title": "Schema search: database model project",
        "body": {"query": "database model project schema", "languages": ["python"]},
        "expect": "code: ProjectBase/Project pydantic schemas + doc: DB test cases",
    },
]


def query_rest(body: dict) -> dict:
    """Send a query to the REST API and return the parsed response."""
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{API_BASE}/api/v1/query",
        data=data,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": API_KEY,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "detail": e.read().decode()[:200]}


def print_result(result: dict, expect: str) -> None:
    """Pretty-print a query result."""
    qt = result.get("query_type", "?")
    degraded = result.get("degraded", False)
    code = result.get("code_results", [])
    docs = result.get("doc_results", [])

    status = "DEGRADED" if degraded else "OK"
    print(f"  [{status}] type={qt}  code_results={len(code)}  doc_results={len(docs)}")

    for i, r in enumerate(code[:2]):
        sym = r.get("symbol", "-")
        lang = r.get("language", "-")
        score = r["relevance_score"]
        snippet = r["content"][:80].replace("\n", " ")
        print(f"  [code {i+1}] {r['file_path']}::{sym}  {lang}  score={score:.4f}")
        print(f"            {snippet}...")

    for i, r in enumerate(docs[:2]):
        score = r["relevance_score"]
        snippet = r["content"][:80].replace("\n", " ")
        print(f"  [doc  {i+1}] {r['file_path']}  score={score:.4f}")
        print(f"            {snippet}...")

    if result.get("error"):
        print(f"  ERROR: {result['error']} — {result.get('detail', '')}")

    print(f"  Expected: {expect}")


def run_rest_demo():
    """Run the REST API demo."""
    print("=" * 72)
    print("  Code Context Retrieval — Live Retrieval Demo (REST API)")
    print("  Pipeline: BM25 + Vector(text-embedding-v3) + RRF + qwen3-rerank")
    print("  Repository: suriyel/githubtrends (2071 chunks)")
    print("=" * 72)

    # Check health
    try:
        with urllib.request.urlopen(f"{API_BASE}/api/v1/health", timeout=5) as resp:
            health = json.loads(resp.read())
            svcs = health.get("services", {})
            print(f"\n  Health: {health['status']}  ES={svcs.get('elasticsearch')} "
                  f"Qdrant={svcs.get('qdrant')} Redis={svcs.get('redis')}")
    except Exception as e:
        print(f"\n  Health check failed: {e}")
        print("  Start the API first: uvicorn --factory src.query.main:build_app --port 8000")
        return

    for q in QUERIES:
        print(f"\n--- {q['title']} ---")
        result = query_rest(q["body"])
        print_result(result, q["expect"])

    print("\n" + "=" * 72)


# ---------------------------------------------------------------------------
# MCP demo
# ---------------------------------------------------------------------------

def run_mcp_demo():
    """Run the MCP tool-call demo (programmatic, same pipeline)."""
    # Clear proxy for localhost access
    for k in ("ALL_PROXY", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY",
              "http_proxy", "https_proxy"):
        os.environ.pop(k, None)

    import asyncio

    async def demo():
        from src.shared.database import get_engine, get_session_factory
        from src.shared.clients.elasticsearch import ElasticsearchClient
        from src.shared.clients.qdrant import QdrantClientWrapper
        from src.shared.clients.redis import RedisClient
        from src.indexing.embedding_encoder import EmbeddingEncoder
        from src.query.retriever import Retriever
        from src.query.rank_fusion import RankFusion
        from src.query.reranker import Reranker
        from src.query.response_builder import ResponseBuilder
        from src.query.query_handler import QueryHandler
        from src.query.mcp_server import create_mcp_server

        es = ElasticsearchClient(url=os.environ["ELASTICSEARCH_URL"])
        qdrant = QdrantClientWrapper(url=os.environ["QDRANT_URL"])
        redis = RedisClient(url=os.environ["REDIS_URL"])
        engine = get_engine(os.environ["DATABASE_URL"])
        sf = get_session_factory(engine)
        await es.connect(); await qdrant.connect(); await redis.connect()

        encoder = EmbeddingEncoder()
        handler = QueryHandler(
            retriever=Retriever(es_client=es, qdrant_client=qdrant, embedding_encoder=encoder),
            rank_fusion=RankFusion(), reranker=Reranker(), response_builder=ResponseBuilder(),
            search_timeout=5.0, pipeline_timeout=15.0)

        mcp = create_mcp_server(handler, sf, es)
        tools = mcp._tool_manager._tools
        search = tools["search_code_context"].fn
        list_repos = tools["list_repositories"].fn

        print("=" * 72)
        print("  Code Context Retrieval — MCP Tool-Call Demo")
        print("  AI Agent --stdio--> MCP Server ---> QueryHandler")
        print("=" * 72)

        print("\n  MCP: list_repositories()")
        repos = json.loads(await list_repos())
        for r in repos:
            b = r.get("indexed_branch") or r.get("default_branch") or "-"
            print(f"    {r['name']}  status={r['status']}  branch={b}")

        for q in QUERIES:
            print(f"\n--- MCP: search_code_context({q['body']}) ---")
            try:
                r = json.loads(await search(**q["body"]))
                qt = r.get("query_type", "?")
                code = r.get("code_results", [])
                docs = r.get("doc_results", [])
                print(f"  type={qt}  code={len(code)}  doc={len(docs)}")
                for i, c in enumerate(code[:2]):
                    print(f"  [code {i+1}] {c['file_path']}::{c.get('symbol','-')}  "
                          f"score={c['relevance_score']:.4f}")
                for i, d in enumerate(docs[:1]):
                    print(f"  [doc  {i+1}] {d['file_path']}  score={d['relevance_score']:.4f}")
            except Exception as e:
                print(f"  Error: {e}")

        print("\n" + "=" * 72)
        await es.close(); await qdrant.close(); await redis.close(); await engine.dispose()

    asyncio.run(demo())


if __name__ == "__main__":
    if "--mcp" in sys.argv:
        run_mcp_demo()
    else:
        if not API_KEY:
            print("Set DEMO_API_KEY environment variable to your API key.")
            print("  export DEMO_API_KEY=<your-key>")
            sys.exit(1)
        run_rest_demo()
