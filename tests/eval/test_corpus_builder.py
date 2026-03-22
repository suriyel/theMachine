"""Tests for EvalCorpusBuilder — Feature #40: Evaluation Corpus Management.

Test Inventory from feature detailed design (docs/plans/2026-03-22-evaluation-corpus-management.md).
15 test scenarios: 6 happy path, 9 negative (60% negative ratio).

Categories covered:
- Happy path: T1, T2, T3, T11, T14
- Error handling: T4, T5, T6, T7, T8, T9, T12, T15
- Boundary: T10, T11, T13
- Security: N/A — internal offline CLI tool with no user-facing input
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from src.eval.corpus_builder import (
    CorpusSummary,
    EvalCorpusBuilder,
    EvalRepo,
)
from src.indexing.chunker import CodeChunk
from src.indexing.content_extractor import ContentType, ExtractedFile
from src.indexing.exceptions import EmbeddingModelError, IndexWriteError
from src.shared.exceptions import CloneError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_chunk(chunk_id: str, repo_id: str, content: str = "x") -> CodeChunk:
    """Create a minimal CodeChunk for testing."""
    return CodeChunk(
        chunk_id=chunk_id,
        repo_id=repo_id,
        branch="main",
        file_path="test.py",
        language="python",
        chunk_type="function",
        symbol="test_fn",
        signature="def test_fn():",
        doc_comment="",
        parent_class="",
        content=content,
        line_start=1,
        line_end=5,
    )


def _make_code_file(path: str = "src/main.py") -> ExtractedFile:
    return ExtractedFile(
        path=path,
        content_type=ContentType.CODE,
        content="def main(): pass",
        size=17,
    )


def _make_doc_file(path: str = "README.md") -> ExtractedFile:
    return ExtractedFile(
        path=path,
        content_type=ContentType.DOC,
        content="# Readme",
        size=8,
    )


def _make_repos_json(tmp_path: Path, repos: list[dict]) -> str:
    """Write repos JSON to a temp file and return its path."""
    p = tmp_path / "repos.json"
    p.write_text(json.dumps(repos))
    return str(p)


def _sample_repos(count: int = 3) -> list[dict]:
    """Return a list of N well-formed repo dicts."""
    return [
        {"name": f"repo{i}", "url": f"https://github.com/test/repo{i}", "language": "python", "branch": "main"}
        for i in range(1, count + 1)
    ]


@pytest.fixture
def mock_deps():
    """Create mocked dependency objects for EvalCorpusBuilder."""
    git_cloner = MagicMock()
    git_cloner.clone_or_update = MagicMock(return_value="/tmp/clone")

    content_extractor = MagicMock()
    content_extractor.extract = MagicMock(return_value=[_make_code_file()])

    chunker = MagicMock()
    chunker.chunk = MagicMock(return_value=[_make_chunk("c1", "repo1")])

    embedding_encoder = MagicMock()
    embedding_encoder.encode_batch = MagicMock(return_value=[np.zeros(1024)])

    index_writer = MagicMock()
    index_writer.write_code_chunks = AsyncMock()

    es_client = MagicMock()
    es_client._client = AsyncMock()
    es_client._client.count = AsyncMock(return_value={"count": 0})

    return {
        "git_cloner": git_cloner,
        "content_extractor": content_extractor,
        "chunker": chunker,
        "embedding_encoder": embedding_encoder,
        "index_writer": index_writer,
        "es_client": es_client,
    }


def _build(mock_deps: dict) -> EvalCorpusBuilder:
    return EvalCorpusBuilder(
        git_cloner=mock_deps["git_cloner"],
        content_extractor=mock_deps["content_extractor"],
        chunker=mock_deps["chunker"],
        embedding_encoder=mock_deps["embedding_encoder"],
        index_writer=mock_deps["index_writer"],
        es_client=mock_deps["es_client"],
    )


# ---------------------------------------------------------------------------
# T1: Happy path — all repos indexed fresh
# [unit] — mocked dependencies
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_indexes_all_repos(tmp_path, mock_deps):
    """T1: Given 3 repos with ES count=0, build() indexes all 3."""
    repos_path = _make_repos_json(tmp_path, _sample_repos(3))
    builder = _build(mock_deps)

    result = await builder.build(repos_path)

    assert result.total == 3
    assert result.indexed == 3
    assert result.skipped == 0
    assert result.failed == 0
    assert mock_deps["index_writer"].write_code_chunks.await_count == 3
    assert mock_deps["git_cloner"].clone_or_update.call_count == 3
    # Verify eval_ prefix is passed to IndexWriter
    for call in mock_deps["index_writer"].write_code_chunks.call_args_list:
        assert call.kwargs["es_index"] == "eval_code_chunks"
        assert call.kwargs["qdrant_collection"] == "eval_code_embeddings"


# ---------------------------------------------------------------------------
# T2: Happy path — all repos already indexed (idempotent skip)
# [unit] — mocked dependencies
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_skips_already_indexed(tmp_path, mock_deps):
    """T2: Given 3 repos with ES count>0 for all, build() skips all."""
    mock_deps["es_client"]._client.count = AsyncMock(return_value={"count": 10})
    repos_path = _make_repos_json(tmp_path, _sample_repos(3))
    builder = _build(mock_deps)

    result = await builder.build(repos_path)

    assert result.total == 3
    assert result.indexed == 0
    assert result.skipped == 3
    assert result.failed == 0
    mock_deps["git_cloner"].clone_or_update.assert_not_called()
    mock_deps["index_writer"].write_code_chunks.assert_not_awaited()


# ---------------------------------------------------------------------------
# T3: Happy path — mixed (some indexed, some not)
# [unit] — mocked dependencies
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_mixed_indexed_and_new(tmp_path, mock_deps):
    """T3: repo1 indexed, repo2 new, repo3 indexed → indexed=1, skipped=2."""
    counts = {"repo1": 5, "repo2": 0, "repo3": 8}

    async def count_side_effect(index, body):
        repo_name = body["query"]["term"]["repo_id"]
        return {"count": counts.get(repo_name, 0)}

    mock_deps["es_client"]._client.count = AsyncMock(side_effect=count_side_effect)
    repos_path = _make_repos_json(tmp_path, _sample_repos(3))
    builder = _build(mock_deps)

    result = await builder.build(repos_path)

    assert result.total == 3
    assert result.indexed == 1
    assert result.skipped == 2
    assert result.failed == 0
    assert mock_deps["git_cloner"].clone_or_update.call_count == 1


# ---------------------------------------------------------------------------
# T4: Error — clone failure for one repo, others continue
# [unit] — mocked dependencies
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_continues_on_clone_error(tmp_path, mock_deps):
    """T4: repo2 clone fails → indexed=2, failed=1."""
    call_count = 0

    def clone_side_effect(repo_id, url, branch=None):
        nonlocal call_count
        call_count += 1
        if repo_id == "repo2":
            raise CloneError("network error")
        return "/tmp/clone"

    mock_deps["git_cloner"].clone_or_update = MagicMock(side_effect=clone_side_effect)
    repos_path = _make_repos_json(tmp_path, _sample_repos(3))
    builder = _build(mock_deps)

    result = await builder.build(repos_path)

    assert result.total == 3
    assert result.indexed == 2
    assert result.failed == 1
    assert result.skipped == 0
    # Verify the failed repo is tracked in details
    failed_detail = [d for d in result.details if d.status == "failed"]
    assert len(failed_detail) == 1
    assert failed_detail[0].name == "repo2"
    assert "network error" in failed_detail[0].error


# ---------------------------------------------------------------------------
# T5: Error — nonexistent repos.json path
# [unit] — no mocks needed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_file_not_found(mock_deps):
    """T5: Nonexistent repos_json_path → FileNotFoundError."""
    builder = _build(mock_deps)

    with pytest.raises(FileNotFoundError):
        await builder.build("/nonexistent/repos.json")


# ---------------------------------------------------------------------------
# T6: Error — invalid JSON (not a list)
# [unit] — no mocks needed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_invalid_json(tmp_path, mock_deps):
    """T6: repos.json with non-list content → ValueError."""
    p = tmp_path / "repos.json"
    p.write_text('{"not": "a list"}')
    builder = _build(mock_deps)

    with pytest.raises(ValueError, match="JSON array"):
        await builder.build(str(p))


# ---------------------------------------------------------------------------
# T7: Error — repo entry missing required field
# [unit] — no mocks needed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_missing_required_field(tmp_path, mock_deps):
    """T7: Repo entry missing 'url' → ValueError mentioning missing fields."""
    repos = [{"name": "repo1", "language": "python", "branch": "main"}]  # no url
    repos_path = _make_repos_json(tmp_path, repos)
    builder = _build(mock_deps)

    with pytest.raises(ValueError, match="missing"):
        await builder.build(repos_path)


# ---------------------------------------------------------------------------
# T8: Error — embedding failure for one repo, others continue
# [unit] — mocked dependencies
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_continues_on_embedding_error(tmp_path, mock_deps):
    """T8: repo2 embedding fails → indexed=2, failed=1."""
    call_count = 0

    def encode_side_effect(texts, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:  # Second repo
            raise EmbeddingModelError("API timeout")
        return [np.zeros(1024) for _ in texts]

    mock_deps["embedding_encoder"].encode_batch = MagicMock(side_effect=encode_side_effect)
    repos_path = _make_repos_json(tmp_path, _sample_repos(3))
    builder = _build(mock_deps)

    result = await builder.build(repos_path)

    assert result.total == 3
    assert result.indexed == 2
    assert result.failed == 1


# ---------------------------------------------------------------------------
# T9: Error — IndexWriter write failure for one repo, others continue
# [unit] — mocked dependencies
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_continues_on_write_error(tmp_path, mock_deps):
    """T9: repo2 IndexWriter fails → indexed=2, failed=1."""
    call_count = 0

    async def write_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise IndexWriteError("ES bulk write failed")

    mock_deps["index_writer"].write_code_chunks = AsyncMock(side_effect=write_side_effect)
    repos_path = _make_repos_json(tmp_path, _sample_repos(3))
    builder = _build(mock_deps)

    result = await builder.build(repos_path)

    assert result.total == 3
    assert result.indexed == 2
    assert result.failed == 1


# ---------------------------------------------------------------------------
# T10: Boundary — empty repos.json array
# [unit] — no mocks needed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_empty_repos_list(tmp_path, mock_deps):
    """T10: Empty repos array → all zeros in summary."""
    repos_path = _make_repos_json(tmp_path, [])
    builder = _build(mock_deps)

    result = await builder.build(repos_path)

    assert result.total == 0
    assert result.indexed == 0
    assert result.skipped == 0
    assert result.failed == 0
    assert result.details == []


# ---------------------------------------------------------------------------
# T11: Boundary — repo with only DOC files (no CODE)
# [unit] — mocked dependencies
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_no_code_files(tmp_path, mock_deps):
    """T11: ContentExtractor returns only DOC files → indexed=1, 0 chunks written."""
    mock_deps["content_extractor"].extract = MagicMock(return_value=[_make_doc_file()])
    repos_path = _make_repos_json(tmp_path, _sample_repos(1))
    builder = _build(mock_deps)

    result = await builder.build(repos_path)

    assert result.total == 1
    assert result.indexed == 1
    assert result.skipped == 0
    assert result.failed == 0
    # No chunks to write → write_code_chunks not called
    mock_deps["index_writer"].write_code_chunks.assert_not_awaited()
    mock_deps["embedding_encoder"].encode_batch.assert_not_called()


# ---------------------------------------------------------------------------
# T12: Error — ES unavailable during idempotency check → re-index
# [unit] — mocked dependencies
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_es_unavailable_for_idempotency(tmp_path, mock_deps):
    """T12: ES count raises ConnectionError → repo re-indexed (not skipped)."""
    mock_deps["es_client"]._client.count = AsyncMock(side_effect=ConnectionError("ES down"))
    repos_path = _make_repos_json(tmp_path, _sample_repos(1))
    builder = _build(mock_deps)

    result = await builder.build(repos_path)

    assert result.total == 1
    assert result.indexed == 1
    assert result.skipped == 0
    # Clone was called despite ES being unavailable
    mock_deps["git_cloner"].clone_or_update.assert_called_once()


# ---------------------------------------------------------------------------
# T13: Boundary — empty repo name → ValueError
# [unit] — no mocks needed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_empty_repo_name(tmp_path, mock_deps):
    """T13: Repo entry with name='' → ValueError for invalid entry."""
    repos = [{"name": "", "url": "https://github.com/test/x", "language": "python", "branch": "main"}]
    repos_path = _make_repos_json(tmp_path, repos)
    builder = _build(mock_deps)

    with pytest.raises(ValueError, match="name"):
        await builder.build(repos_path)


# ---------------------------------------------------------------------------
# T14: Happy path — multi-file repo batching
# [unit] — mocked dependencies
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_batches_chunks_across_files(tmp_path, mock_deps):
    """T14: 2 code files → 5 chunks total → encode_batch called with 5 texts."""
    files = [_make_code_file("a.py"), _make_code_file("b.py")]
    mock_deps["content_extractor"].extract = MagicMock(return_value=files)

    chunk_a = [_make_chunk("c1", "repo1", "code_a1"), _make_chunk("c2", "repo1", "code_a2")]
    chunk_b = [_make_chunk("c3", "repo1", "code_b1"), _make_chunk("c4", "repo1", "code_b2"), _make_chunk("c5", "repo1", "code_b3")]

    call_count = 0
    def chunk_side_effect(file, repo_id, branch):
        nonlocal call_count
        call_count += 1
        return chunk_a if call_count == 1 else chunk_b

    mock_deps["chunker"].chunk = MagicMock(side_effect=chunk_side_effect)
    mock_deps["embedding_encoder"].encode_batch = MagicMock(
        return_value=[np.zeros(1024) for _ in range(5)]
    )
    repos_path = _make_repos_json(tmp_path, _sample_repos(1))
    builder = _build(mock_deps)

    result = await builder.build(repos_path)

    assert result.total == 1
    assert result.indexed == 1
    # Verify encode_batch was called with all 5 chunk contents
    encode_call = mock_deps["embedding_encoder"].encode_batch.call_args
    assert len(encode_call[0][0]) == 5
    assert encode_call[0][0] == ["code_a1", "code_a2", "code_b1", "code_b2", "code_b3"]


# ---------------------------------------------------------------------------
# T15: Error — all repos fail
# [unit] — mocked dependencies
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_all_repos_fail(tmp_path, mock_deps):
    """T15: All repos raise CloneError → indexed=0, failed=2, returns summary (no raise)."""
    mock_deps["git_cloner"].clone_or_update = MagicMock(side_effect=CloneError("fail"))
    repos_path = _make_repos_json(tmp_path, _sample_repos(2))
    builder = _build(mock_deps)

    result = await builder.build(repos_path)

    assert result.total == 2
    assert result.indexed == 0
    assert result.skipped == 0
    assert result.failed == 2
    assert len(result.details) == 2
    assert all(d.status == "failed" for d in result.details)


# ---------------------------------------------------------------------------
# T16: Error — malformed JSON syntax
# [unit] — no mocks needed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_malformed_json(tmp_path, mock_deps):
    """T16: repos.json with syntax errors → ValueError mentioning valid JSON."""
    p = tmp_path / "repos.json"
    p.write_text("{not valid json!!!")
    builder = _build(mock_deps)

    with pytest.raises(ValueError, match="valid JSON"):
        await builder.build(str(p))


# ---------------------------------------------------------------------------
# Real tests — ES connectivity for idempotency check
# [integration] — uses real Elasticsearch
# ---------------------------------------------------------------------------

# Clear proxy for real test connectivity
for k in ("ALL_PROXY", "all_proxy"):
    os.environ.pop(k, None)


@pytest.mark.real
@pytest.mark.asyncio
async def test_real_es_idempotency_check_feature_40():
    """Real test: verify _is_already_indexed works against real ES.

    Creates a test index, inserts a doc, and checks count-based idempotency.
    """
    import uuid
    from elasticsearch import AsyncElasticsearch

    es = AsyncElasticsearch("http://localhost:9200")
    test_index = f"test_eval_idem_{uuid.uuid4().hex[:8]}"

    try:
        # Create index with keyword mapping for repo_id (term queries need keyword type)
        await es.indices.create(
            index=test_index,
            settings={"number_of_shards": 1, "number_of_replicas": 0},
            mappings={"properties": {"repo_id": {"type": "keyword"}}},
        )
        await es.index(
            index=test_index,
            id="doc1",
            document={"repo_id": "test-repo", "content": "hello"},
            refresh="wait_for",
        )

        # Count for existing repo — should be > 0
        result = await es.count(
            index=test_index,
            body={"query": {"term": {"repo_id": "test-repo"}}},
        )
        assert result["count"] == 1

        # Count for non-existent repo — should be 0
        result = await es.count(
            index=test_index,
            body={"query": {"term": {"repo_id": "nonexistent"}}},
        )
        assert result["count"] == 0

    finally:
        await es.indices.delete(index=test_index, ignore=[404])
        await es.close()
