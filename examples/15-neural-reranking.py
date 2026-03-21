#!/usr/bin/env python3
"""Example: Neural Reranking with cross-encoder model.

Demonstrates the Reranker module that re-scores fused candidates using
a cross-encoder model (bge-reranker-v2-m3) and selects top-K results.
Also shows graceful fallback when the model is unavailable.
"""

from unittest.mock import MagicMock, patch

import numpy as np

from src.query.scored_chunk import ScoredChunk


def make_candidates(n: int) -> list[ScoredChunk]:
    """Create sample fused candidates with RRF scores."""
    return [
        ScoredChunk(
            chunk_id=f"chunk-{i}",
            content_type="code",
            repo_id="my-repo",
            file_path=f"src/module_{i}.py",
            content=f"def handler_{i}(request): return response_{i}",
            score=0.5 - i * 0.005,  # RRF fusion scores (descending)
            language="python",
            chunk_type="function",
            symbol=f"handler_{i}",
        )
        for i in range(n)
    ]


def demo_reranking():
    """Demo 1: Normal reranking with cross-encoder scores."""
    from src.query.reranker import Reranker

    candidates = make_candidates(20)

    # Mock the CrossEncoder to avoid downloading a real model
    mock_scores = np.array([float(19 - i) for i in range(20)])

    with patch("src.query.reranker.CrossEncoder") as MockCE:
        mock_model = MagicMock()
        mock_model.predict.return_value = mock_scores
        MockCE.return_value = mock_model

        reranker = Reranker(model_name="BAAI/bge-reranker-v2-m3")
        results = reranker.rerank(
            query="spring webclient timeout configuration",
            candidates=candidates,
            top_k=6,
        )

    print("=== Neural Reranking Results ===")
    print(f"Input: {len(candidates)} fused candidates")
    print(f"Output: {len(results)} reranked results\n")
    for i, chunk in enumerate(results, 1):
        print(f"  {i}. {chunk.symbol} (score: {chunk.score:.2f}) — {chunk.file_path}")


def demo_fallback():
    """Demo 2: Graceful fallback when model fails to load."""
    from src.query.reranker import Reranker

    candidates = make_candidates(10)

    with patch("src.query.reranker.CrossEncoder") as MockCE:
        MockCE.side_effect = RuntimeError("Model OOM")
        reranker = Reranker(model_name="unavailable-model")

    results = reranker.rerank("query", candidates, top_k=3)

    print("\n=== Fallback Mode (Model Unavailable) ===")
    print(f"Input: {len(candidates)} candidates")
    print(f"Output: {len(results)} results (fusion order preserved)\n")
    for i, chunk in enumerate(results, 1):
        print(f"  {i}. {chunk.symbol} (score: {chunk.score:.2f}) — {chunk.file_path}")


if __name__ == "__main__":
    demo_reranking()
    demo_fallback()
