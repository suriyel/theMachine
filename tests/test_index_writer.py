"""Tests for IndexWriter — Feature #7 Embedding Generation.

Test layers:
- [unit] Tests use mock ES/Qdrant clients.
- [integration] Real test verifies Qdrant connectivity (marked @pytest.mark.real).

Categories covered:
- Happy path: T3, T6, T7, T8
- Error: T10, T11, T14
- Boundary: T16, T17
- Security: N/A — internal indexing component with no user-facing input
"""

import numpy as np
import pytest
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock, patch, call

from src.indexing.index_writer import IndexWriter
from src.indexing.exceptions import IndexWriteError
from src.indexing.chunker import CodeChunk
from src.indexing.doc_chunker import DocChunk
from src.indexing.rule_extractor import RuleChunk


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_es_client():
    """Mock Elasticsearch client with async bulk/delete_by_query."""
    client = MagicMock()
    client._client = MagicMock()
    client._client.bulk = AsyncMock(return_value={"errors": False, "items": []})
    client._client.delete_by_query = AsyncMock(return_value={"deleted": 5})
    return client


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client with async upsert/delete."""
    client = MagicMock()
    client._client = MagicMock()
    client._client.upsert = AsyncMock(return_value=None)
    client._client.delete = AsyncMock(return_value=None)
    return client


@pytest.fixture
def writer(mock_es_client, mock_qdrant_client):
    """IndexWriter with mocked clients."""
    return IndexWriter(es_client=mock_es_client, qdrant_client=mock_qdrant_client)


def _make_code_chunks(n: int, repo_id: str = "repo-1", branch: str = "main") -> list[CodeChunk]:
    """Helper to create N CodeChunks."""
    return [
        CodeChunk(
            chunk_id=f"{repo_id}:{branch}:file{i}.py:func_{i}:function:{i}",
            repo_id=repo_id,
            branch=branch,
            file_path=f"src/file{i}.py",
            language="python",
            chunk_type="function",
            symbol=f"func_{i}",
            signature=f"def func_{i}():",
            doc_comment=f"Function {i}",
            parent_class="",
            content=f"def func_{i}(): pass",
            line_start=i,
            line_end=i + 5,
        )
        for i in range(n)
    ]


def _make_doc_chunks(n: int, repo_id: str = "repo-1", branch: str = "main") -> list[DocChunk]:
    """Helper to create N DocChunks."""
    return [
        DocChunk(
            chunk_id=f"{repo_id}:{branch}:doc{i}.md:section:0",
            repo_id=repo_id,
            file_path=f"docs/doc{i}.md",
            breadcrumb=f"doc{i}.md > Section",
            content=f"Documentation content {i}",
            code_examples=[],
            content_tokens=50,
            heading_level=2,
        )
        for i in range(n)
    ]


def _make_rule_chunks(n: int, repo_id: str = "repo-1", branch: str = "main") -> list[RuleChunk]:
    """Helper to create N RuleChunks."""
    return [
        RuleChunk(
            chunk_id=f"{repo_id}:{branch}:rule{i}.md",
            repo_id=repo_id,
            file_path=f"rule{i}.md",
            rule_type="agent_rules",
            content=f"Rule content {i}",
        )
        for i in range(n)
    ]


def _make_embeddings(n: int) -> list[np.ndarray]:
    """Helper to create N random 1024-dim float32 vectors."""
    return [np.random.rand(1024).astype(np.float32) for _ in range(n)]


# ---------------------------------------------------------------------------
# T3: Happy path — write_code_chunks stores 100 chunks in ES + Qdrant
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_write_code_chunks_stores_all_in_es_and_qdrant(writer, mock_es_client, mock_qdrant_client):
    """VS-3: 100 chunks + embeddings → all stored in ES code_chunks + Qdrant code_embeddings."""
    chunks = _make_code_chunks(100)
    embeddings = _make_embeddings(100)

    await writer.write_code_chunks(chunks, embeddings, repo_id="repo-1")

    # Verify ES bulk was called with actions for code_chunks index
    mock_es_client._client.bulk.assert_called()
    bulk_call = mock_es_client._client.bulk.call_args
    operations = bulk_call[1].get("operations") or bulk_call[0][0]
    # Should contain index operations for code_chunks
    assert any("code_chunks" in str(op) for op in operations)

    # Verify Qdrant upsert was called for code_embeddings collection
    mock_qdrant_client._client.upsert.assert_called()
    upsert_call = mock_qdrant_client._client.upsert.call_args
    assert upsert_call[1].get("collection_name") == "code_embeddings" or \
           upsert_call[0][0] == "code_embeddings"


# ---------------------------------------------------------------------------
# T6: Happy path — write_doc_chunks to ES doc_chunks + Qdrant doc_embeddings
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_write_doc_chunks_stores_in_correct_indices(writer, mock_es_client, mock_qdrant_client):
    """DocChunks → ES doc_chunks + Qdrant doc_embeddings."""
    chunks = _make_doc_chunks(5)
    embeddings = _make_embeddings(5)

    await writer.write_doc_chunks(chunks, embeddings, repo_id="repo-1")

    mock_es_client._client.bulk.assert_called()
    bulk_call = mock_es_client._client.bulk.call_args
    operations = bulk_call[1].get("operations") or bulk_call[0][0]
    assert any("doc_chunks" in str(op) for op in operations)

    mock_qdrant_client._client.upsert.assert_called()
    upsert_call = mock_qdrant_client._client.upsert.call_args
    assert upsert_call[1].get("collection_name") == "doc_embeddings" or \
           upsert_call[0][0] == "doc_embeddings"


# ---------------------------------------------------------------------------
# T7: Happy path — write_rule_chunks to ES rule_chunks only (no Qdrant)
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_write_rule_chunks_es_only_no_qdrant(writer, mock_es_client, mock_qdrant_client):
    """RuleChunks → ES rule_chunks only, NO Qdrant write (keyword-only per design)."""
    chunks = _make_rule_chunks(3)

    await writer.write_rule_chunks(chunks, repo_id="repo-1")

    mock_es_client._client.bulk.assert_called()
    bulk_call = mock_es_client._client.bulk.call_args
    operations = bulk_call[1].get("operations") or bulk_call[0][0]
    assert any("rule_chunks" in str(op) for op in operations)

    # Qdrant must NOT be called for rule chunks
    mock_qdrant_client._client.upsert.assert_not_called()


# ---------------------------------------------------------------------------
# T8: Happy path — delete_repo_index removes from all indices + collections
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_repo_index_clears_all_stores(writer, mock_es_client, mock_qdrant_client):
    """delete_repo_index removes chunks from all 3 ES indices + 2 Qdrant collections."""
    await writer.delete_repo_index(repo_id="repo-1", branch="main")

    # ES: delete_by_query called for code_chunks, doc_chunks, rule_chunks
    assert mock_es_client._client.delete_by_query.call_count >= 3
    es_calls = [str(c) for c in mock_es_client._client.delete_by_query.call_args_list]
    assert any("code_chunks" in c for c in es_calls)
    assert any("doc_chunks" in c for c in es_calls)
    assert any("rule_chunks" in c for c in es_calls)

    # Qdrant: delete called for code_embeddings, doc_embeddings
    assert mock_qdrant_client._client.delete.call_count >= 2
    qd_calls = [str(c) for c in mock_qdrant_client._client.delete.call_args_list]
    assert any("code_embeddings" in c for c in qd_calls)
    assert any("doc_embeddings" in c for c in qd_calls)


# ---------------------------------------------------------------------------
# T10: Error — Qdrant unreachable, retry 3x then IndexWriteError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_write_code_chunks_qdrant_unreachable_retries_and_fails(writer, mock_es_client, mock_qdrant_client):
    """FR-005 AC-4: Qdrant unreachable → retry 3x with backoff → IndexWriteError."""
    from qdrant_client.http.exceptions import UnexpectedResponse
    mock_qdrant_client._client.upsert = AsyncMock(
        side_effect=ConnectionError("Connection refused")
    )

    chunks = _make_code_chunks(5)
    embeddings = _make_embeddings(5)

    with pytest.raises(IndexWriteError, match="failed after 3 retries"):
        await writer.write_code_chunks(chunks, embeddings, repo_id="repo-1")

    # Should have retried 3 times
    assert mock_qdrant_client._client.upsert.call_count == 3


# ---------------------------------------------------------------------------
# T11: Error — ES unreachable, retry 3x then IndexWriteError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_write_code_chunks_es_unreachable_retries_and_fails(writer, mock_es_client, mock_qdrant_client):
    """ES unreachable → retry 3x with backoff → IndexWriteError."""
    mock_es_client._client.bulk = AsyncMock(
        side_effect=ConnectionError("Connection refused")
    )

    chunks = _make_code_chunks(5)
    embeddings = _make_embeddings(5)

    with pytest.raises(IndexWriteError, match="failed after 3 retries"):
        await writer.write_code_chunks(chunks, embeddings, repo_id="repo-1")

    assert mock_es_client._client.bulk.call_count == 3


# ---------------------------------------------------------------------------
# T14: Error — chunks/embeddings length mismatch raises ValueError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_write_code_chunks_length_mismatch_raises_value_error(writer):
    """Mismatched chunks and embeddings lengths must raise ValueError."""
    chunks = _make_code_chunks(5)
    embeddings = _make_embeddings(3)  # mismatch!

    with pytest.raises(ValueError, match="same length"):
        await writer.write_code_chunks(chunks, embeddings, repo_id="repo-1")


# ---------------------------------------------------------------------------
# T16: Boundary — empty chunks list is a no-op
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_write_code_chunks_empty_is_noop(writer, mock_es_client, mock_qdrant_client):
    """Empty chunks + embeddings → no-op, no ES/Qdrant calls."""
    await writer.write_code_chunks([], [], repo_id="repo-1")

    mock_es_client._client.bulk.assert_not_called()
    mock_qdrant_client._client.upsert.assert_not_called()


# ---------------------------------------------------------------------------
# T17: Error — Qdrant fails 2x then succeeds on 3rd retry
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_write_code_chunks_qdrant_succeeds_on_third_retry(writer, mock_es_client, mock_qdrant_client):
    """Retry: fail 2x, succeed on 3rd → write completes, no error."""
    mock_qdrant_client._client.upsert = AsyncMock(
        side_effect=[ConnectionError("fail 1"), ConnectionError("fail 2"), None]
    )

    chunks = _make_code_chunks(5)
    embeddings = _make_embeddings(5)

    # Should NOT raise — succeeds on 3rd attempt
    await writer.write_code_chunks(chunks, embeddings, repo_id="repo-1")

    assert mock_qdrant_client._client.upsert.call_count == 3


# ---------------------------------------------------------------------------
# Real test: verify Qdrant client connectivity
# [integration]
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# T17b: Boundary — retry uses exponential backoff (timing check)
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retry_write_uses_exponential_backoff(writer, mock_es_client, mock_qdrant_client):
    """Verify retry uses exponential backoff delay between attempts."""
    mock_qdrant_client._client.upsert = AsyncMock(
        side_effect=[ConnectionError("fail 1"), ConnectionError("fail 2"), None]
    )
    chunks = _make_code_chunks(2)
    embeddings = _make_embeddings(2)

    with patch("src.indexing.index_writer.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await writer.write_code_chunks(chunks, embeddings, repo_id="repo-1")

        # Should have slept twice (after attempt 1 and attempt 2)
        assert mock_sleep.call_count == 2
        # Verify exponential backoff: 2^1 * 0.5 = 1.0, 2^2 * 0.5 = 2.0
        mock_sleep.assert_any_call(1.0)
        mock_sleep.assert_any_call(2.0)


@pytest.mark.real
@pytest.mark.asyncio
async def test_real_qdrant_connectivity():
    """Real test: verify Qdrant client can connect and list collections."""
    import os
    from qdrant_client import AsyncQdrantClient

    url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    # Disable proxy env vars that may interfere with local connections
    env_overrides = {}
    for key in ("ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy",
                "HTTPS_PROXY", "https_proxy"):
        if key in os.environ:
            env_overrides[key] = os.environ.pop(key)
    try:
        client = AsyncQdrantClient(url=url, check_compatibility=False)
        try:
            collections = await client.get_collections()
            # Just verify we got a response — collection list may be empty
            assert collections is not None
            assert hasattr(collections, "collections")
        finally:
            await client.close()
    finally:
        os.environ.update(env_overrides)
