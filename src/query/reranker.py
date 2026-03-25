"""Reranker — Neural reranking via DashScope-compatible rerank API."""

from __future__ import annotations

import logging
import os
from dataclasses import replace

import httpx

from src.query.scored_chunk import ScoredChunk

log = logging.getLogger(__name__)


class Reranker:
    """Reranks candidates using an external reranker API (e.g. qwen3-rerank).

    Falls back to fusion-ranked order on API failure.
    """

    def __init__(
        self,
        model_name: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        threshold: float | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._model = model_name or os.environ.get(
            "RERANKER_MODEL", "qwen3-rerank"
        )
        self._api_key = api_key or os.environ.get("RERANKER_API_KEY", "")
        self._base_url = (
            base_url
            or os.environ.get(
                "RERANKER_BASE_URL",
                "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank",
            )
        ).rstrip("/")
        threshold_env = os.environ.get("RERANKER_THRESHOLD")
        self._threshold = (
            threshold
            if threshold is not None
            else float(threshold_env)
            if threshold_env
            else 0.0
        )
        self._timeout = timeout

        if not self._api_key:
            log.warning("RERANKER_API_KEY not set, reranker will fall back to fusion order")

    def rerank(
        self,
        query: str,
        candidates: list[ScoredChunk],
        top_k: int = 6,
    ) -> list[ScoredChunk]:
        """Rerank candidates via reranker API and return top_k results.

        Falls back to fusion-ranked order (input order truncated to top_k)
        if the API key is missing or the API call fails.
        """
        if not candidates:
            return []

        if not self._api_key:
            log.warning(
                "Reranker API key not configured, falling back to fusion order"
            )
            return candidates[:top_k]

        # Filter out empty-content candidates — DashScope rerank API rejects
        # empty documents with 400 InvalidParameter.
        valid = [(i, c) for i, c in enumerate(candidates) if c.content]
        if not valid:
            log.warning("All candidates have empty content, falling back to fusion order")
            return candidates[:top_k]

        orig_indices, valid_candidates = zip(*valid)
        documents = [c.content for c in valid_candidates]

        try:
            results = self._call_api(query, documents, top_k)
        except Exception:
            log.warning(
                "Reranker API call failed, falling back to fusion order",
                exc_info=True,
            )
            return candidates[:top_k]

        # Map API results back to ScoredChunks (remap filtered indices to original)
        scored: list[ScoredChunk] = []
        for item in results:
            filtered_idx = item["index"]
            score = float(item["relevance_score"])
            if score < self._threshold:
                continue
            if filtered_idx < 0 or filtered_idx >= len(valid_candidates):
                continue
            scored.append(replace(valid_candidates[filtered_idx], score=score))

        if not scored:
            log.warning(
                "All candidates below threshold %.2f, falling back to fusion order",
                self._threshold,
            )
            return candidates[:top_k]

        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[:top_k]

    def _call_api(
        self, query: str, documents: list[str], top_n: int
    ) -> list[dict]:
        """Call the DashScope rerank API.

        Returns list of dicts with 'index' and 'relevance_score' keys,
        sorted by relevance_score descending.
        """
        # Detect API format: OpenAI-compatible (/reranks) vs DashScope native
        is_openai_compat = "/compatible" in self._base_url
        url = f"{self._base_url}/reranks" if is_openai_compat else self._base_url
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if is_openai_compat:
            payload = {
                "model": self._model,
                "query": query,
                "documents": documents,
                "top_n": top_n,
            }
        else:
            payload = {
                "model": self._model,
                "input": {
                    "query": query,
                    "documents": documents,
                },
                "parameters": {
                    "top_n": top_n,
                    "return_documents": False,
                },
            }

        # Clear proxy env vars for direct HTTPS connections
        env_overrides: dict[str, str] = {}
        for key in (
            "ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy",
            "HTTPS_PROXY", "https_proxy",
        ):
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
        data = resp.json()

        # DashScope native format: {"output": {"results": [...]}}
        # OpenAI-compatible format: {"results": [...]}
        if "output" in data and "results" in data["output"]:
            return data["output"]["results"]
        if "results" in data:
            return data["results"]

        raise ValueError(f"Unexpected API response format: {list(data.keys())}")
