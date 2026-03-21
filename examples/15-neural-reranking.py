#!/usr/bin/env python3
"""Example: Neural Reranking via DashScope reranker API.

Demonstrates the Reranker module that re-scores fused candidates using
an external reranker API (qwen3-rerank) and selects top-K results.
Also shows graceful fallback when the API is unavailable.

Requires: RERANKER_API_KEY set in .env or environment.
"""

from __future__ import annotations

import os

from src.query.scored_chunk import ScoredChunk


def make_candidates() -> list[ScoredChunk]:
    """Create sample fused candidates with RRF scores."""
    return [
        ScoredChunk(
            chunk_id="c1", content_type="code", repo_id="my-repo",
            file_path="src/timeout.py", score=0.5,
            content="def configure_timeout(client, timeout_ms): client.timeout = timeout_ms",
            language="python", chunk_type="function", symbol="configure_timeout",
        ),
        ScoredChunk(
            chunk_id="c2", content_type="code", repo_id="my-repo",
            file_path="src/utils.py", score=0.45,
            content="def sort_list(items): return sorted(items)",
            language="python", chunk_type="function", symbol="sort_list",
        ),
        ScoredChunk(
            chunk_id="c3", content_type="code", repo_id="my-repo",
            file_path="src/webclient.py", score=0.4,
            content="class WebClient:\n    def __init__(self, base_url, timeout=30):\n        self.timeout = timeout",
            language="python", chunk_type="class", symbol="WebClient",
        ),
        ScoredChunk(
            chunk_id="c4", content_type="doc", repo_id="my-repo",
            file_path="docs/configuration.md", score=0.35,
            content="## Timeout Configuration\n\nSet the webclient timeout to control request duration.",
            language=None, chunk_type=None, symbol=None,
            breadcrumb="docs > configuration", heading_level=2,
        ),
        ScoredChunk(
            chunk_id="c5", content_type="code", repo_id="my-repo",
            file_path="src/logging.py", score=0.3,
            content="import logging\nlogger = logging.getLogger(__name__)",
            language="python", chunk_type="function", symbol="logger",
        ),
    ]


def demo_reranking():
    """Demo 1: Reranking with real DashScope API."""
    from src.query.reranker import Reranker

    api_key = os.environ.get("RERANKER_API_KEY", "")
    if not api_key:
        print("RERANKER_API_KEY not set — skipping real API demo")
        print("Set it in .env: RERANKER_API_KEY=your-key")
        return

    reranker = Reranker()  # reads from env vars
    candidates = make_candidates()

    print("=== Neural Reranking (qwen3-rerank API) ===")
    print(f"Query: 'webclient timeout configuration'")
    print(f"Input: {len(candidates)} fused candidates (RRF scores)\n")

    results = reranker.rerank(
        query="webclient timeout configuration",
        candidates=candidates,
        top_k=3,
    )

    print(f"Output: {len(results)} reranked results\n")
    for i, chunk in enumerate(results, 1):
        print(f"  {i}. [{chunk.content_type}] {chunk.symbol or chunk.file_path}")
        print(f"     Score: {chunk.score:.4f} (was RRF: original)")
        print(f"     File: {chunk.file_path}")
        print()


def demo_fallback():
    """Demo 2: Graceful fallback when API key is missing."""
    from src.query.reranker import Reranker

    # Force no API key
    reranker = Reranker.__new__(Reranker)
    reranker._model = "qwen3-rerank"
    reranker._api_key = ""
    reranker._base_url = "https://example.com/v1"
    reranker._threshold = 0.0
    reranker._timeout = 30.0

    candidates = make_candidates()[:3]
    results = reranker.rerank("query", candidates, top_k=3)

    print("=== Fallback Mode (No API Key) ===")
    print(f"Input: {len(candidates)} candidates")
    print(f"Output: {len(results)} results (fusion order preserved)\n")
    for i, chunk in enumerate(results, 1):
        print(f"  {i}. {chunk.symbol or chunk.file_path} (score: {chunk.score:.2f})")


if __name__ == "__main__":
    demo_reranking()
    print()
    demo_fallback()
