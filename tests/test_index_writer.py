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


# ===========================================================================
# Feature #48: Fix delete_repo_index branch filter on doc/rule indices
# ===========================================================================
# Bug: delete_repo_index uses repo_id+branch filter on all indices, but
# doc_chunks, rule_chunks (ES) and doc_embeddings (Qdrant) have no branch
# field. The branch filter silently matches zero docs → stale data remains.
#
# Security: N/A — internal indexing component with no user-facing input
# ===========================================================================


# ---------------------------------------------------------------------------
# Feature #48 T1: Happy path — doc_chunks and rule_chunks use repo_id-only filter
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_feature_48_delete_doc_rule_chunks_uses_repo_only_filter(
    writer, mock_es_client, mock_qdrant_client
):
    """VS-1: doc_chunks and rule_chunks must be deleted with repo_id-only filter (no branch)."""
    await writer.delete_repo_index(repo_id="repo-1", branch="main")

    es_calls = mock_es_client._client.delete_by_query.call_args_list
    # Find calls for doc_chunks and rule_chunks
    for es_call in es_calls:
        idx = es_call.kwargs.get("index") or es_call.args[0] if es_call.args else None
        if idx is None:
            idx = str(es_call)
        body = es_call.kwargs.get("body", {})
        if "doc_chunks" in str(es_call) or "rule_chunks" in str(es_call):
            must_clauses = body.get("query", {}).get("bool", {}).get("must", [])
            # Must have repo_id term but NOT branch term
            has_repo_id = any("repo_id" in str(c) for c in must_clauses)
            has_branch = any("branch" in str(c) for c in must_clauses)
            assert has_repo_id, f"Missing repo_id filter for {es_call}"
            assert not has_branch, f"doc/rule index should NOT have branch filter: {es_call}"


# ---------------------------------------------------------------------------
# Feature #48 T2: Happy path — code_chunks and code_embeddings use repo_id+branch
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_feature_48_delete_code_chunks_uses_repo_branch_filter(
    writer, mock_es_client, mock_qdrant_client
):
    """VS-2: code_chunks must be deleted with repo_id+branch filter."""
    await writer.delete_repo_index(repo_id="repo-1", branch="main")

    es_calls = mock_es_client._client.delete_by_query.call_args_list
    for es_call in es_calls:
        body = es_call.kwargs.get("body", {})
        if "code_chunks" in str(es_call):
            must_clauses = body.get("query", {}).get("bool", {}).get("must", [])
            has_repo_id = any("repo_id" in str(c) for c in must_clauses)
            has_branch = any("branch" in str(c) for c in must_clauses)
            assert has_repo_id, "code_chunks must have repo_id filter"
            assert has_branch, "code_chunks must have branch filter"


# ---------------------------------------------------------------------------
# Feature #48 T3: Happy path — doc_embeddings uses repo_id-only Qdrant filter
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_feature_48_delete_doc_embeddings_uses_repo_only_filter(
    writer, mock_es_client, mock_qdrant_client
):
    """VS-3: doc_embeddings Qdrant delete must use repo_id-only filter (no branch)."""
    from qdrant_client.models import FieldCondition

    await writer.delete_repo_index(repo_id="repo-1", branch="main")

    qdrant_calls = mock_qdrant_client._client.delete.call_args_list
    for qd_call in qdrant_calls:
        coll = qd_call.kwargs.get("collection_name", "")
        if coll == "doc_embeddings":
            points_selector = qd_call.kwargs.get("points_selector")
            # Check filter conditions — should have only repo_id, no branch
            conditions = points_selector.must
            field_keys = [c.key for c in conditions if isinstance(c, FieldCondition)]
            assert "repo_id" in field_keys, "doc_embeddings must filter by repo_id"
            assert "branch" not in field_keys, "doc_embeddings must NOT filter by branch"


# ---------------------------------------------------------------------------
# Feature #48 T4: Happy path — all 5 delete operations are called
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_feature_48_delete_calls_all_five_stores(
    writer, mock_es_client, mock_qdrant_client
):
    """All 5 delete operations must be executed: 3 ES + 2 Qdrant."""
    await writer.delete_repo_index(repo_id="repo-1", branch="main")

    # ES: exactly 3 calls (code_chunks, doc_chunks, rule_chunks)
    assert mock_es_client._client.delete_by_query.call_count == 3
    es_indices = [str(c) for c in mock_es_client._client.delete_by_query.call_args_list]
    assert any("code_chunks" in c for c in es_indices)
    assert any("doc_chunks" in c for c in es_indices)
    assert any("rule_chunks" in c for c in es_indices)

    # Qdrant: exactly 2 calls (code_embeddings, doc_embeddings)
    assert mock_qdrant_client._client.delete.call_count == 2
    qd_colls = [str(c) for c in mock_qdrant_client._client.delete.call_args_list]
    assert any("code_embeddings" in c for c in qd_colls)
    assert any("doc_embeddings" in c for c in qd_colls)


# ---------------------------------------------------------------------------
# Feature #48 T5: Error — ES fails on doc_chunks raises IndexWriteError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_feature_48_es_doc_chunks_failure_raises_error(
    writer, mock_es_client, mock_qdrant_client
):
    """ES delete_by_query failure on doc_chunks must raise IndexWriteError."""
    call_count = 0

    async def fail_on_doc_chunks(**kwargs):
        nonlocal call_count
        call_count += 1
        idx = kwargs.get("index", "")
        if idx == "doc_chunks":
            raise ConnectionError("Connection refused")
        return {"deleted": 0}

    mock_es_client._client.delete_by_query = AsyncMock(side_effect=fail_on_doc_chunks)

    with pytest.raises(IndexWriteError, match="failed after 3 retries"):
        await writer.delete_repo_index(repo_id="repo-1", branch="main")


# ---------------------------------------------------------------------------
# Feature #48 T6: Error — Qdrant fails on doc_embeddings raises IndexWriteError
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_feature_48_qdrant_doc_embeddings_failure_raises_error(
    writer, mock_es_client, mock_qdrant_client
):
    """Qdrant delete failure on doc_embeddings must raise IndexWriteError."""
    async def fail_on_doc_embeddings(**kwargs):
        coll = kwargs.get("collection_name", "")
        if coll == "doc_embeddings":
            raise ConnectionError("Connection refused")
        return None

    mock_qdrant_client._client.delete = AsyncMock(side_effect=fail_on_doc_embeddings)

    with pytest.raises(IndexWriteError, match="failed after 3 retries"):
        await writer.delete_repo_index(repo_id="repo-1", branch="main")


# ---------------------------------------------------------------------------
# Feature #48 T7: Boundary — empty repo_id runs without error
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_feature_48_empty_repo_id_no_error(
    writer, mock_es_client, mock_qdrant_client
):
    """Empty repo_id should execute all deletes without exception."""
    await writer.delete_repo_index(repo_id="", branch="main")

    assert mock_es_client._client.delete_by_query.call_count == 3
    assert mock_qdrant_client._client.delete.call_count == 2


# ---------------------------------------------------------------------------
# Feature #48 T8: Boundary — no documents match, 0 deleted, no error
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_feature_48_no_matching_docs_no_error(
    writer, mock_es_client, mock_qdrant_client
):
    """When 0 documents match any filter, no exception should be raised."""
    mock_es_client._client.delete_by_query = AsyncMock(return_value={"deleted": 0})
    mock_qdrant_client._client.delete = AsyncMock(return_value=None)

    await writer.delete_repo_index(repo_id="nonexistent", branch="main")

    assert mock_es_client._client.delete_by_query.call_count == 3
    assert mock_qdrant_client._client.delete.call_count == 2


# ---------------------------------------------------------------------------
# Feature #48 T9: Error — ES fails on code_chunks (first call) raises error
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_feature_48_es_code_chunks_failure_raises_error(
    writer, mock_es_client, mock_qdrant_client
):
    """ES delete_by_query failure on code_chunks (first call) must raise IndexWriteError."""
    mock_es_client._client.delete_by_query = AsyncMock(
        side_effect=ConnectionError("Connection refused")
    )

    with pytest.raises(IndexWriteError, match="failed after 3 retries"):
        await writer.delete_repo_index(repo_id="repo-1", branch="main")


# ---------------------------------------------------------------------------
# Feature #48 T10: Negative — verify doc_chunks query body has NO branch term
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_feature_48_doc_chunks_query_body_no_branch_term(
    writer, mock_es_client, mock_qdrant_client
):
    """Inspect actual query body for doc_chunks: must have exactly 1 term (repo_id only)."""
    await writer.delete_repo_index(repo_id="repo-1", branch="main")

    es_calls = mock_es_client._client.delete_by_query.call_args_list
    for es_call in es_calls:
        idx = es_call.kwargs.get("index", "")
        if idx == "doc_chunks":
            body = es_call.kwargs.get("body", {})
            must_clauses = body["query"]["bool"]["must"]
            # Must have exactly 1 clause: repo_id only
            assert len(must_clauses) == 1, (
                f"doc_chunks query must have exactly 1 must clause (repo_id only), "
                f"got {len(must_clauses)}: {must_clauses}"
            )
            assert "repo_id" in str(must_clauses[0]), (
                f"The single clause must be repo_id, got: {must_clauses[0]}"
            )
            break
    else:
        pytest.fail("doc_chunks delete_by_query call not found")


# ---------------------------------------------------------------------------
# Feature #48 T11: Mutation hardening — exact query structure verification
# [unit]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_feature_48_exact_es_query_structures(
    writer, mock_es_client, mock_qdrant_client
):
    """Verify exact ES query dict structures to catch string-key mutations."""
    await writer.delete_repo_index(repo_id="repo-1", branch="main")

    es_calls = mock_es_client._client.delete_by_query.call_args_list
    # Build dict: index -> body
    calls_by_index = {}
    for c in es_calls:
        idx = c.kwargs["index"]
        calls_by_index[idx] = c.kwargs["body"]

    # code_chunks: repo_id + branch
    assert "code_chunks" in calls_by_index
    cc_must = calls_by_index["code_chunks"]["query"]["bool"]["must"]
    assert {"term": {"repo_id": "repo-1"}} in cc_must
    assert {"term": {"branch": "main"}} in cc_must
    assert len(cc_must) == 2

    # doc_chunks: repo_id only
    assert "doc_chunks" in calls_by_index
    dc_must = calls_by_index["doc_chunks"]["query"]["bool"]["must"]
    assert {"term": {"repo_id": "repo-1"}} in dc_must
    assert len(dc_must) == 1

    # rule_chunks: repo_id only
    assert "rule_chunks" in calls_by_index
    rc_must = calls_by_index["rule_chunks"]["query"]["bool"]["must"]
    assert {"term": {"repo_id": "repo-1"}} in rc_must
    assert len(rc_must) == 1


@pytest.mark.asyncio
async def test_feature_48_exact_qdrant_filter_structures(
    writer, mock_es_client, mock_qdrant_client
):
    """Verify exact Qdrant filter structures to catch key/value mutations."""
    from qdrant_client.models import FieldCondition, MatchValue

    await writer.delete_repo_index(repo_id="repo-1", branch="main")

    qd_calls = mock_qdrant_client._client.delete.call_args_list
    calls_by_coll = {}
    for c in qd_calls:
        coll = c.kwargs["collection_name"]
        calls_by_coll[coll] = c.kwargs["points_selector"]

    # code_embeddings: repo_id + branch
    assert "code_embeddings" in calls_by_coll
    ce_conditions = calls_by_coll["code_embeddings"].must
    ce_keys = [c.key for c in ce_conditions if isinstance(c, FieldCondition)]
    ce_values = [c.match.value for c in ce_conditions if isinstance(c, FieldCondition)]
    assert "repo_id" in ce_keys
    assert "branch" in ce_keys
    assert "repo-1" in ce_values
    assert "main" in ce_values
    assert len(ce_conditions) == 2

    # doc_embeddings: repo_id only
    assert "doc_embeddings" in calls_by_coll
    de_conditions = calls_by_coll["doc_embeddings"].must
    de_keys = [c.key for c in de_conditions if isinstance(c, FieldCondition)]
    de_values = [c.match.value for c in de_conditions if isinstance(c, FieldCondition)]
    assert de_keys == ["repo_id"]
    assert de_values == ["repo-1"]
    assert len(de_conditions) == 1


@pytest.mark.asyncio
async def test_feature_48_exact_index_names_in_calls(
    writer, mock_es_client, mock_qdrant_client
):
    """Verify exact index and collection names passed as kwargs."""
    await writer.delete_repo_index(repo_id="repo-1", branch="main")

    es_indices = [c.kwargs["index"] for c in mock_es_client._client.delete_by_query.call_args_list]
    assert es_indices == ["code_chunks", "doc_chunks", "rule_chunks"]

    qd_collections = [c.kwargs["collection_name"] for c in mock_qdrant_client._client.delete.call_args_list]
    assert qd_collections == ["code_embeddings", "doc_embeddings"]


# ---------------------------------------------------------------------------
# Feature #48 T-real: Real test — ES delete_by_query with repo_id-only filter
# [integration]
# ---------------------------------------------------------------------------

@pytest.mark.real
@pytest.mark.asyncio
async def test_real_feature_48_es_delete_repo_only_filter():
    """Real test: verify ES deletes doc_chunks by repo_id-only (no branch field)."""
    import os
    import uuid as _uuid

    for k in ("ALL_PROXY", "all_proxy"):
        os.environ.pop(k, None)

    es_url = os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200")
    assert es_url, "ELASTICSEARCH_URL must be set for real ES test"

    from elasticsearch import AsyncElasticsearch

    es = AsyncElasticsearch(es_url)
    test_index = f"test_doc_chunks_{_uuid.uuid4().hex[:8]}"
    repo_id = f"test-repo-{_uuid.uuid4().hex[:8]}"

    try:
        # Create test index with repo_id field only (no branch)
        await es.indices.create(
            index=test_index,
            body={
                "settings": {"number_of_shards": 1, "number_of_replicas": 0},
                "mappings": {
                    "properties": {
                        "repo_id": {"type": "keyword"},
                        "content": {"type": "text"},
                    }
                },
            },
        )

        # Index 3 docs with repo_id only (mimicking doc_chunks — no branch field)
        for i in range(3):
            await es.index(
                index=test_index,
                id=f"{repo_id}-doc-{i}",
                body={"repo_id": repo_id, "content": f"doc content {i}"},
            )
        await es.indices.refresh(index=test_index)

        # Delete using repo_id-only filter (the fixed behavior)
        repo_only_query = {"query": {"bool": {"must": [
            {"term": {"repo_id": repo_id}},
        ]}}}
        result = await es.delete_by_query(index=test_index, body=repo_only_query)
        assert result["deleted"] == 3, f"Expected 3 deleted, got {result['deleted']}"

        # Verify 0 docs remain
        await es.indices.refresh(index=test_index)
        count = await es.count(index=test_index, body={"query": {"match_all": {}}})
        assert count["count"] == 0, f"Expected 0 remaining, got {count['count']}"

    finally:
        await es.indices.delete(index=test_index, ignore=[404])
        await es.close()
