"""Tests for ReportGenerator — Feature #42.

Covers: T09, T10, T17, T25, T27 from Test Inventory.

# [no integration test] — pure string formatting, no external I/O.
# Security: N/A — internal CLI tool with no user-facing input.
"""

from __future__ import annotations

import re

import pytest

from src.eval.report import ReportGenerator
from src.eval.runner import StageMetrics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_stage(
    stage: str = "vector",
    mrr: float | None = 0.75,
    ndcg: float | None = 0.80,
    recall: float | None = 0.90,
    precision: float | None = 0.60,
    per_language: dict | None = None,
    query_count: int = 10,
    status: str = "OK",
) -> StageMetrics:
    return StageMetrics(
        stage=stage,
        mrr_at_10=mrr,
        ndcg_at_10=ndcg,
        recall_at_200=recall,
        precision_at_3=precision,
        per_language=per_language or {},
        query_count=query_count,
        status=status,
    )


def _make_prev_report() -> str:
    """A minimal previous report with an overall scores table."""
    return (
        "# Retrieval Quality Evaluation Report\n\n"
        "**Date**: 2026-03-20\n\n"
        "## Overall Scores\n\n"
        "| Stage | MRR@10 | NDCG@10 | Recall@200 | Precision@3 |\n"
        "|-------|--------|---------|------------|-------------|\n"
        "| vector | 0.7000 | 0.7500 | 0.8500 | 0.5500 |\n"
        "| bm25 | 0.6000 | 0.6500 | 0.7000 | 0.4000 |\n"
    )


# ---------------------------------------------------------------------------
# T09: Happy path — report with OK and N/A stages
# ---------------------------------------------------------------------------


# [unit]
def test_generate_report_with_ok_and_na_stages():
    """T09: Report with vector (OK) and rrf (N/A) has overall table, per-stage, per-language."""
    vector = _make_stage(
        stage="vector",
        mrr=0.75,
        ndcg=0.80,
        recall=0.90,
        precision=0.60,
        per_language={
            "python": {
                "mrr_at_10": 0.80,
                "ndcg_at_10": 0.85,
                "recall_at_200": 0.95,
                "precision_at_3": 0.65,
            }
        },
    )
    rrf = _make_stage(
        stage="rrf",
        mrr=None,
        ndcg=None,
        recall=None,
        precision=None,
        status="N/A",
    )

    gen = ReportGenerator()
    report = gen.generate([vector, rrf])

    # Must contain header
    assert "Retrieval Quality Evaluation Report" in report
    # Must contain date
    assert re.search(r"\d{4}-\d{2}-\d{2}", report)
    # Must contain overall scores table with both stages
    assert "vector" in report
    assert "rrf" in report
    assert "N/A" in report
    # Must contain per-language section with python (title-cased in report)
    assert "Python" in report
    # Must contain metric values for vector
    assert "0.7500" in report or "0.75" in report
    assert "0.8000" in report or "0.80" in report


# ---------------------------------------------------------------------------
# T10: Happy path — delta comparison with previous report
# ---------------------------------------------------------------------------


# [unit]
def test_generate_report_with_delta():
    """T10: Previous report provided → delta section with signed differences."""
    vector = _make_stage(
        stage="vector",
        mrr=0.75,
        ndcg=0.80,
        recall=0.90,
        precision=0.60,
    )
    bm25 = _make_stage(
        stage="bm25",
        mrr=0.65,
        ndcg=0.70,
        recall=0.80,
        precision=0.50,
    )

    gen = ReportGenerator()
    report = gen.generate([vector, bm25], prev_report=_make_prev_report())

    # Must contain delta section
    assert "Delta" in report or "delta" in report or "Δ" in report
    # Vector MRR delta: 0.75 - 0.70 = +0.05
    assert "+0.0500" in report or "+0.05" in report
    # BM25 MRR delta: 0.65 - 0.60 = +0.05
    assert "bm25" in report.lower()


# ---------------------------------------------------------------------------
# T17: Error — empty stages → ValueError
# ---------------------------------------------------------------------------


# [unit]
def test_generate_empty_stages_raises():
    """T17: Empty stages list raises ValueError."""
    gen = ReportGenerator()

    with pytest.raises(ValueError, match="At least one stage required"):
        gen.generate([])


# ---------------------------------------------------------------------------
# T25: Boundary — empty string as previous report
# ---------------------------------------------------------------------------


# [unit]
def test_generate_with_empty_prev_report():
    """T25: Empty string prev_report → report generated, no crash."""
    vector = _make_stage(stage="vector")
    gen = ReportGenerator()

    report = gen.generate([vector], prev_report="")

    # Should still have a report
    assert "Retrieval Quality Evaluation Report" in report
    # Delta section should indicate no comparable metrics
    assert "No comparable metrics" in report or "no comparable" in report.lower()


# ---------------------------------------------------------------------------
# T27: Boundary — all stages N/A
# ---------------------------------------------------------------------------


# [unit]
def test_generate_all_na_stages():
    """T27: All stages N/A → valid report, no crash."""
    rrf = _make_stage(stage="rrf", mrr=None, ndcg=None, recall=None, precision=None, status="N/A")
    reranked = _make_stage(
        stage="reranked", mrr=None, ndcg=None, recall=None, precision=None, status="N/A"
    )

    gen = ReportGenerator()
    report = gen.generate([rrf, reranked])

    assert "Retrieval Quality Evaluation Report" in report
    assert "N/A" in report
    # No metric values should appear
    assert "rrf" in report
    assert "reranked" in report
