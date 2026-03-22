"""Tests for GoldenDataset — Feature #41: LLM Query Generation & Relevance Annotation.

Test Inventory: T05, T06, T19, T20, T29.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.eval.annotator import Annotation, EvalQuery
from src.eval.golden_dataset import GoldenDataset


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sample_queries() -> list[EvalQuery]:
    return [
        EvalQuery(text="how to use flask app", repo_id="flask", language="Python", category="api_usage"),
        EvalQuery(text="debug flask error", repo_id="flask", language="Python", category="bug_diagnosis"),
    ]


def _sample_annotations() -> dict[str, list[Annotation]]:
    return {
        "how to use flask app": [
            Annotation(chunk_id="c1", score=2, annotator_run=2),
            Annotation(chunk_id="c2", score=1, annotator_run=3),
        ],
        "debug flask error": [
            Annotation(chunk_id="c3", score=3, annotator_run=2),
        ],
    }


def _sample_dataset() -> GoldenDataset:
    return GoldenDataset(
        repo_slug="flask",
        queries=_sample_queries(),
        annotations=_sample_annotations(),
        kappa=0.72,
        provider="minimax",
        model="MiniMax-M2.7",
    )


# ---------------------------------------------------------------------------
# T05: Happy path — save writes correct JSON
# ---------------------------------------------------------------------------


class TestGoldenDatasetSave:
    def test_t05_save_writes_complete_json(self, tmp_path):
        """T05: save() writes JSON with all required keys."""
        ds = _sample_dataset()
        path = str(tmp_path / "eval" / "golden" / "flask.json")

        ds.save(path)

        data = json.loads(Path(path).read_text())
        assert data["repo_slug"] == "flask"
        assert len(data["queries"]) == 2
        assert "how to use flask app" in data["annotations"]
        assert data["kappa"] == 0.72
        assert "metadata" in data
        assert data["metadata"]["provider"] == "minimax"
        assert data["metadata"]["model"] == "MiniMax-M2.7"
        assert "generated_at" in data["metadata"]

    def test_t29_save_creates_parent_dirs(self, tmp_path):
        """T29: save() creates non-existent parent directories."""
        ds = _sample_dataset()
        path = str(tmp_path / "deep" / "nested" / "dir" / "flask.json")

        ds.save(path)

        assert Path(path).exists()
        data = json.loads(Path(path).read_text())
        assert data["repo_slug"] == "flask"


# ---------------------------------------------------------------------------
# T06: Happy path — load reconstructs identical dataset
# ---------------------------------------------------------------------------


class TestGoldenDatasetLoad:
    def test_t06_load_reconstructs_dataset(self, tmp_path):
        """T06: load() reconstructs GoldenDataset with all fields."""
        ds = _sample_dataset()
        path = str(tmp_path / "flask.json")
        ds.save(path)

        loaded = GoldenDataset.load(path)

        assert loaded.repo_slug == "flask"
        assert len(loaded.queries) == 2
        assert loaded.queries[0].text == "how to use flask app"
        assert loaded.queries[0].category == "api_usage"
        assert loaded.kappa == 0.72
        assert loaded.provider == "minimax"
        assert loaded.model == "MiniMax-M2.7"
        # Check annotations
        anns = loaded.annotations["how to use flask app"]
        assert len(anns) == 2
        assert anns[0].chunk_id == "c1"
        assert anns[0].score == 2
        assert anns[0].annotator_run == 2


# ---------------------------------------------------------------------------
# T19: Error — load file not found
# ---------------------------------------------------------------------------


class TestGoldenDatasetLoadErrors:
    def test_t19_load_file_not_found(self, tmp_path):
        """T19: load() raises FileNotFoundError for non-existent path."""
        with pytest.raises(FileNotFoundError):
            GoldenDataset.load(str(tmp_path / "nonexistent.json"))

    def test_t20_load_missing_key_raises(self, tmp_path):
        """T20: load() raises ValueError when JSON missing required key 'kappa'."""
        path = tmp_path / "bad.json"
        data = {
            "repo_slug": "flask",
            "queries": [],
            "annotations": {},
            # "kappa" is missing
        }
        path.write_text(json.dumps(data))

        with pytest.raises(ValueError, match="missing keys"):
            GoldenDataset.load(str(path))
