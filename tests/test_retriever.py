"""Tests for Retriever — BM25 keyword search (Feature #8).

Test layers:
- [unit] tests: mock ElasticsearchClient._client for deterministic BM25 results
- [integration] tests: real Elasticsearch via @pytest.mark.real

Security: N/A — internal query component, no direct user-facing input
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.shared.clients.elasticsearch import ElasticsearchClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_es_hit(
    chunk_id: str,
    score: float,
    source: dict,
) -> dict:
    """Build a single ES search hit dict."""
    return {"_id": chunk_id, "_score": score, "_source": source}


def _code_source(
    repo_id: str = "r1",
    file_path: str = "src/Main.java",
    language: str = "java",
    chunk_type: str = "function",
    symbol: str = "getUserName",
    signature: str = "public String getUserName()",
    doc_comment: str = "",
    content: str = "public String getUserName() { return name; }",
    line_start: int = 10,
    line_end: int = 12,
    parent_class: str = "User",
    branch: str = "main",
) -> dict:
    return {
        "repo_id": repo_id,
        "file_path": file_path,
        "language": language,
        "chunk_type": chunk_type,
        "symbol": symbol,
        "signature": signature,
        "doc_comment": doc_comment,
        "content": content,
        "line_start": line_start,
        "line_end": line_end,
        "parent_class": parent_class,
        "branch": branch,
    }


def _doc_source(
    repo_id: str = "r1",
    file_path: str = "docs/README.md",
    breadcrumb: str = "docs/README.md > Getting Started",
    content: str = "Configure timeout settings for the WebClient.",
    heading_level: int = 2,
) -> dict:
    return {
        "repo_id": repo_id,
        "file_path": file_path,
        "breadcrumb": breadcrumb,
        "content": content,
        "heading_level": heading_level,
    }


def _mock_es_search_response(hits: list[dict]) -> dict:
    """Build a mock ES search response."""
    return {"hits": {"hits": hits, "total": {"value": len(hits)}}}


@pytest.fixture
def es_client() -> ElasticsearchClient:
    """ElasticsearchClient with mocked internal _client."""
    client = ElasticsearchClient.__new__(ElasticsearchClient)
    client._url = "http://localhost:9200"
    client._client = AsyncMock()
    return client


# ---------------------------------------------------------------------------
# T1: Happy path — bm25_code_search returns matching chunks by symbol
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bm25_code_search_returns_matching_chunks(es_client):
    """VS-1: Given indexed code chunks with 'getUserName', bm25_search returns
    them ranked by BM25 score with content_type='code'."""
    from src.query.retriever import Retriever

    hits = [
        _make_es_hit("c1", 5.2, _code_source(symbol="getUserName", content="public String getUserName() { return name; }")),
        _make_es_hit("c2", 3.1, _code_source(symbol="getUserName", content="String getUserName = user.getName();")),
        _make_es_hit("c3", 1.8, _code_source(symbol="setUserName", content="void setUserName(String n) { this.name = n; }")),
    ]
    es_client._client.search = AsyncMock(return_value=_mock_es_search_response(hits))

    retriever = Retriever(es_client)
    results = await retriever.bm25_code_search("getUserName", "r1")

    assert len(results) == 3
    assert results[0].chunk_id == "c1"
    assert results[0].score == 5.2
    assert results[1].chunk_id == "c2"
    assert results[1].score == 3.1
    assert results[2].chunk_id == "c3"
    assert results[2].score == 1.8
    for r in results:
        assert r.content_type == "code"
        assert r.repo_id == "r1"


# ---------------------------------------------------------------------------
# T2: Happy path — synonym expansion (auth → authentication/authorization)
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bm25_code_search_synonym_expansion(es_client):
    """VS-2: When searching 'auth', results include chunks with
    'authentication' and 'authorization' (synonym filter in ES)."""
    from src.query.retriever import Retriever

    hits = [
        _make_es_hit("c1", 4.0, _code_source(symbol="authenticate", content="def authenticate(user): ...")),
        _make_es_hit("c2", 3.5, _code_source(symbol="authorize", content="def authorize(token): ...")),
    ]
    es_client._client.search = AsyncMock(return_value=_mock_es_search_response(hits))

    retriever = Retriever(es_client)
    results = await retriever.bm25_code_search("auth", "r1")

    # Synonym expansion is handled by ES analyzer, so we verify the query
    # is sent and results are returned correctly
    assert len(results) == 2
    assert results[0].chunk_id == "c1"
    assert results[1].chunk_id == "c2"
    # Verify the query was sent to ES (synonym matching happens server-side)
    es_client._client.search.assert_called_once()
    call_kwargs = es_client._client.search.call_args
    assert call_kwargs is not None


# ---------------------------------------------------------------------------
# T3: Happy path — top_k limits results
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bm25_code_search_respects_top_k(es_client):
    """FR-006 AC1: top_k=3 limits results to at most 3."""
    from src.query.retriever import Retriever

    hits = [
        _make_es_hit("c1", 5.0, _code_source()),
        _make_es_hit("c2", 4.0, _code_source()),
        _make_es_hit("c3", 3.0, _code_source()),
    ]
    es_client._client.search = AsyncMock(return_value=_mock_es_search_response(hits))

    retriever = Retriever(es_client)
    results = await retriever.bm25_code_search("test", "r1", top_k=3)

    assert len(results) == 3
    # Verify size=3 was passed to ES
    call_kwargs = es_client._client.search.call_args
    assert call_kwargs.kwargs.get("size") == 3 or call_kwargs[1].get("size") == 3


# ---------------------------------------------------------------------------
# T4: Happy path — bm25_doc_search returns doc chunks
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bm25_doc_search_returns_doc_chunks(es_client):
    """bm25_doc_search returns ScoredChunks with content_type='doc'."""
    from src.query.retriever import Retriever

    hits = [
        _make_es_hit("d1", 4.5, _doc_source(content="Configure timeout settings")),
        _make_es_hit("d2", 2.3, _doc_source(content="Timeout defaults are 30s")),
    ]
    es_client._client.search = AsyncMock(return_value=_mock_es_search_response(hits))

    retriever = Retriever(es_client)
    results = await retriever.bm25_doc_search("timeout config", "r1")

    assert len(results) == 2
    for r in results:
        assert r.content_type == "doc"
        assert r.repo_id == "r1"
    assert results[0].chunk_id == "d1"
    assert results[0].breadcrumb == "docs/README.md > Getting Started"
    assert results[0].heading_level == 2
    assert results[1].chunk_id == "d2"


# ---------------------------------------------------------------------------
# T5: Happy path — language filter
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bm25_code_search_filters_by_language(es_client):
    """Languages filter: only Python chunks returned when languages=['python']."""
    from src.query.retriever import Retriever

    hits = [
        _make_es_hit("c1", 3.0, _code_source(language="python")),
    ]
    es_client._client.search = AsyncMock(return_value=_mock_es_search_response(hits))

    retriever = Retriever(es_client)
    results = await retriever.bm25_code_search("test", "r1", languages=["python"])

    assert len(results) == 1
    assert results[0].language == "python"
    # Verify the language filter was included in the ES query
    call_kwargs = es_client._client.search.call_args
    body = call_kwargs.kwargs.get("body") or call_kwargs[1].get("body")
    filters = body["query"]["bool"]["filter"]
    lang_filter = [f for f in filters if "terms" in f and "language" in f["terms"]]
    assert len(lang_filter) == 1
    assert lang_filter[0]["terms"]["language"] == ["python"]


# ---------------------------------------------------------------------------
# T6: Error — ES ConnectionError raises RetrievalError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bm25_code_search_raises_retrieval_error_on_connection_error(es_client):
    """VS-4: When ES is unreachable, raises RetrievalError."""
    from elasticsearch import ConnectionError as ESConnectionError

    from src.query.exceptions import RetrievalError
    from src.query.retriever import Retriever

    es_client._client.search = AsyncMock(side_effect=ESConnectionError("connection refused"))

    retriever = Retriever(es_client)
    with pytest.raises(RetrievalError, match="Elasticsearch search failed"):
        await retriever.bm25_code_search("test", "r1")


# ---------------------------------------------------------------------------
# T7: Error — ES TransportError raises RetrievalError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bm25_code_search_raises_retrieval_error_on_transport_error(es_client):
    """TransportError (timeout, 5xx) also raises RetrievalError."""
    from elasticsearch import TransportError

    from src.query.exceptions import RetrievalError
    from src.query.retriever import Retriever

    es_client._client.search = AsyncMock(side_effect=TransportError(500, "Internal Server Error"))

    retriever = Retriever(es_client)
    with pytest.raises(RetrievalError, match="Elasticsearch search failed"):
        await retriever.bm25_code_search("query", "r1")


# ---------------------------------------------------------------------------
# T8: Error — empty query raises ValueError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bm25_code_search_raises_value_error_on_empty_query(es_client):
    """Empty query string raises ValueError."""
    from src.query.retriever import Retriever

    retriever = Retriever(es_client)
    with pytest.raises(ValueError, match="query must not be empty"):
        await retriever.bm25_code_search("", "r1")


# ---------------------------------------------------------------------------
# T9: Boundary — no matching chunks returns empty list
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bm25_code_search_returns_empty_on_no_match(es_client):
    """VS-3: No matching terms returns empty list without error."""
    from src.query.retriever import Retriever

    es_client._client.search = AsyncMock(return_value=_mock_es_search_response([]))

    retriever = Retriever(es_client)
    results = await retriever.bm25_code_search("nonexistent_symbol_xyz", "r1")

    assert results == []


# ---------------------------------------------------------------------------
# T10: Boundary — single-char query works
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bm25_code_search_single_char_query(es_client):
    """1-char query executes normally."""
    from src.query.retriever import Retriever

    hits = [_make_es_hit("c1", 1.0, _code_source())]
    es_client._client.search = AsyncMock(return_value=_mock_es_search_response(hits))

    retriever = Retriever(es_client)
    results = await retriever.bm25_code_search("a", "r1")

    assert len(results) == 1
    assert results[0].chunk_id == "c1"


# ---------------------------------------------------------------------------
# T11: Boundary — empty languages list behaves as None (no filter)
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bm25_code_search_empty_languages_list(es_client):
    """Empty languages list [] behaves same as None — no language filter."""
    from src.query.retriever import Retriever

    hits = [_make_es_hit("c1", 2.0, _code_source(language="java"))]
    es_client._client.search = AsyncMock(return_value=_mock_es_search_response(hits))

    retriever = Retriever(es_client)
    results = await retriever.bm25_code_search("test", "r1", languages=[])

    assert len(results) == 1
    # Verify no language filter in query
    call_kwargs = es_client._client.search.call_args
    body = call_kwargs.kwargs.get("body") or call_kwargs[1].get("body")
    filters = body["query"]["bool"]["filter"]
    lang_filters = [f for f in filters if "terms" in f and "language" in f["terms"]]
    assert len(lang_filters) == 0


# ---------------------------------------------------------------------------
# T12: Boundary — top_k=1 returns exactly 1 result
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bm25_code_search_top_k_one(es_client):
    """top_k=1 returns at most 1 result."""
    from src.query.retriever import Retriever

    hits = [_make_es_hit("c1", 5.0, _code_source())]
    es_client._client.search = AsyncMock(return_value=_mock_es_search_response(hits))

    retriever = Retriever(es_client)
    results = await retriever.bm25_code_search("test", "r1", top_k=1)

    assert len(results) == 1
    call_kwargs = es_client._client.search.call_args
    assert call_kwargs.kwargs.get("size") == 1 or call_kwargs[1].get("size") == 1


# ---------------------------------------------------------------------------
# T13: Happy path — ScoredChunk fields populated correctly
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bm25_code_search_scored_chunk_fields(es_client):
    """All ScoredChunk fields are correctly mapped from ES hit."""
    from src.query.retriever import Retriever

    source = _code_source(
        repo_id="repo-42",
        file_path="src/auth/Login.java",
        language="java",
        chunk_type="function",
        symbol="authenticate",
        signature="public boolean authenticate(String user, String pass)",
        doc_comment="Authenticates a user",
        content="public boolean authenticate(String u, String p) { ... }",
        line_start=25,
        line_end=40,
        parent_class="LoginService",
    )
    hits = [_make_es_hit("chunk-99", 7.3, source)]
    es_client._client.search = AsyncMock(return_value=_mock_es_search_response(hits))

    retriever = Retriever(es_client)
    results = await retriever.bm25_code_search("authenticate", "repo-42")

    assert len(results) == 1
    chunk = results[0]
    assert chunk.chunk_id == "chunk-99"
    assert chunk.content_type == "code"
    assert chunk.repo_id == "repo-42"
    assert chunk.file_path == "src/auth/Login.java"
    assert chunk.content == "public boolean authenticate(String u, String p) { ... }"
    assert chunk.score == 7.3
    assert chunk.language == "java"
    assert chunk.chunk_type == "function"
    assert chunk.symbol == "authenticate"
    assert chunk.signature == "public boolean authenticate(String user, String pass)"
    assert chunk.doc_comment == "Authenticates a user"
    assert chunk.line_start == 25
    assert chunk.line_end == 40
    assert chunk.parent_class == "LoginService"


# ---------------------------------------------------------------------------
# T14: Error — whitespace-only query raises ValueError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bm25_code_search_whitespace_only_query(es_client):
    """Whitespace-only query raises ValueError."""
    from src.query.retriever import Retriever

    retriever = Retriever(es_client)
    with pytest.raises(ValueError, match="query must not be empty"):
        await retriever.bm25_code_search("   ", "r1")


# ---------------------------------------------------------------------------
# T7b: Error — ES NotFoundError (index missing) raises RetrievalError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bm25_code_search_raises_retrieval_error_on_not_found(es_client):
    """NotFoundError (index not found) also raises RetrievalError."""
    from elasticsearch import NotFoundError

    from src.query.exceptions import RetrievalError
    from src.query.retriever import Retriever

    es_client._client.search = AsyncMock(
        side_effect=NotFoundError(
            message="index_not_found_exception",
            meta=MagicMock(status=404),
            body={"error": {"type": "index_not_found_exception"}},
        )
    )

    retriever = Retriever(es_client)
    with pytest.raises(RetrievalError, match="Elasticsearch search failed"):
        await retriever.bm25_code_search("test", "r1")


# ---------------------------------------------------------------------------
# T8b: Error — bm25_doc_search empty query raises ValueError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bm25_doc_search_raises_value_error_on_empty_query(es_client):
    """bm25_doc_search also validates empty query."""
    from src.query.retriever import Retriever

    retriever = Retriever(es_client)
    with pytest.raises(ValueError, match="query must not be empty"):
        await retriever.bm25_doc_search("", "r1")


# ---------------------------------------------------------------------------
# T6b: Error — bm25_doc_search also raises RetrievalError on ES failure
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bm25_doc_search_raises_retrieval_error_on_connection_error(es_client):
    """bm25_doc_search also wraps ES errors in RetrievalError."""
    from elasticsearch import ConnectionError as ESConnectionError

    from src.query.exceptions import RetrievalError
    from src.query.retriever import Retriever

    es_client._client.search = AsyncMock(side_effect=ESConnectionError("refused"))

    retriever = Retriever(es_client)
    with pytest.raises(RetrievalError, match="Elasticsearch search failed"):
        await retriever.bm25_doc_search("test", "r1")


# ---------------------------------------------------------------------------
# T4b: Happy path — doc chunk ScoredChunk fields
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bm25_doc_search_scored_chunk_fields(es_client):
    """Doc ScoredChunk has correct doc-specific fields and None code fields."""
    from src.query.retriever import Retriever

    source = _doc_source(
        repo_id="r2",
        file_path="docs/guide.md",
        breadcrumb="docs/guide.md > Configuration > Timeouts",
        content="Set timeout to 30 seconds.",
        heading_level=3,
    )
    hits = [_make_es_hit("doc-1", 3.7, source)]
    es_client._client.search = AsyncMock(return_value=_mock_es_search_response(hits))

    retriever = Retriever(es_client)
    results = await retriever.bm25_doc_search("timeout", "r2")

    assert len(results) == 1
    chunk = results[0]
    assert chunk.chunk_id == "doc-1"
    assert chunk.content_type == "doc"
    assert chunk.repo_id == "r2"
    assert chunk.file_path == "docs/guide.md"
    assert chunk.breadcrumb == "docs/guide.md > Configuration > Timeouts"
    assert chunk.heading_level == 3
    assert chunk.content == "Set timeout to 30 seconds."
    assert chunk.score == 3.7
    # Code-specific fields should be None
    assert chunk.language is None
    assert chunk.symbol is None
    assert chunk.line_start is None


# ---------------------------------------------------------------------------
# Real tests — @pytest.mark.real (integration with real Elasticsearch)
# ---------------------------------------------------------------------------

@pytest.mark.real
@pytest.mark.asyncio
async def test_real_es_bm25_code_search():
    """[integration] Real Elasticsearch: index a code chunk and search for it."""
    import os

    from elastic_transport import ConnectionTimeout

    from src.query.exceptions import RetrievalError
    from src.query.retriever import Retriever

    es_url = os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200")
    es_client = ElasticsearchClient(es_url)
    await es_client.connect()

    try:
        # Ensure cluster is reachable
        healthy = await es_client.health_check()
        if not healthy:
            pytest.skip("Elasticsearch not available")

        test_index = "test_code_chunks_feat8"
        # Clean up any leftover test data
        try:
            await es_client._client.indices.delete(index=test_index, ignore_unavailable=True)
        except Exception:
            pass

        # Create index with a simple mapping
        try:
            await es_client._client.indices.create(
                index=test_index,
                body={
                    "mappings": {
                        "properties": {
                            "repo_id": {"type": "keyword"},
                            "file_path": {"type": "text"},
                            "language": {"type": "keyword"},
                            "chunk_type": {"type": "keyword"},
                            "symbol": {"type": "text"},
                            "signature": {"type": "text"},
                            "doc_comment": {"type": "text"},
                            "content": {"type": "text"},
                            "line_start": {"type": "integer"},
                            "line_end": {"type": "integer"},
                            "parent_class": {"type": "text"},
                            "branch": {"type": "keyword"},
                        }
                    }
                },
            )
        except (ConnectionTimeout, Exception) as exc:
            if "ConnectionTimeout" in type(exc).__name__:
                pytest.skip("Elasticsearch timed out on index creation")
            raise

        # Index a test document
        await es_client._client.index(
            index=test_index,
            id="real-chunk-1",
            body=_code_source(symbol="getUserName", content="public String getUserName() { return this.name; }"),
            refresh="wait_for",
        )

        # Search using Retriever (override index name for test)
        retriever = Retriever(es_client, code_index=test_index)
        results = await retriever.bm25_code_search("getUserName", "r1")

        assert len(results) >= 1
        assert results[0].chunk_id == "real-chunk-1"
        assert results[0].content_type == "code"
        assert "getUserName" in results[0].content
        assert results[0].score > 0

    finally:
        # Cleanup
        try:
            await es_client._client.indices.delete(index=test_index, ignore_unavailable=True)
        except Exception:
            pass
        await es_client.close()


@pytest.mark.real
@pytest.mark.asyncio
async def test_real_es_bm25_doc_search():
    """[integration] Real Elasticsearch: index a doc chunk and search for it."""
    import os

    from elastic_transport import ConnectionTimeout

    from src.query.retriever import Retriever

    es_url = os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200")
    es_client = ElasticsearchClient(es_url)
    await es_client.connect()

    try:
        healthy = await es_client.health_check()
        if not healthy:
            pytest.skip("Elasticsearch not available")

        test_index = "test_doc_chunks_feat8"
        try:
            await es_client._client.indices.delete(index=test_index, ignore_unavailable=True)
        except Exception:
            pass

        try:
            await es_client._client.indices.create(
                index=test_index,
                body={
                    "mappings": {
                        "properties": {
                            "repo_id": {"type": "keyword"},
                            "file_path": {"type": "text"},
                            "breadcrumb": {"type": "text"},
                            "content": {"type": "text"},
                            "heading_level": {"type": "integer"},
                        }
                    }
                },
            )
        except (ConnectionTimeout, Exception) as exc:
            if "ConnectionTimeout" in type(exc).__name__:
                pytest.skip("Elasticsearch timed out on index creation")
            raise

        await es_client._client.index(
            index=test_index,
            id="real-doc-1",
            body=_doc_source(content="Configure timeout settings for the HTTP client"),
            refresh="wait_for",
        )

        retriever = Retriever(es_client, doc_index=test_index)
        results = await retriever.bm25_doc_search("timeout", "r1")

        assert len(results) >= 1
        assert results[0].chunk_id == "real-doc-1"
        assert results[0].content_type == "doc"
        assert "timeout" in results[0].content.lower()
        assert results[0].score > 0

    finally:
        try:
            await es_client._client.indices.delete(index=test_index, ignore_unavailable=True)
        except Exception:
            pass
        await es_client.close()
