"""GoldenDataset — persistence for evaluation golden datasets.

Stores and loads query/annotation data as JSON files.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from src.eval.annotator import Annotation, EvalQuery

logger = logging.getLogger(__name__)


@dataclass
class GoldenDataset:
    """A complete golden dataset for one evaluation repository."""

    repo_slug: str
    queries: list[EvalQuery]
    annotations: dict[str, list[Annotation]]
    kappa: float
    provider: str | None = None
    model: str | None = None

    def save(self, path: str) -> None:
        """Save the golden dataset to a JSON file.

        Creates parent directories if they don't exist.
        Uses atomic write via temporary file.
        """
        data = {
            "repo_slug": self.repo_slug,
            "queries": [
                {
                    "text": q.text,
                    "repo_id": q.repo_id,
                    "language": q.language,
                    "category": q.category,
                }
                for q in self.queries
            ],
            "annotations": {
                qtext: [
                    {
                        "chunk_id": a.chunk_id,
                        "score": a.score,
                        "annotator_run": a.annotator_run,
                    }
                    for a in anns
                ]
                for qtext, anns in self.annotations.items()
            },
            "kappa": self.kappa,
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "provider": self.provider,
                "model": self.model,
            },
        }

        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        tmp.rename(p)

    @classmethod
    def load(cls, path: str) -> GoldenDataset:
        """Load a golden dataset from a JSON file.

        Raises:
            FileNotFoundError: If path does not exist.
            ValueError: If JSON is invalid or missing required keys.
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Golden dataset not found: {path}")

        try:
            data = json.loads(p.read_text())
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in golden dataset: {e}") from e

        required = {"repo_slug", "queries", "annotations", "kappa"}
        missing = required - set(data.keys())
        if missing:
            raise ValueError(f"Golden dataset missing keys: {missing}")

        queries = [EvalQuery(**q) for q in data["queries"]]
        annotations = {
            k: [Annotation(**a) for a in v]
            for k, v in data["annotations"].items()
        }

        metadata = data.get("metadata", {})

        return cls(
            repo_slug=data["repo_slug"],
            queries=queries,
            annotations=annotations,
            kappa=data["kappa"],
            provider=metadata.get("provider"),
            model=metadata.get("model"),
        )
