"""LLMAnnotator — LLM-based query generation and dual relevance annotation.

Uses OpenAI-compatible APIs (MiniMax or Zhipu) to generate evaluation queries
and annotate relevance of retrieved code chunks on a 0-3 scale.
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections import Counter
from dataclasses import dataclass

from openai import OpenAI

from src.eval.corpus_builder import EvalRepo
from src.eval.exceptions import LLMAnnotatorError
from src.query.scored_chunk import ScoredChunk

logger = logging.getLogger(__name__)

VALID_CATEGORIES = {"api_usage", "bug_diagnosis", "configuration", "architecture"}

QUERY_SYSTEM_PROMPT = (
    "You are an expert developer generating realistic search queries for a code repository. "
    "Return a JSON object with a 'queries' key containing a list of query objects, "
    "each with 'text' (the query) and 'category' (one of: api_usage, bug_diagnosis, configuration, architecture)."
)

ANNOTATION_SYSTEM_PROMPT = (
    "You are a relevance annotator for code search results. "
    "Given a search query and a code chunk, rate the relevance on a scale of 0-3:\n"
    "0 = Not relevant at all\n"
    "1 = Marginally relevant\n"
    "2 = Fairly relevant\n"
    "3 = Highly relevant\n\n"
    "Respond with ONLY a single integer (0, 1, 2, or 3)."
)

def _extract_json(text: str) -> str:
    """Extract JSON from LLM response that may contain thinking blocks or markdown.

    Strips <think>...</think> blocks and ```json...``` code fences.
    """
    # Remove <think>...</think> blocks (reasoning models)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    # Extract from markdown code fence if present
    match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, flags=re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


PROVIDERS = {
    "minimax": {
        "base_url_env": "MINIMAX_BASE_URL",
        "base_url_default": "https://api.minimaxi.com/v1",
        "api_key_env": "MINIMAX_API_KEY",
        "model_env": "MINIMAX_MODEL",
        "model_default": "MiniMax-M2.7",
    },
    "zhipu": {
        "base_url_env": "ZHIPU_BASE_URL",
        "api_key_env": "ZHIPU_API_KEY",
        "model_env": "ZHIPU_MODEL",
        "model_default": "glm-4",
    },
}


@dataclass
class EvalQuery:
    """A generated evaluation query."""

    text: str
    repo_id: str
    language: str
    category: str


@dataclass
class Annotation:
    """A relevance annotation for a (query, chunk) pair."""

    chunk_id: str
    score: int
    annotator_run: int


class LLMAnnotator:
    """Orchestrates LLM-based query generation and relevance annotation."""

    def __init__(
        self,
        provider: str | None = None,
        retriever=None,
    ) -> None:
        if provider is None:
            provider = os.environ.get("EVAL_LLM_PROVIDER", "minimax")

        self._base_url, self._api_key, self._model = self._resolve_provider_config(provider)
        self._client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        self._retriever = retriever

    @staticmethod
    def _resolve_provider_config(provider: str) -> tuple[str, str, str]:
        """Resolve provider configuration from environment variables.

        Returns (base_url, api_key, model).
        Raises ValueError if provider is unsupported or required env vars are missing.
        """
        if provider not in PROVIDERS:
            raise ValueError(
                f"Unsupported provider: {provider}. Must be one of {list(PROVIDERS.keys())}"
            )

        cfg = PROVIDERS[provider]
        base_url = os.environ.get(cfg["base_url_env"], cfg.get("base_url_default", ""))
        api_key = os.environ.get(cfg["api_key_env"], "")
        model = os.environ.get(cfg["model_env"], cfg.get("model_default", ""))

        if not api_key:
            raise ValueError(f"Missing env var: {cfg['api_key_env']}")
        if not base_url:
            raise ValueError(f"Missing env var: {cfg['base_url_env']}")

        return base_url, api_key, model

    def generate_queries(
        self,
        repo: EvalRepo,
        chunk_count: int,
        n_queries: int = 75,
    ) -> list[EvalQuery]:
        """Generate evaluation queries for a repository using LLM.

        Args:
            repo: The evaluation repository.
            chunk_count: Number of chunks indexed for the repo.
            n_queries: Number of queries to generate (50-100).

        Returns:
            List of EvalQuery objects.

        Raises:
            ValueError: If n_queries outside [50, 100] or chunk_count <= 0.
            LLMAnnotatorError: If LLM call fails or response cannot be parsed.
        """
        if n_queries < 50 or n_queries > 100:
            raise ValueError("n_queries must be between 50 and 100")
        if chunk_count <= 0:
            raise ValueError("chunk_count must be positive")

        prompt = (
            f"Generate exactly {n_queries} diverse search queries for the '{repo.name}' repository "
            f"(language: {repo.language}, {chunk_count} indexed code chunks).\n\n"
            f"Distribute queries across categories approximately:\n"
            f"- api_usage: 30%\n"
            f"- bug_diagnosis: 25%\n"
            f"- configuration: 25%\n"
            f"- architecture: 20%\n\n"
            f"Return a JSON object with a 'queries' key."
        )

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                temperature=0.7,
                seed=42,
                messages=[
                    {"role": "system", "content": QUERY_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            content = _extract_json(content)
            raw = json.loads(content)
        except json.JSONDecodeError as e:
            raise LLMAnnotatorError(f"Failed to parse LLM response: {e}") from e
        except Exception as e:
            raise LLMAnnotatorError(f"Query generation failed: {e}") from e

        queries_raw = raw.get("queries", [])
        if not isinstance(queries_raw, list):
            raise LLMAnnotatorError("Failed to parse LLM response: 'queries' is not a list")

        queries: list[EvalQuery] = []
        for entry in queries_raw:
            cat = entry.get("category", "")
            text = entry.get("text", "")
            if cat not in VALID_CATEGORIES:
                continue
            if not text:
                continue
            queries.append(
                EvalQuery(
                    text=text,
                    repo_id=repo.name,
                    language=repo.language,
                    category=cat,
                )
            )

        if len(queries) > 100:
            queries = queries[:100]
        if len(queries) < 50:
            raise LLMAnnotatorError(
                f"LLM produced fewer than 50 valid queries ({len(queries)})"
            )

        return queries

    def annotate_relevance(
        self,
        query: EvalQuery,
        chunks: list[ScoredChunk],
    ) -> list[Annotation]:
        """Annotate relevance of chunks for a query using dual annotation.

        Args:
            query: The evaluation query.
            chunks: List of retrieved chunks to annotate.

        Returns:
            List of Annotation objects, one per chunk.

        Raises:
            ValueError: If chunks is empty.
            LLMAnnotatorError: If LLM call fails.
        """
        if not chunks:
            raise ValueError("chunks must not be empty")

        annotations: list[Annotation] = []

        for chunk in chunks:
            score_1, score_2 = self._dual_annotate(query.text, chunk)

            if abs(score_1 - score_2) > 1:
                final_score = self._resolve_disagreement(query.text, chunk, (score_1, score_2))
                annotator_run = 3
            else:
                final_score = round((score_1 + score_2) / 2)
                annotator_run = 2

            annotations.append(
                Annotation(
                    chunk_id=chunk.chunk_id,
                    score=final_score,
                    annotator_run=annotator_run,
                )
            )

        return annotations

    def _dual_annotate(self, query: str, chunk: ScoredChunk) -> tuple[int, int]:
        """Run dual annotation: two LLM calls at different temperatures.

        Returns (score_1, score_2) where each is in [0, 3].
        """
        prompt = self._build_annotation_prompt(query, chunk)
        score_1 = self._call_llm_for_score(prompt, temperature=0.1)
        score_2 = self._call_llm_for_score(prompt, temperature=0.3)
        return score_1, score_2

    def _resolve_disagreement(
        self,
        query: str,
        chunk: ScoredChunk,
        scores: tuple[int, int],
    ) -> int:
        """Resolve disagreement via majority vote with a third LLM call."""
        prompt = self._build_annotation_prompt(query, chunk)
        score_3 = self._call_llm_for_score(prompt, temperature=0.2)

        all_scores = [scores[0], scores[1], score_3]
        counter = Counter(all_scores)
        most_common = counter.most_common(1)[0]

        if most_common[1] >= 2:
            return most_common[0]
        # All three different — return median
        return sorted(all_scores)[1]

    def _call_llm_for_score(self, prompt: str, temperature: float) -> int:
        """Call LLM and parse a single integer score in [0, 3].

        Raises LLMAnnotatorError on any failure.
        """
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                temperature=temperature,
                seed=42,
                messages=[
                    {"role": "system", "content": ANNOTATION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
            raw = response.choices[0].message.content.strip()
            # Strip reasoning model <think> blocks and extract just the score
            raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
            # Extract first integer from response
            score_match = re.search(r"\b([0-3])\b", raw)
            if score_match:
                score = int(score_match.group(1))
            else:
                score = int(raw)
        except (ValueError, TypeError) as e:
            raise LLMAnnotatorError(f"Annotation failed: {e}") from e
        except Exception as e:
            raise LLMAnnotatorError(f"Annotation failed: {e}") from e

        if score < 0 or score > 3:
            raise LLMAnnotatorError(f"Score {score} outside [0,3]")

        return score

    @staticmethod
    def _build_annotation_prompt(query: str, chunk: ScoredChunk) -> str:
        """Build the annotation prompt for a (query, chunk) pair."""
        return (
            f"Query: {query}\n\n"
            f"File: {chunk.file_path}\n"
            f"Language: {chunk.language or 'unknown'}\n\n"
            f"Code chunk:\n```\n{chunk.content}\n```\n\n"
            f"Rate the relevance of this code chunk to the query (0-3):"
        )

    @staticmethod
    def _compute_kappa(annotations_pairs: list[tuple[int, int]]) -> float:
        """Compute Cohen's Kappa for inter-annotator agreement.

        Args:
            annotations_pairs: List of (score_1, score_2) tuples.

        Returns:
            Cohen's Kappa as float in [-1.0, 1.0].

        Raises:
            ValueError: If annotations_pairs is empty.
        """
        if not annotations_pairs:
            raise ValueError("No annotation pairs")

        n = len(annotations_pairs)
        k = 4  # categories: 0, 1, 2, 3

        # Build confusion matrix
        matrix = [[0] * k for _ in range(k)]
        for s1, s2 in annotations_pairs:
            matrix[s1][s2] += 1

        # Observed agreement
        p_o = sum(matrix[i][i] for i in range(k)) / n

        # Expected agreement
        p_e = 0.0
        for i in range(k):
            row_sum = sum(matrix[i][j] for j in range(k))
            col_sum = sum(matrix[j][i] for j in range(k))
            p_e += row_sum * col_sum
        p_e = p_e / (n * n)

        if p_e == 1.0:
            return 1.0

        return (p_o - p_e) / (1.0 - p_e)
