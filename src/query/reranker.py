"""Reranker — Neural reranking using cross-encoder model."""

from __future__ import annotations

import logging
import math
from dataclasses import replace

from src.query.scored_chunk import ScoredChunk

log = logging.getLogger(__name__)

try:
    from sentence_transformers import CrossEncoder
except ImportError:  # pragma: no cover
    CrossEncoder = None  # type: ignore[assignment,misc]


class Reranker:
    """Reranks candidates using a cross-encoder model (bge-reranker-v2-m3).

    Falls back to fusion-ranked order on model failure.
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3") -> None:
        self._model_name = model_name
        self._model: CrossEncoder | None = None
        try:
            self._model = CrossEncoder(model_name)
        except Exception:
            log.warning("Failed to load reranker model '%s'", model_name, exc_info=True)

    def rerank(
        self,
        query: str,
        candidates: list[ScoredChunk],
        top_k: int = 6,
    ) -> list[ScoredChunk]:
        """Rerank candidates using cross-encoder and return top_k results.

        Falls back to fusion-ranked order (input order truncated to top_k)
        if the model is unavailable or inference fails.
        """
        if not candidates:
            return []

        if self._model is None:
            log.warning(
                "Reranker model not loaded, falling back to fusion order"
            )
            return candidates[:top_k]

        try:
            pairs = [(query, chunk.content) for chunk in candidates]
            scores = self._model.predict(pairs, batch_size=32)
        except Exception:
            log.warning(
                "Reranker inference failed, falling back to fusion order",
                exc_info=True,
            )
            return candidates[:top_k]

        # Check for NaN in scores
        if any(math.isnan(float(s)) for s in scores):
            log.warning(
                "Reranker produced NaN scores, falling back to fusion order"
            )
            return candidates[:top_k]

        scored = [
            replace(chunk, score=float(s))
            for chunk, s in zip(candidates, scores)
        ]
        scored.sort(key=lambda c: c.score, reverse=True)

        return scored[:top_k]
