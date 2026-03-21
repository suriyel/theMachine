"""RankFusion — Reciprocal Rank Fusion (RRF) for merging ranked lists."""

from __future__ import annotations

from dataclasses import replace

from src.query.scored_chunk import ScoredChunk


class RankFusion:
    """Merges multiple ranked lists using Reciprocal Rank Fusion (RRF)."""

    def __init__(self, k: int = 60) -> None:
        if k <= 0:
            msg = f"k must be positive, got {k}"
            raise ValueError(msg)
        self._k = k

    def fuse(
        self, *result_lists: list[ScoredChunk], top_k: int = 50
    ) -> list[ScoredChunk]:
        """Merge ranked lists using RRF and return top_k results.

        Each input list is treated as a ranked list (index 0 = rank 1).
        Chunks appearing in multiple lists receive boosted scores.
        """
        score_map: dict[str, tuple[float, ScoredChunk]] = {}

        for result_list in result_lists:
            for rank, chunk in enumerate(result_list, start=1):
                rrf = self._rrf_score(rank)
                if chunk.chunk_id in score_map:
                    accumulated, existing = score_map[chunk.chunk_id]
                    score_map[chunk.chunk_id] = (accumulated + rrf, existing)
                else:
                    score_map[chunk.chunk_id] = (rrf, chunk)

        if not score_map:
            return []

        sorted_entries = sorted(
            score_map.values(), key=lambda x: x[0], reverse=True
        )

        return [
            replace(chunk, score=score)
            for score, chunk in sorted_entries[:top_k]
        ]

    def _rrf_score(self, rank: int) -> float:
        """Compute RRF score: 1 / (k + rank)."""
        return 1.0 / (self._k + rank)
