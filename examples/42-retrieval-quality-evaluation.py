#!/usr/bin/env python3
"""Example: Retrieval Quality Evaluation & Reporting (Feature #42).

Demonstrates how to:
1. Create an EvalRunner from a golden dataset and retriever
2. Evaluate a retrieval stage and compute IR metrics
3. Generate a Markdown evaluation report
4. Compare against a previous report with delta computation

This example uses synthetic data — no live services required.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio

from src.eval.annotator import Annotation, EvalQuery
from src.eval.golden_dataset import GoldenDataset
from src.eval.report import ReportGenerator
from src.eval.runner import EvalRunner, StageMetrics


def make_mock_retriever():
    """Create a mock retriever that returns predetermined results."""
    from src.query.scored_chunk import ScoredChunk

    def make_chunk(chunk_id: str, score: float = 1.0) -> ScoredChunk:
        return ScoredChunk(
            chunk_id=chunk_id,
            content_type="code",
            repo_id="demo-repo",
            file_path="example.py",
            content="def example(): pass",
            score=score,
        )

    retriever = MagicMock()
    retriever._qdrant = MagicMock()  # Vector search available
    retriever.vector_code_search = AsyncMock(
        return_value=[
            make_chunk("chunk-1", 0.95),
            make_chunk("chunk-2", 0.80),
            make_chunk("chunk-3", 0.65),
            make_chunk("chunk-4", 0.50),
        ]
    )
    retriever.bm25_code_search = AsyncMock(
        return_value=[
            make_chunk("chunk-2", 12.5),
            make_chunk("chunk-1", 10.2),
            make_chunk("chunk-5", 8.0),
        ]
    )
    return retriever


async def main():
    # --- Step 1: Build a synthetic golden dataset ---
    queries = [
        EvalQuery(
            text="How to configure logging in Flask?",
            repo_id="demo-repo",
            language="python",
            category="configuration",
        ),
        EvalQuery(
            text="Find database connection pool implementation",
            repo_id="demo-repo",
            language="python",
            category="api_usage",
        ),
    ]

    annotations = {
        "How to configure logging in Flask?": [
            Annotation(chunk_id="chunk-1", score=3, annotator_run=1),
            Annotation(chunk_id="chunk-3", score=2, annotator_run=1),
        ],
        "Find database connection pool implementation": [
            Annotation(chunk_id="chunk-2", score=3, annotator_run=1),
            Annotation(chunk_id="chunk-5", score=1, annotator_run=1),
        ],
    }

    golden = GoldenDataset(
        repo_slug="demo-repo",
        queries=queries,
        annotations=annotations,
        kappa=0.85,
    )

    # --- Step 2: Create EvalRunner and evaluate stages ---
    retriever = make_mock_retriever()
    runner = EvalRunner(retriever=retriever, golden=golden)

    print("=== Retrieval Quality Evaluation ===\n")

    # Evaluate vector stage
    vector_metrics = await runner.evaluate_stage("vector")
    print(f"Vector stage: {vector_metrics.status}")
    print(f"  MRR@10:      {vector_metrics.mrr_at_10:.4f}")
    print(f"  NDCG@10:     {vector_metrics.ndcg_at_10:.4f}")
    print(f"  Recall@200:  {vector_metrics.recall_at_200:.4f}")
    print(f"  Precision@3: {vector_metrics.precision_at_3:.4f}")
    print()

    # Evaluate BM25 stage
    bm25_metrics = await runner.evaluate_stage("bm25")
    print(f"BM25 stage: {bm25_metrics.status}")
    print(f"  MRR@10:      {bm25_metrics.mrr_at_10:.4f}")
    print(f"  NDCG@10:     {bm25_metrics.ndcg_at_10:.4f}")
    print(f"  Recall@200:  {bm25_metrics.recall_at_200:.4f}")
    print(f"  Precision@3: {bm25_metrics.precision_at_3:.4f}")
    print()

    # Evaluate unimplemented stage (RRF)
    rrf_metrics = await runner.evaluate_stage("rrf")
    print(f"RRF stage: {rrf_metrics.status} (not yet implemented)")
    print()

    # --- Step 3: Generate report ---
    generator = ReportGenerator()
    report = generator.generate([vector_metrics, bm25_metrics, rrf_metrics])
    print("=== Generated Report (no previous) ===\n")
    print(report[:500] + "...\n" if len(report) > 500 else report + "\n")

    # --- Step 4: Delta comparison with mock previous report ---
    prev_report = (
        "# Retrieval Quality Evaluation Report\n\n"
        "**Date**: 2026-03-20\n\n"
        "## Overall Scores\n\n"
        "| Stage | MRR@10 | NDCG@10 | Recall@200 | Precision@3 |\n"
        "|-------|--------|---------|------------|-------------|\n"
        "| vector | 0.4000 | 0.5000 | 0.3000 | 0.2000 |\n"
        "| bm25 | 0.3500 | 0.4500 | 0.2500 | 0.1500 |\n"
    )

    report_with_delta = generator.generate(
        [vector_metrics, bm25_metrics, rrf_metrics],
        prev_report=prev_report,
    )

    # Extract and show just the delta section
    if "Delta" in report_with_delta:
        delta_start = report_with_delta.index("## Delta")
        print("=== Delta Section ===\n")
        print(report_with_delta[delta_start:])


if __name__ == "__main__":
    asyncio.run(main())
