"""Tests for Retriever vector search (Feature #9 — Semantic Retrieval)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, PropertyMock

import numpy as np
import pytest
from grpc import RpcError
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import QueryResponse, ScoredPoint

from src.indexing.exceptions import EmbeddingModelError
from src.query.exceptions import RetrievalError
from src.query.retriever import Retriever
from src.query.scored_chunk import ScoredChunk
from src.shared.clients.elasticsearch import ElasticsearchClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_embedding_encoder() -> MagicMock:
    """Create a mock EmbeddingEncoder that returns a fixed 1024-dim vector."""
    encoder = MagicMock()
    encoder.encode_query = MagicMock(
        return_value=np.ones(1024, dtype=np.float32)
    )
    return encoder


def _make_qdrant_client(points: list[ScoredPoint] | None = None) -> MagicMock:
    """Create a mock QdrantClientWrapper with an async query_points."""
    wrapper = MagicMock()
    inner = AsyncMock()
    inner.query_points = AsyncMock(
        return_value=QueryResponse(points=points or [])
    )
    wrapper._client = inner
    return wrapper


def _make_code_point(
    point_id: str,
    score: float,
    repo_id: str = "repo-1",
    file_path: str = "src/main.py",
    content: str = "def hello(): pass",
    language: str = "python",
    chunk_type: str = "function",
    symbol: str = "hello",
    signature: str = "def hello()",
    doc_comment: str = "Says hello",
    line_start: int = 1,
    line_end: int = 2,
    parent_class: str | None = None,
) -> ScoredPoint:
    return ScoredPoint(
        id=point_id,
        version=1,
        score=score,
        payload={
            "repo_id": repo_id,
            "file_path": file_path,
            "content": content,
            "language": language,
            "chunk_type": chunk_type,
            "symbol": symbol,
            "signature": signature,
            "doc_comment": doc_comment,
            "line_start": line_start,
            "line_end": line_end,
            "parent_class": parent_class,
        },
    )


def _make_doc_point(
    point_id: str,
    score: float,
    repo_id: str = "repo-1",
    file_path: str = "docs/README.md",
    content: str = "# Getting Started",
    breadcrumb: str = "README > Getting Started",
    heading_level: int = 1,
) -> ScoredPoint:
    return ScoredPoint(
        id=point_id,
        version=1,
        score=score,
        payload={
            "repo_id": repo_id,
            "file_path": file_path,
            "content": content,
            "breadcrumb": breadcrumb,
            "heading_level": heading_level,
        },
    )


def _make_retriever(
    points: list[ScoredPoint] | None = None,
    encoder: MagicMock | None = None,
    qdrant: MagicMock | None = None,
) -> tuple[Retriever, MagicMock, MagicMock]:
    """Build a Retriever with mock ES, mock EmbeddingEncoder, mock QdrantClient."""
    es = MagicMock(spec=ElasticsearchClient)
    enc = encoder or _make_embedding_encoder()
    qd = qdrant or _make_qdrant_client(points)
    retriever = Retriever(
        es_client=es,
        embedding_encoder=enc,
        qdrant_client=qd,
    )
    return retriever, enc, qd


# ---------------------------------------------------------------------------
# T01: Happy path — vector_code_search returns ScoredChunks with correct fields
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vector_code_search_returns_scored_chunks():
    """T01: 3 code points → 3 ScoredChunks with correct field mapping."""
    points = [
        _make_code_point("c1", 0.95, symbol="configureTimeout", language="java"),
        _make_code_point("c2", 0.88, symbol="setReadTimeout", language="java"),
        _make_code_point("c3", 0.80, symbol="getClient", language="java"),
    ]
    retriever, enc, qd = _make_retriever(points)

    results = await retriever.vector_code_search("http client timeout", "repo-1")

    assert len(results) == 3
    # Verify first chunk field mapping
    c = results[0]
    assert isinstance(c, ScoredChunk)
    assert c.chunk_id == "c1"
    assert c.content_type == "code"
    assert c.repo_id == "repo-1"
    assert c.file_path == "src/main.py"
    assert c.content == "def hello(): pass"
    assert c.score == 0.95
    assert c.language == "java"
    assert c.symbol == "configureTimeout"
    assert c.chunk_type == "function"
    assert c.signature == "def hello()"
    assert c.doc_comment == "Says hello"
    assert c.line_start == 1
    assert c.line_end == 2
    assert c.parent_class is None
    # Verify EmbeddingEncoder was called
    enc.encode_query.assert_called_once_with("http client timeout")


# ---------------------------------------------------------------------------
# T02: Happy path — returns up to top_k=200
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vector_code_search_returns_up_to_top_k():
    """T02: 200 points → 200 ScoredChunks, limit=200 passed to Qdrant."""
    points = [_make_code_point(f"c{i}", 0.99 - i * 0.001) for i in range(200)]
    retriever, _, qd = _make_retriever(points)

    results = await retriever.vector_code_search("timeout", "repo-1", top_k=200)

    assert len(results) == 200
    # Verify limit was passed to Qdrant
    call_kwargs = qd._client.query_points.call_args
    assert call_kwargs.kwargs.get("limit") == 200 or (
        len(call_kwargs.args) > 0 and call_kwargs.kwargs.get("limit", 200) == 200
    )


# ---------------------------------------------------------------------------
# T03: Happy path — vector_doc_search returns doc chunks
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vector_doc_search_returns_doc_chunks():
    """T03: 5 doc points → 5 ScoredChunks with content_type='doc'."""
    points = [
        _make_doc_point(f"d{i}", 0.90 - i * 0.01, breadcrumb=f"Section {i}")
        for i in range(5)
    ]
    retriever, _, _ = _make_retriever(points)

    results = await retriever.vector_doc_search("getting started", "repo-1")

    assert len(results) == 5
    for r in results:
        assert r.content_type == "doc"
    # Verify doc-specific fields
    assert results[0].breadcrumb == "Section 0"
    assert results[0].heading_level == 1
    assert results[0].file_path == "docs/README.md"
    # Verify code-specific fields are None
    assert results[0].language is None
    assert results[0].symbol is None
    assert results[0].chunk_type is None


# ---------------------------------------------------------------------------
# T04: Happy path — language filter applied to Qdrant
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vector_code_search_with_language_filter():
    """T04: languages=['python','java'] → Qdrant filter includes MatchAny."""
    retriever, _, qd = _make_retriever([])

    await retriever.vector_code_search("timeout", "repo-1", languages=["python", "java"])

    call_kwargs = qd._client.query_points.call_args.kwargs
    qfilter = call_kwargs["query_filter"]
    # Filter must have a condition matching languages
    filter_conditions = qfilter.must
    lang_conditions = [
        c for c in filter_conditions
        if hasattr(c, "key") and c.key == "language"
    ]
    assert len(lang_conditions) == 1
    assert set(lang_conditions[0].match.any) == {"python", "java"}


# ---------------------------------------------------------------------------
# T05: Happy path — no language filter when None
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vector_code_search_without_language_filter():
    """T05: languages=None → Qdrant filter has only repo_id."""
    retriever, _, qd = _make_retriever([])

    await retriever.vector_code_search("timeout", "repo-1", languages=None)

    call_kwargs = qd._client.query_points.call_args.kwargs
    qfilter = call_kwargs["query_filter"]
    filter_conditions = qfilter.must
    # Should only have repo_id condition
    lang_conditions = [
        c for c in filter_conditions
        if hasattr(c, "key") and c.key == "language"
    ]
    assert len(lang_conditions) == 0


# ---------------------------------------------------------------------------
# T06: Error — Qdrant unreachable raises RetrievalError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vector_code_search_qdrant_unreachable():
    """T06: Qdrant connection error → RetrievalError + degradation warning logged."""
    qdrant = _make_qdrant_client()
    qdrant._client.query_points = AsyncMock(
        side_effect=ConnectionError("Connection refused")
    )
    retriever, _, _ = _make_retriever(qdrant=qdrant)

    import logging

    with pytest.raises(RetrievalError, match="Qdrant search failed"):
        await retriever.vector_code_search("timeout", "repo-1")


@pytest.mark.asyncio
async def test_vector_code_search_qdrant_unreachable_logs_warning(caplog):
    """T06b: Qdrant unreachable → logs degradation warning per SRS AC-3."""
    import logging

    qdrant = _make_qdrant_client()
    qdrant._client.query_points = AsyncMock(
        side_effect=ConnectionError("Connection refused")
    )
    retriever, _, _ = _make_retriever(qdrant=qdrant)

    with caplog.at_level(logging.WARNING, logger="src.query.retriever"):
        with pytest.raises(RetrievalError):
            await retriever.vector_code_search("timeout", "repo-1")

    assert any("Qdrant unreachable" in rec.message for rec in caplog.records)
    assert any("BM25-only" in rec.message for rec in caplog.records)


# ---------------------------------------------------------------------------
# T07: Error — EmbeddingEncoder fails raises RetrievalError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vector_code_search_embedding_fails():
    """T07: EmbeddingModelError → RetrievalError wrapping."""
    encoder = _make_embedding_encoder()
    encoder.encode_query = MagicMock(
        side_effect=EmbeddingModelError("API timeout")
    )
    retriever, _, _ = _make_retriever(encoder=encoder)

    with pytest.raises(RetrievalError, match="Embedding failed"):
        await retriever.vector_code_search("timeout", "repo-1")


# ---------------------------------------------------------------------------
# T08: Error — empty query raises ValueError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vector_code_search_empty_query():
    """T08: Empty string → ValueError."""
    retriever, _, _ = _make_retriever()

    with pytest.raises(ValueError, match="query must not be empty"):
        await retriever.vector_code_search("", "repo-1")


# ---------------------------------------------------------------------------
# T09: Error — whitespace-only query raises ValueError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vector_code_search_whitespace_query():
    """T09: Whitespace-only string → ValueError."""
    retriever, _, _ = _make_retriever()

    with pytest.raises(ValueError, match="query must not be empty"):
        await retriever.vector_code_search("   ", "repo-1")


# ---------------------------------------------------------------------------
# T10: Boundary — empty Qdrant results → empty list
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vector_code_search_no_results():
    """T10: 0 points returned → empty list."""
    retriever, _, _ = _make_retriever([])

    results = await retriever.vector_code_search("nonexistent query", "repo-1")

    assert results == []


# ---------------------------------------------------------------------------
# T11: Boundary — top_k=1 → single result
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vector_code_search_top_k_one():
    """T11: top_k=1 → limit=1 passed to Qdrant."""
    points = [_make_code_point("c1", 0.99)]
    retriever, _, qd = _make_retriever(points)

    results = await retriever.vector_code_search("timeout", "repo-1", top_k=1)

    assert len(results) == 1
    call_kwargs = qd._client.query_points.call_args.kwargs
    assert call_kwargs["limit"] == 1


# ---------------------------------------------------------------------------
# T12: Boundary — empty languages list same as None
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vector_code_search_empty_languages_list():
    """T12: languages=[] → no language filter (same as None)."""
    retriever, _, qd = _make_retriever([])

    await retriever.vector_code_search("timeout", "repo-1", languages=[])

    call_kwargs = qd._client.query_points.call_args.kwargs
    qfilter = call_kwargs["query_filter"]
    lang_conditions = [
        c for c in qfilter.must
        if hasattr(c, "key") and c.key == "language"
    ]
    assert len(lang_conditions) == 0


# ---------------------------------------------------------------------------
# T13: Happy path — repo_id filter present in Qdrant query
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vector_code_search_repo_id_filter():
    """T13: repo_id passed as Qdrant filter condition."""
    retriever, _, qd = _make_retriever([])

    await retriever.vector_code_search("timeout", "repo-42")

    call_kwargs = qd._client.query_points.call_args.kwargs
    qfilter = call_kwargs["query_filter"]
    repo_conditions = [
        c for c in qfilter.must
        if hasattr(c, "key") and c.key == "repo_id"
    ]
    assert len(repo_conditions) == 1
    assert repo_conditions[0].match.value == "repo-42"


# ---------------------------------------------------------------------------
# T14: Error — RpcError raises RetrievalError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vector_code_search_rpc_error():
    """T14: gRPC RpcError → RetrievalError."""

    class FakeRpcError(RpcError):
        def __str__(self):
            return "gRPC unavailable"

    qdrant = _make_qdrant_client()
    qdrant._client.query_points = AsyncMock(side_effect=FakeRpcError())
    retriever, _, _ = _make_retriever(qdrant=qdrant)

    with pytest.raises(RetrievalError, match="Qdrant search failed"):
        await retriever.vector_code_search("timeout", "repo-1")


# ---------------------------------------------------------------------------
# T15: vector_doc_search — empty query raises ValueError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vector_doc_search_empty_query():
    """Verify vector_doc_search also validates empty query."""
    retriever, _, _ = _make_retriever()

    with pytest.raises(ValueError, match="query must not be empty"):
        await retriever.vector_doc_search("", "repo-1")


# ---------------------------------------------------------------------------
# T16: vector_doc_search — Qdrant error wrapping
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vector_doc_search_qdrant_unreachable():
    """Verify vector_doc_search wraps Qdrant errors as RetrievalError."""
    qdrant = _make_qdrant_client()
    qdrant._client.query_points = AsyncMock(
        side_effect=UnexpectedResponse(
            status_code=503, reason_phrase="unavailable", content=b"", headers={}
        )
    )
    retriever, _, _ = _make_retriever(qdrant=qdrant)

    with pytest.raises(RetrievalError, match="Qdrant search failed"):
        await retriever.vector_doc_search("timeout", "repo-1")


# ---------------------------------------------------------------------------
# T17: vector_code_search — UnexpectedResponse raises RetrievalError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vector_code_search_unexpected_response():
    """Verify UnexpectedResponse from Qdrant is caught and wrapped."""
    qdrant = _make_qdrant_client()
    qdrant._client.query_points = AsyncMock(
        side_effect=UnexpectedResponse(
            status_code=500, reason_phrase="internal", content=b"", headers={}
        )
    )
    retriever, _, _ = _make_retriever(qdrant=qdrant)

    with pytest.raises(RetrievalError, match="Qdrant search failed"):
        await retriever.vector_code_search("timeout", "repo-1")


# ---------------------------------------------------------------------------
# Real test — Qdrant connectivity (integration)
# Security: N/A — internal retrieval module with no user-facing input
# ---------------------------------------------------------------------------

@pytest.mark.real
@pytest.mark.asyncio
async def test_qdrant_connectivity_real():
    """[integration] Verify Qdrant client can connect and list collections.

    Requires QDRANT_URL in environment pointing to a running Qdrant instance.
    """
    import os

    from src.shared.clients.qdrant import QdrantClientWrapper

    # Clear proxy env vars that interfere with local Qdrant connections
    proxy_keys = ("ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy",
                  "HTTPS_PROXY", "https_proxy")
    saved: dict[str, str] = {}
    for key in proxy_keys:
        val = os.environ.pop(key, None)
        if val is not None:
            saved[key] = val
    try:
        url = os.environ.get("QDRANT_URL", "http://localhost:6333")
        client = QdrantClientWrapper(url=url)
        await client.connect()
        try:
            healthy = await client.health_check()
            assert healthy is True, f"Qdrant at {url} is not healthy"
        finally:
            await client.close()
    finally:
        os.environ.update(saved)
