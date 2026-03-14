"""Rank Fusion module - Reciprocal Rank Fusion (RRF) for merging search results.

This module provides the RankFusion class for merging keyword and semantic
retrieval results using the Reciprocal Rank Fusion algorithm.
"""
from dataclasses import dataclass

from src.query.retriever import Candidate


@dataclass
class RankFusion:
    """Reciprocal Rank Fusion (RRF) for merging search results.

    The RRF algorithm combines multiple ranked lists by computing a score
    for each document based on its position in each list:

        score(doc) = sum(1.0 / (k + rank(doc_in_list)))

    where k is a constant (default 60) that controls how much position matters.

    Attributes:
        k: The constant used in the RRF formula. Higher values reduce
           the impact of position differences. Default is 60.
    """

    k: int = 60

    def fuse(
        self, keyword_results: list[Candidate], semantic_results: list[Candidate]
    ) -> list[Candidate]:
        """Fuse keyword and semantic retrieval results using RRF.

        Args:
            keyword_results: List of candidates from keyword retrieval,
                           ordered by rank (best first)
            semantic_results: List of candidates from semantic retrieval,
                            ordered by rank (best first)

        Returns:
            Fused list of candidates ordered by RRF score (highest first).
            Duplicates (same chunk_id) are deduplicated - the candidate
            from the higher-ranked list is kept.
        """
        if not keyword_results and not semantic_results:
            return []

        # Build a map of chunk_id -> Candidate (keep first occurrence)
        candidates_map: dict[str, Candidate] = {}

        # Add keyword results to the map
        for candidate in keyword_results:
            if candidate.chunk_id not in candidates_map:
                candidates_map[candidate.chunk_id] = candidate

        # Add semantic results to the map (if not already present)
        for candidate in semantic_results:
            if candidate.chunk_id not in candidates_map:
                candidates_map[candidate.chunk_id] = candidate

        # Compute RRF scores
        scores: dict[str, float] = {}

        # Score from keyword results
        for rank, candidate in enumerate(keyword_results):
            if candidate.chunk_id not in scores:
                scores[candidate.chunk_id] = 0.0
            scores[candidate.chunk_id] += 1.0 / (self.k + rank)

        # Score from semantic results
        for rank, candidate in enumerate(semantic_results):
            if candidate.chunk_id not in scores:
                scores[candidate.chunk_id] = 0.0
            scores[candidate.chunk_id] += 1.0 / (self.k + rank)

        # Sort by RRF score (descending), then by chunk_id for stability
        sorted_chunk_ids = sorted(
            scores.keys(), key=lambda cid: (-scores[cid], cid)
        )

        # Build result list with original candidate data
        result: list[Candidate] = []
        for chunk_id in sorted_chunk_ids:
            candidate = candidates_map[chunk_id]
            # Create a new Candidate preserving original score (RRF score used only for ordering)
            fused_candidate = Candidate(
                chunk_id=candidate.chunk_id,
                repo_name=candidate.repo_name,
                file_path=candidate.file_path,
                symbol=candidate.symbol,
                content=candidate.content,
                score=candidate.score,  # Preserve original search score
                language=candidate.language,
            )
            result.append(fused_candidate)

        return result
