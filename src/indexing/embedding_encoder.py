"""EmbeddingEncoder — generates dense vector embeddings using sentence-transformers."""

from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer

from src.indexing.exceptions import EmbeddingModelError


class EmbeddingEncoder:
    """Encodes text into 1024-dim dense vectors using CodeSage-large."""

    def __init__(
        self,
        model_name: str = "Salesforce/codesage-large",
        batch_size: int = 64,
        device: str | None = None,
    ) -> None:
        self._batch_size = batch_size
        self._query_prefix = "Represent this code search query: "
        try:
            kwargs: dict = {}
            if device is not None:
                kwargs["device"] = device
            self._model = SentenceTransformer(model_name, **kwargs)
        except Exception as exc:
            raise EmbeddingModelError(f"Failed to load model: {exc}") from exc

    def encode_batch(
        self, texts: list[str], is_query: bool = False
    ) -> list[np.ndarray]:
        """Encode a list of texts into 1024-dim float32 vectors.

        Args:
            texts: Non-empty list of text strings to encode.
            is_query: If True, prepend query instruction prefix to each text.

        Returns:
            List of 1024-dim float32 ndarray vectors, one per input text.

        Raises:
            ValueError: If texts is empty.
            EmbeddingModelError: If model inference fails.
        """
        if len(texts) == 0:
            raise ValueError("texts must be non-empty")

        prepared = texts
        if is_query:
            prepared = [self._query_prefix + t for t in texts]

        try:
            all_vectors = self._model.encode(
                prepared,
                batch_size=self._batch_size,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
        except Exception as exc:
            raise EmbeddingModelError(f"Model inference failed: {exc}") from exc

        return [all_vectors[i].astype(np.float32) for i in range(len(all_vectors))]

    def encode_query(self, query: str) -> np.ndarray:
        """Encode a single query string with instruction prefix.

        Args:
            query: Non-empty query string.

        Returns:
            Single 1024-dim float32 ndarray.

        Raises:
            ValueError: If query is empty.
            EmbeddingModelError: If model inference fails.
        """
        if not query:
            raise ValueError("query must be non-empty")
        return self.encode_batch([query], is_query=True)[0]
