"""EvalRunner — IR metric computation for retrieval quality evaluation.

Evaluates retrieval pipeline stages against golden datasets using
MRR@10, NDCG@10, Recall@200, and Precision@3.
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field

from src.eval.annotator import Annotation, EvalQuery
from src.eval.golden_dataset import GoldenDataset
from src.query.exceptions import RetrievalError

logger = logging.getLogger(__name__)

VALID_STAGES = {"vector", "bm25", "rrf", "reranked"}

MRR_K = 10
NDCG_K = 10
RECALL_K = 200
PRECISION_K = 3


@dataclass
class StageMetrics:
    """Evaluation metrics for a single retrieval stage."""

    stage: str
    mrr_at_10: float | None
    ndcg_at_10: float | None
    recall_at_200: float | None
    precision_at_3: float | None
    per_language: dict[str, dict[str, float | None]]
    query_count: int
    status: str = "OK"


class EvalRunner:
    """Evaluates retrieval stages against a golden dataset."""

    def __init__(self, retriever, golden: GoldenDataset) -> None:
        if not golden.queries:
            raise ValueError("Golden dataset has no queries")

        self._retriever = retriever
        self._golden = golden

        # Build relevance maps from annotations
        # relevant_map: query_text -> set of chunk_ids with score >= 2
        self._relevant_map: dict[str, set[str]] = {}
        # relevance_scores_map: query_text -> {chunk_id: score}
        self._relevance_scores_map: dict[str, dict[str, int]] = {}

        for query in golden.queries:
            anns = golden.annotations.get(query.text, [])
            self._relevant_map[query.text] = {
                a.chunk_id for a in anns if a.score >= 2
            }
            self._relevance_scores_map[query.text] = {
                a.chunk_id: a.score for a in anns
            }

    async def evaluate_stage(self, stage: str) -> StageMetrics:
        """Evaluate a retrieval stage against all golden queries."""
        if stage not in VALID_STAGES:
            raise ValueError(f"Unknown stage: {stage}")

        search_fn = self._get_search_fn(stage)
        if search_fn is None:
            return StageMetrics(
                stage=stage,
                mrr_at_10=None,
                ndcg_at_10=None,
                recall_at_200=None,
                precision_at_3=None,
                per_language={},
                query_count=len(self._golden.queries),
                status="N/A",
            )

        overall_mrr: list[float] = []
        overall_ndcg: list[float] = []
        overall_recall: list[float] = []
        overall_prec: list[float] = []
        lang_accum: dict[str, dict[str, list[float]]] = defaultdict(
            lambda: {"mrr": [], "ndcg": [], "recall": [], "prec": []}
        )

        for query in self._golden.queries:
            try:
                results = await search_fn(
                    query.text, repo_id=query.repo_id, top_k=RECALL_K
                )
            except RetrievalError:
                return StageMetrics(
                    stage=stage,
                    mrr_at_10=None,
                    ndcg_at_10=None,
                    recall_at_200=None,
                    precision_at_3=None,
                    per_language={},
                    query_count=len(self._golden.queries),
                    status="N/A",
                )

            result_ids = [r.chunk_id for r in results]
            relevant = self._relevant_map.get(query.text, set())
            relevance_scores = self._relevance_scores_map.get(query.text, {})

            mrr = self.compute_mrr(result_ids, relevant, k=MRR_K)
            ndcg = self.compute_ndcg(result_ids, relevance_scores, k=NDCG_K)
            recall = self.compute_recall(result_ids, relevant, k=RECALL_K)
            prec = self.compute_precision(result_ids, relevant, k=PRECISION_K)

            overall_mrr.append(mrr)
            overall_ndcg.append(ndcg)
            overall_recall.append(recall)
            overall_prec.append(prec)

            lang_accum[query.language]["mrr"].append(mrr)
            lang_accum[query.language]["ndcg"].append(ndcg)
            lang_accum[query.language]["recall"].append(recall)
            lang_accum[query.language]["prec"].append(prec)

        per_language: dict[str, dict[str, float | None]] = {}
        for lang, metrics in lang_accum.items():
            per_language[lang] = {
                "mrr_at_10": _mean(metrics["mrr"]),
                "ndcg_at_10": _mean(metrics["ndcg"]),
                "recall_at_200": _mean(metrics["recall"]),
                "precision_at_3": _mean(metrics["prec"]),
            }

        return StageMetrics(
            stage=stage,
            mrr_at_10=_mean(overall_mrr),
            ndcg_at_10=_mean(overall_ndcg),
            recall_at_200=_mean(overall_recall),
            precision_at_3=_mean(overall_prec),
            per_language=per_language,
            query_count=len(self._golden.queries),
            status="OK",
        )

    def compute_mrr(
        self, results: list[str], relevant: set[str], k: int
    ) -> float:
        """Mean Reciprocal Rank — 1/rank of first relevant item in top-k."""
        if k < 1:
            raise ValueError("k must be >= 1")
        for i in range(min(k, len(results))):
            if results[i] in relevant:
                return 1.0 / (i + 1)
        return 0.0

    def compute_ndcg(
        self, results: list[str], relevance_scores: dict[str, int], k: int
    ) -> float:
        """Normalized Discounted Cumulative Gain with log2 discounting."""
        if k < 1:
            raise ValueError("k must be >= 1")

        # DCG
        dcg = 0.0
        for i in range(min(k, len(results))):
            rel = relevance_scores.get(results[i], 0)
            dcg += (2**rel - 1) / math.log2(i + 2)

        # IDCG
        ideal_rels = sorted(relevance_scores.values(), reverse=True)[:k]
        idcg = 0.0
        for i, rel in enumerate(ideal_rels):
            idcg += (2**rel - 1) / math.log2(i + 2)

        if idcg == 0.0:
            return 0.0
        return dcg / idcg

    def compute_recall(
        self, results: list[str], relevant: set[str], k: int
    ) -> float:
        """Recall@k — fraction of relevant items found in top-k results."""
        if k < 1:
            raise ValueError("k must be >= 1")
        if len(relevant) == 0:
            return 1.0
        retrieved_at_k = set(results[:k])
        return len(relevant & retrieved_at_k) / len(relevant)

    def compute_precision(
        self, results: list[str], relevant: set[str], k: int
    ) -> float:
        """Precision@k — fraction of top-k results that are relevant."""
        if k < 1:
            raise ValueError("k must be >= 1")
        retrieved_at_k = set(results[:k])
        return len(relevant & retrieved_at_k) / k

    def _get_search_fn(self, stage: str):
        """Map stage name to retriever search method, or None if unavailable."""
        if stage == "vector":
            if self._retriever._qdrant is None:
                return None
            return self._retriever.vector_code_search
        elif stage == "bm25":
            return self._retriever.bm25_code_search
        elif stage == "rrf":
            return None  # Not yet implemented
        elif stage == "reranked":
            return None  # Not yet implemented
        return None


def _mean(values: list[float]) -> float:
    """Compute arithmetic mean, returns 0.0 for empty list."""
    if not values:
        return 0.0
    return sum(values) / len(values)
