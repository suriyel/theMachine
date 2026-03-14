"""Neural Reranker module - Cross-encoder based reranking.

This module provides the NeuralReranker class which reorders candidate
results using a cross-encoder neural network model (bge-reranker).
"""
from dataclasses import dataclass
from typing import Any

import torch
from sentence_transformers import CrossEncoder


class RerankerError(Exception):
    """Exception raised when reranking fails."""
    pass


@dataclass
class RerankerConfig:
    """Configuration for NeuralReranker.

    Attributes:
        model_name: Name of the cross-encoder model (default: BAAI/bge-reranker-v2-m3)
        max_length: Maximum token length for input (default: 512)
    """
    model_name: str = "BAAI/bge-reranker-v2-m3"
    max_length: int = 512


class NeuralReranker:
    """Cross-encoder based neural reranker.

    Reorders candidate results using a pre-trained cross-encoder model
    that scores query-document pairs for relevance.

    Attributes:
        model: The CrossEncoder model instance
        model_name: Name of the model
        max_length: Maximum token length for inputs
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3", max_length: int = 512):
        """Initialize the NeuralReranker.

        Args:
            model_name: Name of the cross-encoder model
            max_length: Maximum token length for inputs

        Raises:
            RerankerError: If model loading fails
        """
        self.model_name = model_name
        self.max_length = max_length
        self.model = None

        try:
            self._load_model()
        except Exception as e:
            raise RerankerError(f"Failed to load reranker model: {e}") from e

    def _load_model(self) -> CrossEncoder:
        """Load the cross-encoder model.

        Prefers CUDA if available, falls back to CPU.

        Returns:
            The loaded CrossEncoder model
        """
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = CrossEncoder(
            self.model_name,
            max_length=self.max_length,
            device=device
        )
        return self.model

    def rerank(self, query: str, candidates: list) -> list:
        """Rerank candidates using neural relevance scoring.

        If fewer than 2 candidates are provided, returns them in original order
        without invoking the model (pass-through behavior).

        Args:
            query: The search query
            candidates: List of Candidate objects to rerank

        Returns:
            List of candidates reordered by neural relevance score (descending)

        Raises:
            RerankerError: If reranking fails
        """
        # Pass-through for edge cases
        if not candidates:
            return []
        if len(candidates) < 2:
            return candidates

        try:
            # Build query-document pairs
            pairs = [(query, candidate.content) for candidate in candidates]

            # Get relevance scores from cross-encoder
            scores = self.model.predict(pairs)

            # Update candidate scores with neural relevance
            for candidate, score in zip(candidates, scores):
                candidate.score = float(score)

            # Sort by score descending
            reranked = sorted(candidates, key=lambda c: c.score, reverse=True)

            return reranked

        except Exception as e:
            raise RerankerError(f"Reranking failed: {e}") from e
