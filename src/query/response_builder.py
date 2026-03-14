"""Context Response Builder module - builds context results from candidates."""

from dataclasses import dataclass
from typing import List

from src.query.retriever import Candidate
from src.query.api.v1.endpoints.query import ContextResult


@dataclass
class ContextResponseBuilder:
    """Builds ContextResult list from ranked Candidate list.

    Transforms search candidates into the response format expected by the API,
    limiting to top-k results sorted by relevance score.
    """

    def __init__(self, top_k: int = 3):
        """Initialize the builder.

        Args:
            top_k: Maximum number of results to return (default 3)
        """
        if top_k < 1:
            raise ValueError("top_k must be at least 1")
        self._top_k = top_k

    def build(self, candidates: List[Candidate]) -> List[ContextResult]:
        """Build top-k context results from candidates.

        Args:
            candidates: List of Candidate objects (already ranked by previous pipeline stages)

        Returns:
            List of ContextResult objects (max top_k), sorted by score descending.
            Returns empty list if no candidates provided.
        """
        if not candidates:
            return []

        # Sort by score descending, then by chunk_id for stability
        sorted_candidates = sorted(
            candidates,
            key=lambda c: (c.score, c.chunk_id),
            reverse=True
        )

        # Take top k
        top_candidates = sorted_candidates[:self._top_k]

        # Transform to ContextResult
        return [
            ContextResult(
                repository=c.repo_name,
                file_path=c.file_path,
                symbol=c.symbol,
                score=c.score,
                content=c.content,
            )
            for c in top_candidates
        ]
