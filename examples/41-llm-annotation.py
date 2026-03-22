#!/usr/bin/env python3
"""Example: LLM Query Generation & Relevance Annotation (Feature #41).

Demonstrates LLMAnnotator with mocked OpenAI client for query generation,
dual annotation, disagreement resolution, and golden dataset persistence.

Usage:
    python examples/41-llm-annotation.py
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import asdict
from unittest.mock import MagicMock, patch

from src.eval.annotator import Annotation, EvalQuery, LLMAnnotator
from src.eval.corpus_builder import EvalRepo
from src.eval.golden_dataset import GoldenDataset
from src.query.scored_chunk import ScoredChunk


def _mock_query_response(n: int = 60) -> str:
    """Build a fake LLM response with N queries."""
    categories = ["api_usage", "bug_diagnosis", "configuration", "architecture"]
    queries = [
        {"text": f"How to use feature {i}?", "category": categories[i % 4]}
        for i in range(n)
    ]
    return json.dumps({"queries": queries})


def main():
    # --- 1. Query Generation (mocked) ---
    print("=== Query Generation ===")
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = _mock_query_response(60)

    with patch.dict("os.environ", {
        "MINIMAX_API_KEY": "test-key",
        "MINIMAX_BASE_URL": "https://api.minimaxi.com/v1",
        "EVAL_LLM_PROVIDER": "minimax",
    }):
        with patch("src.eval.annotator.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            annotator = LLMAnnotator(provider="minimax")
            repo = EvalRepo(name="flask", url="https://github.com/pallets/flask",
                          language="python", branch="main")
            queries = annotator.generate_queries(repo, chunk_count=200, n_queries=60)

    print(f"Generated {len(queries)} queries")
    for cat in ["api_usage", "bug_diagnosis", "configuration", "architecture"]:
        count = sum(1 for q in queries if q.category == cat)
        print(f"  {cat}: {count}")

    # --- 2. Dual Annotation (mocked) ---
    print("\n=== Dual Annotation ===")
    chunk = ScoredChunk(
        chunk_id="c1", content_type="code", repo_id="flask", file_path="app.py",
        language="python", chunk_type="function", symbol="create_app",
        content="def create_app(): ...", score=0.9,
    )

    # Simulate scores (2, 2) -> agree, final = 2
    score_resp_2 = MagicMock()
    score_resp_2.choices = [MagicMock()]
    score_resp_2.choices[0].message.content = "2"

    with patch.dict("os.environ", {
        "MINIMAX_API_KEY": "test-key",
        "EVAL_LLM_PROVIDER": "minimax",
    }):
        with patch("src.eval.annotator.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = score_resp_2
            mock_openai.return_value = mock_client

            annotator = LLMAnnotator(provider="minimax")
            annotations = annotator.annotate_relevance(queries[0], [chunk])

    print(f"Annotation: chunk={annotations[0].chunk_id}, score={annotations[0].score}, runs={annotations[0].annotator_run}")

    # --- 3. Cohen's Kappa ---
    print("\n=== Cohen's Kappa ===")
    pairs = [(2, 2), (1, 1), (3, 3), (2, 1), (0, 0)]
    kappa = LLMAnnotator._compute_kappa(pairs)
    print(f"Kappa for {len(pairs)} pairs: {kappa:.3f}")

    # --- 4. Golden Dataset Save/Load ---
    print("\n=== Golden Dataset ===")
    dataset = GoldenDataset(
        repo_slug="flask",
        queries=queries[:5],
        annotations={"How to use feature 0?": annotations},
        kappa=kappa,
        provider="minimax",
        model="MiniMax-M2.7",
    )

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        path = f.name

    dataset.save(path)
    loaded = GoldenDataset.load(path)
    print(f"Saved and loaded: {loaded.repo_slug}, {len(loaded.queries)} queries, kappa={loaded.kappa:.3f}")


if __name__ == "__main__":
    main()
