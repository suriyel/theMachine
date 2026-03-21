"""Real integration tests for Repository-Scoped Query (Feature #15).

These tests run against real Elasticsearch and Qdrant instances.
No mocks on primary dependencies.

External dependencies tested:
- Elasticsearch: BM25 search with repo_id filter and without (None)
- Qdrant: vector search with query_filter=None accepted by client

Requires:
- ELASTICSEARCH_URL env var pointing to a live ES instance
- QDRANT_URL env var pointing to a live Qdrant instance
"""

from __future__ import annotations

import os

# Clear SOCKS proxy before any aiohttp/httpx imports — aiohttp ignores NO_PROXY for SOCKS.
# See env-guide.md "Proxy Configuration" section.
for _k in ("ALL_PROXY", "all_proxy"):
    os.environ.pop(_k, None)
os.environ.setdefault("NO_PROXY", "localhost,127.0.0.1")
os.environ.setdefault("no_proxy", "localhost,127.0.0.1")

import uuid

import pytest
from elasticsearch import AsyncElasticsearch

ELASTICSEARCH_URL = os.environ.get("ELASTICSEARCH_URL", "")
QDRANT_URL = os.environ.get("QDRANT_URL", "")

pytestmark = [
    pytest.mark.real,
    pytest.mark.skipif(not ELASTICSEARCH_URL, reason="ELASTICSEARCH_URL not set"),
]

TEST_INDEX = f"test_repo_scoped_{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def es_setup():
    """Create ES client, temp index with test docs. Clean up unconditionally after."""
    es = AsyncElasticsearch(hosts=[ELASTICSEARCH_URL], request_timeout=120)

    try:
        # Create index: 1 shard, 0 replicas (single-node, avoids unassigned shards).
        # See env-guide.md "Test Index Cleanup" section.
        await es.indices.create(
            index=TEST_INDEX,
            settings={"number_of_shards": 1, "number_of_replicas": 0},
            mappings={
                "properties": {
                    "repo_id": {"type": "keyword"},
                    "file_path": {"type": "text"},
                    "content": {"type": "text"},
                    "symbol": {"type": "text", "fields": {"raw": {"type": "keyword"}}},
                    "signature": {"type": "text"},
                    "doc_comment": {"type": "text"},
                    "language": {"type": "keyword"},
                    "chunk_type": {"type": "keyword"},
                    "line_start": {"type": "integer"},
                    "line_end": {"type": "integer"},
                    "parent_class": {"type": "keyword"},
                }
            },
        )

        # Wait for shard to be active before indexing
        await es.cluster.health(index=TEST_INDEX, wait_for_status="green", timeout="30s")

        # Index test documents from different repos
        docs = [
            {"repo_id": "spring-framework", "file_path": "src/TimeoutHandler.java",
             "content": "void handleTimeout() { /* timeout logic */ }", "symbol": "handleTimeout",
             "signature": "void handleTimeout()", "doc_comment": "Handles request timeouts",
             "language": "java", "chunk_type": "function", "line_start": 10, "line_end": 15,
             "parent_class": "TimeoutHandler"},
            {"repo_id": "django", "file_path": "src/timeout_handler.py",
             "content": "def handle_timeout(): pass  # timeout handler", "symbol": "handle_timeout",
             "signature": "def handle_timeout()", "doc_comment": "Python timeout handler",
             "language": "python", "chunk_type": "function", "line_start": 1, "line_end": 2,
             "parent_class": None},
            {"repo_id": "spring-framework", "file_path": "src/ConnectionPool.java",
             "content": "void configureTimeout(int ms) { this.timeout = ms; }", "symbol": "configureTimeout",
             "signature": "void configureTimeout(int ms)", "doc_comment": "Configure connection timeout",
             "language": "java", "chunk_type": "function", "line_start": 20, "line_end": 22,
             "parent_class": "ConnectionPool"},
        ]
        for i, doc in enumerate(docs):
            await es.index(index=TEST_INDEX, id=str(i), document=doc)
        await es.indices.refresh(index=TEST_INDEX)

        # Build retriever pointing at test index
        from src.shared.clients.elasticsearch import ElasticsearchClient
        from src.query.retriever import Retriever

        client = ElasticsearchClient(ELASTICSEARCH_URL)
        client._client = es
        retriever = Retriever(es_client=client, code_index=TEST_INDEX)

        yield retriever
    finally:
        # MANDATORY cleanup — leaked indices cause cluster red.
        await es.indices.delete(index=TEST_INDEX, ignore=[404])
        await es.close()


# ===========================================================================
# Elasticsearch real tests
# ===========================================================================


# [integration] RT-01: BM25 search with repo_id filter returns only that repo
@pytest.mark.asyncio
async def test_bm25_with_repo_filter_real_es(es_setup):
    """VS-1: Real ES — repo_id filter restricts results to specified repo."""
    results = await es_setup.bm25_code_search("timeout", repo_id="spring-framework", top_k=10)
    assert len(results) >= 1
    for chunk in results:
        assert chunk.repo_id == "spring-framework"
        assert chunk.content_type == "code"


# [integration] RT-02: BM25 search without repo_id returns all repos
@pytest.mark.asyncio
async def test_bm25_without_repo_filter_real_es(es_setup):
    """VS-3: Real ES — no repo filter returns results from all repos."""
    results = await es_setup.bm25_code_search("timeout", repo_id=None, top_k=10)
    assert len(results) >= 2
    repo_ids = {chunk.repo_id for chunk in results}
    assert len(repo_ids) >= 2


# [integration] RT-03: BM25 search with non-existent repo returns empty
@pytest.mark.asyncio
async def test_bm25_nonexistent_repo_real_es(es_setup):
    """VS-2: Real ES — non-existent repo returns empty list, no error."""
    results = await es_setup.bm25_code_search("timeout", repo_id="nonexistent-repo-xyz", top_k=10)
    assert results == []


# [integration] RT-04: Query without filter key accepted by real ES
@pytest.mark.asyncio
async def test_query_no_filter_accepted_by_real_es(es_setup):
    """Boundary: ES accepts bool query with no 'filter' key when repo_id=None."""
    query_body = es_setup._build_code_query("timeout", repo_id=None, languages=None, top_k=10)
    assert "filter" not in query_body["query"]["bool"]
    response = await es_setup._es._client.search(index=TEST_INDEX, body=query_body, size=10)
    assert len(response["hits"]["hits"]) >= 2


# ===========================================================================
# Qdrant real test
# ===========================================================================


@pytest.mark.skipif(not QDRANT_URL, reason="QDRANT_URL not set")
class TestQdrantNoneFilter:
    """Verify Qdrant client accepts query_filter=None."""

    @pytest.mark.asyncio
    async def test_qdrant_accepts_none_filter(self):
        """Boundary: _build_qdrant_filter(None, None) returns None; Qdrant client accepts it."""
        from unittest.mock import MagicMock
        from qdrant_client import AsyncQdrantClient
        from src.query.retriever import Retriever

        r = Retriever(es_client=MagicMock())
        qfilter = r._build_qdrant_filter(repo_id=None, languages=None)
        assert qfilter is None

        client = AsyncQdrantClient(url=QDRANT_URL)
        try:
            await client.query_points(
                collection_name="nonexistent_test_collection",
                query=[0.1] * 1024,
                query_filter=None,
                limit=1,
                with_payload=True,
            )
        except Exception as e:
            error_msg = str(e).lower()
            # "not found" is expected (collection doesn't exist) — but filter-related errors are NOT ok
            assert "filter" not in error_msg, f"Qdrant rejected None filter: {e}"
        await client.close()
