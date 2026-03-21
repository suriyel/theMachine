"""Tests for Reranker — Neural Reranking (Feature #11).

Security: N/A — internal utility with no user-facing input.

# [no integration test] — pure computation with mocked model, no external I/O.
# The CrossEncoder model is an external ML dependency that requires large model
# downloads; real model testing is covered by ST acceptance tests.
"""

from __future__ import annotations

import logging
import math
from dataclasses import replace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.query.scored_chunk import ScoredChunk


def _make_chunks(n: int, *, score_start: float = 0.5) -> list[ScoredChunk]:
    """Create n ScoredChunk instances with distinct IDs and content."""
    return [
        ScoredChunk(
            chunk_id=f"chunk-{i}",
            content_type="code",
            repo_id="repo-1",
            file_path=f"src/file_{i}.py",
            content=f"def function_{i}(): pass  # unique content {i}",
            score=score_start + i * 0.01,
            language="python",
            chunk_type="function",
            symbol=f"function_{i}",
        )
        for i in range(n)
    ]


# ---------- Happy Path Tests ----------


# [unit] — mock CrossEncoder, verify reranking logic
def test_rerank_50_candidates_returns_top6_rescored():
    """T1: 50 fused candidates → rerank returns top-6 re-scored by cross-encoder."""
    from src.query.reranker import Reranker

    candidates = _make_chunks(50)
    # Mock cross-encoder scores: higher score for later chunks (reversed order)
    mock_scores = np.array([float(i) for i in range(50)])

    with patch("src.query.reranker.CrossEncoder") as MockCE:
        mock_model = MagicMock()
        mock_model.predict.return_value = mock_scores
        MockCE.return_value = mock_model

        reranker = Reranker(model_name="test-model")
        result = reranker.rerank("spring webclient timeout", candidates, top_k=6)

    assert len(result) == 6
    # Highest CE scores are 49, 48, 47, 46, 45, 44 (for chunks 49..44)
    assert result[0].chunk_id == "chunk-49"
    assert result[5].chunk_id == "chunk-44"
    # Scores should be cross-encoder scores, not original fusion scores
    assert result[0].score == 49.0
    assert result[5].score == 44.0


# [unit] — verify truncation with fewer than 50 candidates
def test_rerank_10_candidates_top6():
    """T2: 10 candidates, top_k=6 → returns exactly 6."""
    from src.query.reranker import Reranker

    candidates = _make_chunks(10)
    mock_scores = np.array([float(9 - i) for i in range(10)])  # descending

    with patch("src.query.reranker.CrossEncoder") as MockCE:
        mock_model = MagicMock()
        mock_model.predict.return_value = mock_scores
        MockCE.return_value = mock_model

        reranker = Reranker(model_name="test-model")
        result = reranker.rerank("query", candidates, top_k=6)

    assert len(result) == 6
    assert result[0].chunk_id == "chunk-0"  # highest score = 9.0


# [unit] — verify scores are replaced with CE scores
def test_rerank_scores_replaced():
    """T9: Returned chunk scores must be cross-encoder values, not originals."""
    from src.query.reranker import Reranker

    candidates = _make_chunks(5, score_start=100.0)  # original scores are high
    mock_scores = np.array([0.1, 0.2, 0.3, 0.4, 0.5])

    with patch("src.query.reranker.CrossEncoder") as MockCE:
        mock_model = MagicMock()
        mock_model.predict.return_value = mock_scores
        MockCE.return_value = mock_model

        reranker = Reranker(model_name="test-model")
        result = reranker.rerank("query", candidates, top_k=5)

    # None of the original scores (100.0+) should remain
    for chunk in result:
        assert chunk.score < 1.0, f"Score {chunk.score} looks like original, not CE score"
    # Best CE score should be first
    assert result[0].score == pytest.approx(0.5)


# [unit] — verify descending sort order
def test_rerank_descending_order():
    """T11: Results must be sorted descending by cross-encoder score."""
    from src.query.reranker import Reranker

    candidates = _make_chunks(8)
    # Random-ish scores to ensure sort is applied
    mock_scores = np.array([0.3, 0.9, 0.1, 0.7, 0.5, 0.2, 0.8, 0.4])

    with patch("src.query.reranker.CrossEncoder") as MockCE:
        mock_model = MagicMock()
        mock_model.predict.return_value = mock_scores
        MockCE.return_value = mock_model

        reranker = Reranker(model_name="test-model")
        result = reranker.rerank("query", candidates, top_k=8)

    for i in range(len(result) - 1):
        assert result[i].score >= result[i + 1].score, (
            f"Not descending at index {i}: {result[i].score} < {result[i + 1].score}"
        )


# ---------- Boundary Tests ----------


# [unit] — fewer candidates than top_k
def test_rerank_fewer_than_topk():
    """T3: 2 candidates with top_k=6 → returns all 2, no error."""
    from src.query.reranker import Reranker

    candidates = _make_chunks(2)
    mock_scores = np.array([0.8, 0.3])

    with patch("src.query.reranker.CrossEncoder") as MockCE:
        mock_model = MagicMock()
        mock_model.predict.return_value = mock_scores
        MockCE.return_value = mock_model

        reranker = Reranker(model_name="test-model")
        result = reranker.rerank("query", candidates, top_k=6)

    assert len(result) == 2
    assert result[0].score == pytest.approx(0.8)
    assert result[1].score == pytest.approx(0.3)


# [unit] — single candidate
def test_rerank_single_candidate():
    """T4: 1 candidate → returns 1 chunk re-scored."""
    from src.query.reranker import Reranker

    candidates = _make_chunks(1)
    mock_scores = np.array([0.95])

    with patch("src.query.reranker.CrossEncoder") as MockCE:
        mock_model = MagicMock()
        mock_model.predict.return_value = mock_scores
        MockCE.return_value = mock_model

        reranker = Reranker(model_name="test-model")
        result = reranker.rerank("query", candidates, top_k=6)

    assert len(result) == 1
    assert result[0].score == pytest.approx(0.95)
    assert result[0].chunk_id == "chunk-0"


# [unit] — empty candidates
def test_rerank_empty_candidates():
    """T5: Empty candidate list → returns []."""
    from src.query.reranker import Reranker

    with patch("src.query.reranker.CrossEncoder") as MockCE:
        MockCE.return_value = MagicMock()
        reranker = Reranker(model_name="test-model")
        result = reranker.rerank("query", [], top_k=6)

    assert result == []


# [unit] — top_k=1
def test_rerank_topk_one():
    """T8: top_k=1 with 10 candidates → returns exactly 1 (the highest)."""
    from src.query.reranker import Reranker

    candidates = _make_chunks(10)
    mock_scores = np.array([float(i) for i in range(10)])  # chunk-9 has highest

    with patch("src.query.reranker.CrossEncoder") as MockCE:
        mock_model = MagicMock()
        mock_model.predict.return_value = mock_scores
        MockCE.return_value = mock_model

        reranker = Reranker(model_name="test-model")
        result = reranker.rerank("query", candidates, top_k=1)

    assert len(result) == 1
    assert result[0].chunk_id == "chunk-9"
    assert result[0].score == 9.0


# ---------- Error / Fallback Tests ----------


# [unit] — model load failure → fallback
def test_rerank_model_load_failure_fallback(caplog):
    """T6: Model fails to load → rerank returns fusion-order candidates, logs warning."""
    from src.query.reranker import Reranker

    with patch("src.query.reranker.CrossEncoder") as MockCE:
        MockCE.side_effect = RuntimeError("OOM: cannot allocate memory")

        with caplog.at_level(logging.WARNING):
            reranker = Reranker(model_name="bad-model")

    candidates = _make_chunks(10, score_start=1.0)

    with caplog.at_level(logging.WARNING):
        result = reranker.rerank("query", candidates, top_k=6)

    # Fallback: return first 6 in original order with original scores
    assert len(result) == 6
    assert result[0].chunk_id == "chunk-0"
    assert result[5].chunk_id == "chunk-5"
    # Original scores preserved
    assert result[0].score == pytest.approx(1.0)
    assert result[5].score == pytest.approx(1.05)
    # Must log the "not loaded" warning specifically (not inference error)
    assert any("not loaded" in msg for msg in caplog.messages), (
        f"Expected 'not loaded' warning, got: {caplog.messages}"
    )


# [unit] — inference failure → fallback
def test_rerank_inference_failure_fallback(caplog):
    """T7: Model loaded but predict() raises → fallback to fusion order, warning logged."""
    from src.query.reranker import Reranker

    with patch("src.query.reranker.CrossEncoder") as MockCE:
        mock_model = MagicMock()
        mock_model.predict.side_effect = RuntimeError("CUDA OOM")
        MockCE.return_value = mock_model

        reranker = Reranker(model_name="test-model")

    candidates = _make_chunks(5, score_start=2.0)

    with caplog.at_level(logging.WARNING):
        result = reranker.rerank("query", candidates, top_k=3)

    assert len(result) == 3
    # Original order preserved (fusion order)
    assert result[0].chunk_id == "chunk-0"
    assert result[2].chunk_id == "chunk-2"
    # Original scores preserved
    assert result[0].score == pytest.approx(2.0)
    # Warning was logged
    assert any("falling back" in msg.lower() or "fallback" in msg.lower() or "failed" in msg.lower()
               for msg in caplog.messages), f"Expected fallback warning in logs: {caplog.messages}"


# [unit] — NaN scores → fallback
def test_rerank_nan_scores_fallback(caplog):
    """T10: Model returns NaN scores → fallback to fusion order, warning logged."""
    from src.query.reranker import Reranker

    candidates = _make_chunks(5, score_start=1.0)
    nan_scores = np.array([float("nan"), 0.5, float("nan"), 0.3, float("nan")])

    with patch("src.query.reranker.CrossEncoder") as MockCE:
        mock_model = MagicMock()
        mock_model.predict.return_value = nan_scores
        MockCE.return_value = mock_model

        reranker = Reranker(model_name="test-model")

    with caplog.at_level(logging.WARNING):
        result = reranker.rerank("query", candidates, top_k=3)

    # Should fall back to fusion order since NaN detected
    assert len(result) == 3
    assert result[0].chunk_id == "chunk-0"
    assert result[1].chunk_id == "chunk-1"
    assert result[2].chunk_id == "chunk-2"
    # Warning logged
    assert any("nan" in msg.lower() or "fallback" in msg.lower()
               for msg in caplog.messages), f"Expected NaN fallback warning: {caplog.messages}"
