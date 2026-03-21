"""Tests for RankFusion — Reciprocal Rank Fusion (Feature #10).

# [no integration test] — pure function, no external I/O
# Security: N/A — internal utility with no user-facing input
"""

from __future__ import annotations

import time

import pytest

from src.query.rank_fusion import RankFusion
from src.query.scored_chunk import ScoredChunk


def _make_chunk(
    chunk_id: str,
    score: float = 0.0,
    content_type: str = "code",
    repo_id: str = "repo-1",
    file_path: str = "src/main.py",
    content: str = "chunk content",
) -> ScoredChunk:
    """Helper to create ScoredChunk instances for testing."""
    return ScoredChunk(
        chunk_id=chunk_id,
        content_type=content_type,
        repo_id=repo_id,
        file_path=file_path,
        content=content,
        score=score,
    )


# ---------- Happy path ----------


# [unit]
class TestRRFHappyPath:
    """T1, T2, T3, T12, T13, T15 — happy path tests."""

    def test_overlapping_chunks_get_boosted_scores(self) -> None:
        """T1: 200 BM25 + 200 vector candidates, 50 overlapping → boosted scores.

        VS-1: overlapping chunks receive boosted RRF scores from both rankings
        and the output contains at most 50 candidates.
        """
        rrf = RankFusion(k=60)

        # Build 200 BM25 chunks: IDs chunk-0..chunk-199
        bm25 = [_make_chunk(f"chunk-{i}", score=1.0 - i * 0.005) for i in range(200)]
        # Build 200 vector chunks: IDs chunk-150..chunk-349 (overlap: chunk-150..chunk-199)
        vector = [
            _make_chunk(f"chunk-{150 + i}", score=0.9 - i * 0.004) for i in range(200)
        ]

        result = rrf.fuse(bm25, vector, top_k=50)

        # At most 50 results
        assert len(result) <= 50

        # Identify overlapping chunk IDs
        bm25_ids = {c.chunk_id for c in bm25}
        vector_ids = {c.chunk_id for c in vector}
        overlap_ids = bm25_ids & vector_ids
        assert len(overlap_ids) == 50  # sanity: 50 overlapping

        # Overlapping chunks should have higher scores than non-overlapping ones
        result_map = {c.chunk_id: c.score for c in result}
        overlapping_in_result = {
            cid: s for cid, s in result_map.items() if cid in overlap_ids
        }
        non_overlapping_in_result = {
            cid: s for cid, s in result_map.items() if cid not in overlap_ids
        }

        if overlapping_in_result and non_overlapping_in_result:
            min_overlap_score = min(overlapping_in_result.values())
            max_non_overlap_score = max(non_overlapping_in_result.values())
            # The highest-ranked overlapping chunk should beat the
            # highest non-overlapping chunk
            assert max(overlapping_in_result.values()) > max_non_overlap_score

        # An overlapping chunk's score should be the sum of two RRF scores
        # Pick the first overlapping chunk: chunk-150, rank 151 in bm25, rank 1 in vector
        if "chunk-150" in result_map:
            expected_score = 1.0 / (60 + 151) + 1.0 / (60 + 1)
            assert abs(result_map["chunk-150"] - expected_score) < 1e-9

    def test_one_empty_list(self) -> None:
        """T2: One empty list + one non-empty list → returns non-empty list results.

        VS-2: returns results from the non-empty list only.
        """
        rrf = RankFusion(k=60)
        chunks = [_make_chunk(f"c-{i}") for i in range(5)]

        result = rrf.fuse([], chunks)

        assert len(result) == 5
        returned_ids = {c.chunk_id for c in result}
        assert returned_ids == {f"c-{i}" for i in range(5)}
        # Each should have a single-list RRF score
        for i, chunk in enumerate(result):
            expected = 1.0 / (60 + (i + 1))
            assert abs(chunk.score - expected) < 1e-9

    def test_four_way_fusion_performance(self) -> None:
        """T3: 4 lists merged correctly within 10ms.

        VS-3: 4-way input merged by RRF, execution < 10ms.
        """
        rrf = RankFusion(k=60)

        bm25_code = [
            _make_chunk(f"code-bm25-{i}", content_type="code") for i in range(100)
        ]
        vec_code = [
            _make_chunk(f"code-vec-{i}", content_type="code") for i in range(100)
        ]
        bm25_doc = [
            _make_chunk(f"doc-bm25-{i}", content_type="doc") for i in range(100)
        ]
        vec_doc = [
            _make_chunk(f"doc-vec-{i}", content_type="doc") for i in range(100)
        ]

        start = time.perf_counter()
        result = rrf.fuse(bm25_code, vec_code, bm25_doc, vec_doc, top_k=50)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 10, f"RRF fusion took {elapsed_ms:.2f}ms, expected < 10ms"
        assert len(result) == 50

        # Both content types should be present
        content_types = {c.content_type for c in result}
        assert "code" in content_types
        assert "doc" in content_types

    def test_default_k_is_60(self) -> None:
        """T17: Default constructor uses k=60 per RRF standard."""
        rrf = RankFusion()  # no explicit k
        result = rrf.fuse([_make_chunk("x")])
        expected = 1.0 / (60 + 1)  # k=60, rank=1
        assert abs(result[0].score - expected) < 1e-9

    def test_rrf_score_formula(self) -> None:
        """T12: Verify exact RRF score computation for overlapping chunks."""
        rrf = RankFusion(k=60)

        # Chunk at rank 1 in both lists
        list_a = [_make_chunk("overlap", score=0.99)]
        list_b = [_make_chunk("overlap", score=0.88)]

        result = rrf.fuse(list_a, list_b)

        assert len(result) == 1
        expected = 1.0 / 61 + 1.0 / 61  # 2/61
        assert abs(result[0].score - expected) < 1e-9
        assert abs(result[0].score - 2.0 / 61) < 1e-9

    def test_ordering_by_rrf_score(self) -> None:
        """T13: Chunk appearing at rank 1 in both lists outscores rank 2 in both."""
        rrf = RankFusion(k=60)

        list_a = [_make_chunk("A"), _make_chunk("B")]
        list_b = [_make_chunk("A"), _make_chunk("B")]

        result = rrf.fuse(list_a, list_b)

        assert len(result) == 2
        assert result[0].chunk_id == "A"
        assert result[1].chunk_id == "B"
        assert result[0].score > result[1].score

        # Exact scores
        assert abs(result[0].score - (1.0 / 61 + 1.0 / 61)) < 1e-9
        assert abs(result[1].score - (1.0 / 62 + 1.0 / 62)) < 1e-9

    def test_score_replacement(self) -> None:
        """T15: Output chunks have RRF scores, not original scores."""
        rrf = RankFusion(k=60)

        chunk = _make_chunk("orig", score=0.95)
        result = rrf.fuse([chunk])

        assert len(result) == 1
        # Should have RRF score, not original 0.95
        expected_rrf = 1.0 / (60 + 1)
        assert abs(result[0].score - expected_rrf) < 1e-9
        assert result[0].score != 0.95


# ---------- Boundary / Edge ----------


# [unit]
class TestRRFBoundary:
    """T4, T5, T6, T7, T8, T9, T14, T16 — boundary tests."""

    def test_no_args_returns_empty(self) -> None:
        """T4: fuse() with no arguments returns empty list."""
        rrf = RankFusion(k=60)
        result = rrf.fuse()
        assert result == []

    def test_all_empty_lists_returns_empty(self) -> None:
        """T5: fuse([], [], []) returns empty list."""
        rrf = RankFusion(k=60)
        result = rrf.fuse([], [], [])
        assert result == []

    def test_top_k_zero_returns_empty(self) -> None:
        """T6: top_k=0 always returns empty list."""
        rrf = RankFusion(k=60)
        chunks = [_make_chunk(f"c-{i}") for i in range(10)]
        result = rrf.fuse(chunks, top_k=0)
        assert result == []

    def test_top_k_one_returns_single(self) -> None:
        """T7: top_k=1 returns only the highest-scored chunk."""
        rrf = RankFusion(k=60)
        list_a = [_make_chunk("A"), _make_chunk("B")]
        list_b = [_make_chunk("A"), _make_chunk("C")]

        result = rrf.fuse(list_a, list_b, top_k=1)

        assert len(result) == 1
        # A appears in both lists at rank 1, so it has the highest score
        assert result[0].chunk_id == "A"

    def test_single_item_list(self) -> None:
        """T8: Single list with single chunk returns that chunk with correct RRF score."""
        rrf = RankFusion(k=60)
        result = rrf.fuse([_make_chunk("solo", score=5.0)])

        assert len(result) == 1
        assert result[0].chunk_id == "solo"
        expected = 1.0 / (60 + 1)
        assert abs(result[0].score - expected) < 1e-9

    def test_top_k_exceeds_available(self) -> None:
        """T9: top_k > total unique chunks returns all available, no padding."""
        rrf = RankFusion(k=60)
        list_a = [_make_chunk("A"), _make_chunk("B")]
        list_b = [_make_chunk("C")]

        result = rrf.fuse(list_a, list_b, top_k=50)

        assert len(result) == 3
        returned_ids = {c.chunk_id for c in result}
        assert returned_ids == {"A", "B", "C"}

    def test_no_overlap_all_unique(self) -> None:
        """T14: Two lists with zero overlap → all unique chunks returned."""
        rrf = RankFusion(k=60)
        list_a = [_make_chunk(f"a-{i}") for i in range(5)]
        list_b = [_make_chunk(f"b-{i}") for i in range(5)]

        result = rrf.fuse(list_a, list_b, top_k=50)

        assert len(result) == 10
        # Each chunk has a single-list RRF score
        for chunk in result:
            # Score should be 1/(60+rank) for some rank 1..5
            assert chunk.score <= 1.0 / 61
            assert chunk.score >= 1.0 / 65

    def test_large_k_value(self) -> None:
        """T16: Large k (1000) produces very small but correct scores."""
        rrf = RankFusion(k=1000)
        list_a = [_make_chunk("A"), _make_chunk("B")]
        list_b = [_make_chunk("A"), _make_chunk("C")]

        result = rrf.fuse(list_a, list_b, top_k=50)

        assert len(result) == 3
        # A appears in both, score = 1/1001 + 1/1001
        a_chunk = next(c for c in result if c.chunk_id == "A")
        expected = 2.0 / 1001
        assert abs(a_chunk.score - expected) < 1e-12


# ---------- Error ----------


# [unit]
class TestRRFError:
    """T10, T11 — error handling tests."""

    def test_k_zero_raises_value_error(self) -> None:
        """T10: k=0 raises ValueError."""
        with pytest.raises(ValueError, match="k must be positive, got 0"):
            RankFusion(k=0)

    def test_k_negative_raises_value_error(self) -> None:
        """T11: k=-5 raises ValueError."""
        with pytest.raises(ValueError, match="k must be positive, got -5"):
            RankFusion(k=-5)
