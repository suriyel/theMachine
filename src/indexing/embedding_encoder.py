"""EmbeddingEncoder — generates dense vector embeddings via OpenAI-compatible API."""

from __future__ import annotations

import os

import httpx
import numpy as np

from src.indexing.exceptions import EmbeddingModelError

# DashScope API has a per-request input limit of 6 texts for text-embedding-v3.
# We batch in groups of this size to stay within the limit.
_API_BATCH_SIZE = 6


class EmbeddingEncoder:
    """Encodes text into 1024-dim dense vectors via an OpenAI-compatible embedding API.

    Default configuration targets Alibaba DashScope text-embedding-v3.
    """

    def __init__(
        self,
        model_name: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        dimensions: int = 1024,
        batch_size: int = _API_BATCH_SIZE,
        timeout: float = 60.0,
    ) -> None:
        self._model = model_name or os.environ.get("EMBEDDING_MODEL", "text-embedding-v3")
        self._api_key = api_key or os.environ.get("EMBEDDING_API_KEY", "")
        self._base_url = (base_url or os.environ.get(
            "EMBEDDING_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        )).rstrip("/")
        self._dimensions = dimensions
        self._batch_size = batch_size
        self._timeout = timeout
        self._query_prefix = "Represent this code search query: "

        if not self._api_key:
            raise EmbeddingModelError(
                "Failed to load model: EMBEDDING_API_KEY is required"
            )

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
            EmbeddingModelError: If API call fails.
        """
        if len(texts) == 0:
            raise ValueError("texts must be non-empty")

        # Truncate texts exceeding API input limit (8192 tokens ≈ 6000 chars for code)
        _MAX_CHARS = 6000
        prepared = [t[:_MAX_CHARS] if len(t) > _MAX_CHARS else t for t in texts]
        if is_query:
            prepared = [self._query_prefix + t for t in prepared]

        # Split into batches to respect API input limits
        all_vectors: list[np.ndarray] = []
        for start in range(0, len(prepared), self._batch_size):
            batch = prepared[start : start + self._batch_size]
            batch_vectors = self._call_api(batch)
            all_vectors.extend(batch_vectors)

        return all_vectors

    def encode_query(self, query: str) -> np.ndarray:
        """Encode a single query string with instruction prefix.

        Args:
            query: Non-empty query string.

        Returns:
            Single 1024-dim float32 ndarray.

        Raises:
            ValueError: If query is empty.
            EmbeddingModelError: If API call fails.
        """
        if not query:
            raise ValueError("query must be non-empty")
        return self.encode_batch([query], is_query=True)[0]

    def _call_api(self, texts: list[str]) -> list[np.ndarray]:
        """Call the OpenAI-compatible embeddings endpoint.

        Returns:
            List of float32 ndarray vectors in the same order as input texts.
        """
        url = f"{self._base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "input": texts,
            "dimensions": self._dimensions,
        }

        try:
            # Clear proxy env vars for direct HTTPS connections
            env_overrides: dict[str, str] = {}
            for key in ("ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy",
                        "HTTPS_PROXY", "https_proxy"):
                val = os.environ.pop(key, None)
                if val is not None:
                    env_overrides[key] = val
            try:
                resp = httpx.post(
                    url, json=payload, headers=headers, timeout=self._timeout
                )
            finally:
                os.environ.update(env_overrides)

            resp.raise_for_status()
            result = resp.json()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:500] if exc.response else ""
            raise EmbeddingModelError(
                f"Model inference failed: HTTP {exc.response.status_code} — {body}"
            ) from exc
        except Exception as exc:
            raise EmbeddingModelError(
                f"Model inference failed: {exc}"
            ) from exc

        data = result.get("data")
        if not data or len(data) != len(texts):
            raise EmbeddingModelError(
                f"Model inference failed: expected {len(texts)} embeddings, "
                f"got {len(data) if data else 0}"
            )

        # Sort by index (API may return out of order) and convert to ndarray
        sorted_data = sorted(data, key=lambda d: d["index"])
        return [
            np.array(d["embedding"], dtype=np.float32) for d in sorted_data
        ]
