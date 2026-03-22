"""Tests for EvalRunner and StageMetrics — Feature #42.

Covers: T01–T08, T11–T16, T18–T24, T26 from Test Inventory.

# [no integration test] — pure computation over in-memory data, no external I/O.
# EvalRunner computes IR metrics from GoldenDataset + Retriever results.
# Retriever is mocked at system boundary (it talks to ES/Qdrant).
# Security: N/A — internal CLI tool with no user-facing input.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.eval.annotator import Annotation, EvalQuery
from src.eval.golden_dataset import GoldenDataset
from src.eval.runner import EvalRunner, StageMetrics, _mean
from src.query.exceptions import RetrievalError
from src.query.scored_chunk import ScoredChunk


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_scored_chunk(chunk_id: str, score: float = 1.0) -> ScoredChunk:
    return ScoredChunk(
        chunk_id=chunk_id,
        content_type="code",
        repo_id="repo-1",
        file_path="f.py",
        content="x",
        score=score,
    )


def _make_golden(
    queries: list[EvalQuery],
    annotations: dict[str, list[Annotation]],
    kappa: float = 0.8,
) -> GoldenDataset:
    return GoldenDataset(
        repo_slug="test-repo",
        queries=queries,
        annotations=annotations,
        kappa=kappa,
    )


def _make_retriever(**kwargs) -> MagicMock:
    """Create a mock Retriever with async search methods."""
    retriever = MagicMock()
    retriever._qdrant = MagicMock()  # vector search available
    retriever.vector_code_search = AsyncMock(**kwargs)
    retriever.bm25_code_search = AsyncMock(**kwargs)
    return retriever


# ---------------------------------------------------------------------------
# T01: Happy path — all 4 metrics computed correctly (hand-calculated)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_stage_vector_computes_all_metrics():
    """T01: Given 2 golden queries with known results, metrics match hand-calc."""
    # Query 1: results = [c1, c2, c3], relevant = {c1, c3}
    #   MRR@10 = 1/1 = 1.0 (c1 at rank 1)
    #   NDCG@10: rel(c1)=3, rel(c2)=0, rel(c3)=2
    #     DCG = (2^3-1)/log2(2) + (2^0-1)/log2(3) + (2^2-1)/log2(4)
    #         = 7/1 + 0/1.585 + 3/2 = 7.0 + 0.0 + 1.5 = 8.5
    #     IDCG: sorted [3,2] at k=10 = (2^3-1)/log2(2) + (2^2-1)/log2(3) = 7.0 + 1.893 = 8.893
    #     NDCG = 8.5 / 8.893 ≈ 0.9558
    #   Recall@200 = 2/2 = 1.0
    #   Precision@3 = 2/3 ≈ 0.6667
    #
    # Query 2: results = [c4, c5], relevant = {c5}
    #   MRR@10 = 1/2 = 0.5 (c5 at rank 2)
    #   NDCG@10: rel(c4)=0, rel(c5)=2
    #     DCG = 0/log2(2) + (2^2-1)/log2(3) = 0 + 3/1.585 = 1.893
    #     IDCG: sorted [2] = (2^2-1)/log2(2) = 3/1 = 3.0
    #     NDCG = 1.893/3.0 = 0.631
    #   Recall@200 = 1/1 = 1.0
    #   Precision@3 = 1/3 ≈ 0.3333

    q1 = EvalQuery(text="query1", repo_id="repo-1", language="python", category="api_usage")
    q2 = EvalQuery(text="query2", repo_id="repo-1", language="python", category="bug_diagnosis")

    annotations = {
        "query1": [
            Annotation(chunk_id="c1", score=3, annotator_run=1),
            Annotation(chunk_id="c3", score=2, annotator_run=1),
        ],
        "query2": [
            Annotation(chunk_id="c5", score=2, annotator_run=1),
        ],
    }

    golden = _make_golden(queries=[q1, q2], annotations=annotations)

    retriever = _make_retriever()
    retriever.vector_code_search = AsyncMock(
        side_effect=[
            [_make_scored_chunk("c1"), _make_scored_chunk("c2"), _make_scored_chunk("c3")],
            [_make_scored_chunk("c4"), _make_scored_chunk("c5")],
        ]
    )

    runner = EvalRunner(retriever=retriever, golden=golden)
    result = await runner.evaluate_stage("vector")

    assert result.stage == "vector"
    assert result.status == "OK"
    assert result.query_count == 2

    # Averages across 2 queries
    expected_mrr = (1.0 + 0.5) / 2  # 0.75
    expected_recall = (1.0 + 1.0) / 2  # 1.0
    expected_prec = (2 / 3 + 1 / 3) / 2  # 0.5

    assert abs(result.mrr_at_10 - expected_mrr) < 1e-6
    assert abs(result.recall_at_200 - expected_recall) < 1e-6
    assert abs(result.precision_at_3 - expected_prec) < 1e-6

    # NDCG hand-calculated
    ndcg_q1 = 8.5 / (7.0 + (2**2 - 1) / math.log2(3))
    ndcg_q2 = ((2**2 - 1) / math.log2(3)) / 3.0
    expected_ndcg = (ndcg_q1 + ndcg_q2) / 2
    assert abs(result.ndcg_at_10 - expected_ndcg) < 1e-4


# ---------------------------------------------------------------------------
# T02: MRR — relevant item at rank 1 → MRR = 1.0
# ---------------------------------------------------------------------------


# [unit]
def test_compute_mrr_first_result_relevant():
    """T02: First result is relevant → MRR@10 = 1.0."""
    q = EvalQuery(text="q", repo_id="r", language="python", category="api_usage")
    golden = _make_golden(
        queries=[q],
        annotations={"q": [Annotation(chunk_id="c1", score=2, annotator_run=1)]},
    )
    runner = EvalRunner(retriever=_make_retriever(), golden=golden)
    assert runner.compute_mrr(["c1", "c2", "c3"], {"c1"}, k=10) == 1.0


# ---------------------------------------------------------------------------
# T03: MRR — relevant item at rank 5 → MRR = 0.2
# ---------------------------------------------------------------------------


# [unit]
def test_compute_mrr_relevant_at_rank_5():
    """T03: Relevant at rank 5 → MRR@10 = 0.2."""
    q = EvalQuery(text="q", repo_id="r", language="python", category="api_usage")
    golden = _make_golden(
        queries=[q],
        annotations={"q": [Annotation(chunk_id="c5", score=2, annotator_run=1)]},
    )
    runner = EvalRunner(retriever=_make_retriever(), golden=golden)
    result = runner.compute_mrr(["c1", "c2", "c3", "c4", "c5"], {"c5"}, k=10)
    assert abs(result - 0.2) < 1e-6


# ---------------------------------------------------------------------------
# T04: NDCG with known graded relevance
# ---------------------------------------------------------------------------


# [unit]
def test_compute_ndcg_hand_calculated():
    """T04: NDCG with graded scores [3,0,2,0] matches hand-calculated value."""
    q = EvalQuery(text="q", repo_id="r", language="python", category="api_usage")
    golden = _make_golden(
        queries=[q],
        annotations={"q": [Annotation(chunk_id="c1", score=3, annotator_run=1)]},
    )
    runner = EvalRunner(retriever=_make_retriever(), golden=golden)

    results = ["c1", "c2", "c3", "c4"]
    rel_scores = {"c1": 3, "c3": 2}

    # DCG@10: (2^3-1)/log2(2) + 0/log2(3) + (2^2-1)/log2(4) + 0/log2(5)
    #       = 7/1 + 0 + 3/2 + 0 = 8.5
    # IDCG: sorted [3,2] → (2^3-1)/log2(2) + (2^2-1)/log2(3) = 7.0 + 1.893 = 8.893
    expected_dcg = 7.0 + 0.0 + 3.0 / 2.0 + 0.0
    expected_idcg = 7.0 + 3.0 / math.log2(3)
    expected_ndcg = expected_dcg / expected_idcg

    ndcg = runner.compute_ndcg(results, rel_scores, k=10)
    assert abs(ndcg - expected_ndcg) < 1e-6


# ---------------------------------------------------------------------------
# T05: Recall@200 — 3 of 5 relevant in results
# ---------------------------------------------------------------------------


# [unit]
def test_compute_recall_partial():
    """T05: 5 relevant items, 3 in top-200 → Recall = 0.6."""
    q = EvalQuery(text="q", repo_id="r", language="python", category="api_usage")
    golden = _make_golden(
        queries=[q],
        annotations={"q": [Annotation(chunk_id="c1", score=2, annotator_run=1)]},
    )
    runner = EvalRunner(retriever=_make_retriever(), golden=golden)

    results = ["c1", "c2", "c3", "c4", "c5"]
    relevant = {"c1", "c3", "c5", "c6", "c7"}
    recall = runner.compute_recall(results, relevant, k=200)
    assert abs(recall - 0.6) < 1e-6


# ---------------------------------------------------------------------------
# T06: Precision@3 — 2 relevant in top-3
# ---------------------------------------------------------------------------


# [unit]
def test_compute_precision_two_of_three():
    """T06: 3 results, 2 relevant in top-3 → Precision@3 = 2/3."""
    q = EvalQuery(text="q", repo_id="r", language="python", category="api_usage")
    golden = _make_golden(
        queries=[q],
        annotations={"q": [Annotation(chunk_id="c1", score=2, annotator_run=1)]},
    )
    runner = EvalRunner(retriever=_make_retriever(), golden=golden)

    results = ["c1", "c2", "c3"]
    relevant = {"c1", "c3"}
    prec = runner.compute_precision(results, relevant, k=3)
    assert abs(prec - 2 / 3) < 1e-6


# ---------------------------------------------------------------------------
# T07: Per-language breakdown with 2 languages
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_stage_per_language_breakdown():
    """T07: 2 queries in different languages → per_language dict has both."""
    q_py = EvalQuery(text="q_py", repo_id="repo-1", language="python", category="api_usage")
    q_java = EvalQuery(text="q_java", repo_id="repo-1", language="java", category="api_usage")

    annotations = {
        "q_py": [Annotation(chunk_id="c1", score=3, annotator_run=1)],
        "q_java": [Annotation(chunk_id="c2", score=2, annotator_run=1)],
    }
    golden = _make_golden(queries=[q_py, q_java], annotations=annotations)

    retriever = _make_retriever()
    retriever.vector_code_search = AsyncMock(
        side_effect=[
            [_make_scored_chunk("c1")],  # Python query → c1 (relevant)
            [_make_scored_chunk("c2")],  # Java query → c2 (relevant)
        ]
    )

    runner = EvalRunner(retriever=retriever, golden=golden)
    result = await runner.evaluate_stage("vector")

    assert "python" in result.per_language
    assert "java" in result.per_language
    # Both queries return their relevant item at rank 1
    assert result.per_language["python"]["mrr_at_10"] == 1.0
    assert result.per_language["java"]["mrr_at_10"] == 1.0


# ---------------------------------------------------------------------------
# T08: N/A stage (rrf not implemented)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_stage_rrf_returns_na():
    """T08: Stage 'rrf' not implemented → StageMetrics with status=N/A."""
    q = EvalQuery(text="q", repo_id="r", language="python", category="api_usage")
    golden = _make_golden(
        queries=[q],
        annotations={"q": [Annotation(chunk_id="c1", score=2, annotator_run=1)]},
    )

    runner = EvalRunner(retriever=_make_retriever(), golden=golden)
    result = await runner.evaluate_stage("rrf")

    assert result.stage == "rrf"
    assert result.status == "N/A"
    assert result.mrr_at_10 is None
    assert result.ndcg_at_10 is None
    assert result.recall_at_200 is None
    assert result.precision_at_3 is None


# ---------------------------------------------------------------------------
# T11: Error — unknown stage → ValueError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_stage_unknown_raises():
    """T11: Unknown stage name raises ValueError."""
    q = EvalQuery(text="q", repo_id="r", language="python", category="api_usage")
    golden = _make_golden(
        queries=[q],
        annotations={"q": [Annotation(chunk_id="c1", score=2, annotator_run=1)]},
    )
    runner = EvalRunner(retriever=_make_retriever(), golden=golden)

    with pytest.raises(ValueError, match="Unknown stage"):
        await runner.evaluate_stage("unknown_stage")


# ---------------------------------------------------------------------------
# T12: Error — compute_mrr k=0 → ValueError
# ---------------------------------------------------------------------------


# [unit]
def test_compute_mrr_k_zero_raises():
    """T12: k=0 raises ValueError."""
    q = EvalQuery(text="q", repo_id="r", language="python", category="api_usage")
    golden = _make_golden(
        queries=[q],
        annotations={"q": [Annotation(chunk_id="c1", score=2, annotator_run=1)]},
    )
    runner = EvalRunner(retriever=_make_retriever(), golden=golden)

    with pytest.raises(ValueError, match="k must be >= 1"):
        runner.compute_mrr(["c1"], {"c1"}, k=0)


# ---------------------------------------------------------------------------
# T13: Error — compute_ndcg k=-1 → ValueError
# ---------------------------------------------------------------------------


# [unit]
def test_compute_ndcg_k_negative_raises():
    """T13: k=-1 raises ValueError."""
    q = EvalQuery(text="q", repo_id="r", language="python", category="api_usage")
    golden = _make_golden(
        queries=[q],
        annotations={"q": [Annotation(chunk_id="c1", score=2, annotator_run=1)]},
    )
    runner = EvalRunner(retriever=_make_retriever(), golden=golden)

    with pytest.raises(ValueError, match="k must be >= 1"):
        runner.compute_ndcg(["c1"], {"c1": 3}, k=-1)


# ---------------------------------------------------------------------------
# T14: Error — compute_recall k=0 → ValueError
# ---------------------------------------------------------------------------


# [unit]
def test_compute_recall_k_zero_raises():
    """T14: k=0 raises ValueError."""
    q = EvalQuery(text="q", repo_id="r", language="python", category="api_usage")
    golden = _make_golden(
        queries=[q],
        annotations={"q": [Annotation(chunk_id="c1", score=2, annotator_run=1)]},
    )
    runner = EvalRunner(retriever=_make_retriever(), golden=golden)

    with pytest.raises(ValueError, match="k must be >= 1"):
        runner.compute_recall(["c1"], {"c1"}, k=0)


# ---------------------------------------------------------------------------
# T15: Error — compute_precision k=0 → ValueError
# ---------------------------------------------------------------------------


# [unit]
def test_compute_precision_k_zero_raises():
    """T15: k=0 raises ValueError."""
    q = EvalQuery(text="q", repo_id="r", language="python", category="api_usage")
    golden = _make_golden(
        queries=[q],
        annotations={"q": [Annotation(chunk_id="c1", score=2, annotator_run=1)]},
    )
    runner = EvalRunner(retriever=_make_retriever(), golden=golden)

    with pytest.raises(ValueError, match="k must be >= 1"):
        runner.compute_precision(["c1"], {"c1"}, k=0)


# ---------------------------------------------------------------------------
# T16: Error — empty golden dataset → ValueError
# ---------------------------------------------------------------------------


def test_eval_runner_empty_golden_raises():
    """T16: Golden dataset with no queries raises ValueError."""
    golden = _make_golden(queries=[], annotations={})

    with pytest.raises(ValueError, match="no queries"):
        EvalRunner(retriever=_make_retriever(), golden=golden)


# ---------------------------------------------------------------------------
# T18: Error — RetrievalError during search → N/A
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_stage_retrieval_error_returns_na():
    """T18: Retriever raises RetrievalError → StageMetrics with status=N/A."""
    q = EvalQuery(text="q", repo_id="r", language="python", category="api_usage")
    golden = _make_golden(
        queries=[q],
        annotations={"q": [Annotation(chunk_id="c1", score=2, annotator_run=1)]},
    )

    retriever = _make_retriever()
    retriever.vector_code_search = AsyncMock(side_effect=RetrievalError("ES down"))

    runner = EvalRunner(retriever=retriever, golden=golden)
    result = await runner.evaluate_stage("vector")

    assert result.status == "N/A"
    assert result.mrr_at_10 is None


# ---------------------------------------------------------------------------
# T19: Boundary — empty results list
# ---------------------------------------------------------------------------


# [unit]
def test_compute_mrr_empty_results():
    """T19: Empty results → MRR = 0.0."""
    q = EvalQuery(text="q", repo_id="r", language="python", category="api_usage")
    golden = _make_golden(
        queries=[q],
        annotations={"q": [Annotation(chunk_id="c1", score=2, annotator_run=1)]},
    )
    runner = EvalRunner(retriever=_make_retriever(), golden=golden)

    assert runner.compute_mrr([], {"c1"}, k=10) == 0.0


# ---------------------------------------------------------------------------
# T20: Boundary — empty relevant set for MRR
# ---------------------------------------------------------------------------


# [unit]
def test_compute_mrr_empty_relevant():
    """T20: Empty relevant set → MRR = 0.0."""
    q = EvalQuery(text="q", repo_id="r", language="python", category="api_usage")
    golden = _make_golden(
        queries=[q],
        annotations={"q": [Annotation(chunk_id="c1", score=2, annotator_run=1)]},
    )
    runner = EvalRunner(retriever=_make_retriever(), golden=golden)

    assert runner.compute_mrr(["c1"], set(), k=10) == 0.0


# ---------------------------------------------------------------------------
# T21: Boundary — empty relevant set for Recall → 1.0
# ---------------------------------------------------------------------------


# [unit]
def test_compute_recall_empty_relevant():
    """T21: Empty relevant set → Recall = 1.0 (vacuously true)."""
    q = EvalQuery(text="q", repo_id="r", language="python", category="api_usage")
    golden = _make_golden(
        queries=[q],
        annotations={"q": [Annotation(chunk_id="c1", score=2, annotator_run=1)]},
    )
    runner = EvalRunner(retriever=_make_retriever(), golden=golden)

    assert runner.compute_recall(["c1"], set(), k=10) == 1.0


# ---------------------------------------------------------------------------
# T22: Boundary — k=1, relevant at rank 2 → MRR=0.0
# ---------------------------------------------------------------------------


# [unit]
def test_compute_mrr_k_1_relevant_beyond():
    """T22: k=1 and relevant item at rank 2 → MRR = 0.0."""
    q = EvalQuery(text="q", repo_id="r", language="python", category="api_usage")
    golden = _make_golden(
        queries=[q],
        annotations={"q": [Annotation(chunk_id="c2", score=2, annotator_run=1)]},
    )
    runner = EvalRunner(retriever=_make_retriever(), golden=golden)

    assert runner.compute_mrr(["c1", "c2"], {"c2"}, k=1) == 0.0


# ---------------------------------------------------------------------------
# T23: Boundary — IDCG=0 (no relevant items) → NDCG=0.0
# ---------------------------------------------------------------------------


# [unit]
def test_compute_ndcg_idcg_zero():
    """T23: No relevant items → IDCG=0 → NDCG=0.0."""
    q = EvalQuery(text="q", repo_id="r", language="python", category="api_usage")
    golden = _make_golden(
        queries=[q],
        annotations={"q": [Annotation(chunk_id="c1", score=2, annotator_run=1)]},
    )
    runner = EvalRunner(retriever=_make_retriever(), golden=golden)

    assert runner.compute_ndcg(["c1"], {}, k=10) == 0.0


# ---------------------------------------------------------------------------
# T24: Boundary — single query golden dataset
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_stage_single_query():
    """T24: Single query → metrics equal to that query's metrics (no averaging distortion)."""
    q = EvalQuery(text="q", repo_id="r", language="python", category="api_usage")
    annotations = {
        "q": [Annotation(chunk_id="c1", score=3, annotator_run=1)],
    }
    golden = _make_golden(queries=[q], annotations=annotations)

    retriever = _make_retriever()
    retriever.bm25_code_search = AsyncMock(
        return_value=[_make_scored_chunk("c1"), _make_scored_chunk("c2")]
    )

    runner = EvalRunner(retriever=retriever, golden=golden)
    result = await runner.evaluate_stage("bm25")

    # c1 at rank 1, relevant → MRR = 1.0
    assert result.mrr_at_10 == 1.0
    # Precision@3 = 1/3
    assert abs(result.precision_at_3 - 1 / 3) < 1e-6
    # Recall@200 = 1/1 = 1.0
    assert result.recall_at_200 == 1.0


# ---------------------------------------------------------------------------
# Real test — pure-function feature #42
# Validates IR metric computation with no mocks, no external I/O.
# ---------------------------------------------------------------------------


@pytest.mark.real
def test_real_eval_runner_pure_metric_computation_feature_42():
    """Real test: EvalRunner IR metrics are pure functions — no external deps."""
    q = EvalQuery(text="q", repo_id="r", language="python", category="api_usage")
    golden = _make_golden(
        queries=[q],
        annotations={
            "q": [
                Annotation(chunk_id="c1", score=3, annotator_run=1),
                Annotation(chunk_id="c3", score=2, annotator_run=1),
            ],
        },
    )
    runner = EvalRunner(retriever=_make_retriever(), golden=golden)

    # MRR: c1 relevant at rank 1 → 1.0
    assert runner.compute_mrr(["c1", "c2", "c3"], {"c1", "c3"}, k=10) == 1.0
    # Precision: 2 relevant in top 3 → 2/3
    assert abs(runner.compute_precision(["c1", "c2", "c3"], {"c1", "c3"}, k=3) - 2 / 3) < 1e-6
    # Recall: 2/2 in results → 1.0
    assert runner.compute_recall(["c1", "c2", "c3"], {"c1", "c3"}, k=10) == 1.0
    # NDCG: hand-verified non-trivial value
    ndcg = runner.compute_ndcg(["c1", "c2", "c3"], {"c1": 3, "c3": 2}, k=3)
    assert 0.0 < ndcg <= 1.0
    # Verify the actual NDCG computation:
    # DCG = (2^3-1)/log2(2) + 0/log2(3) + (2^2-1)/log2(4) = 7 + 0 + 1.5 = 8.5
    # IDCG = (2^3-1)/log2(2) + (2^2-1)/log2(3) = 7 + 1.893 = 8.893
    expected = 8.5 / (7.0 + 3.0 / math.log2(3))
    assert abs(ndcg - expected) < 1e-6


# ---------------------------------------------------------------------------
# T26: Boundary — results shorter than k for precision
# ---------------------------------------------------------------------------


# [unit]
def test_compute_precision_results_shorter_than_k():
    """T26: Results shorter than k → denominator is k, not len(results)."""
    q = EvalQuery(text="q", repo_id="r", language="python", category="api_usage")
    golden = _make_golden(
        queries=[q],
        annotations={"q": [Annotation(chunk_id="c1", score=2, annotator_run=1)]},
    )
    runner = EvalRunner(retriever=_make_retriever(), golden=golden)

    # 1 result, 1 relevant, k=3 → precision = 1/3 (not 1/1)
    prec = runner.compute_precision(["c1"], {"c1"}, k=3)
    assert abs(prec - 1 / 3) < 1e-6


# ---------------------------------------------------------------------------
# T27: _mean helper — empty list returns 0.0
# ---------------------------------------------------------------------------


# [unit]
def test_mean_empty_list_returns_zero():
    """T27: _mean([]) must return 0.0, not any other value."""
    assert _mean([]) == 0.0
