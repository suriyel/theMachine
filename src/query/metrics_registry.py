"""Prometheus metrics registry for the query service."""

from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

REGISTRY = CollectorRegistry()

QUERY_LATENCY = Histogram(
    "query_latency_seconds",
    "Total query latency",
    labelnames=["query_type", "cache_hit"],
    registry=REGISTRY,
)

RETRIEVAL_LATENCY = Histogram(
    "retrieval_latency_seconds",
    "Per-backend retrieval latency",
    labelnames=["backend"],
    registry=REGISTRY,
)

RERANK_LATENCY = Histogram(
    "rerank_latency_seconds",
    "Reranker inference latency",
    registry=REGISTRY,
)

QUERY_TOTAL = Counter(
    "query_total",
    "Total queries processed",
    labelnames=["query_type"],
    registry=REGISTRY,
)

CACHE_HIT_RATIO = Gauge(
    "cache_hit_ratio",
    "Rolling cache hit ratio",
    registry=REGISTRY,
)

INDEX_SIZE_CHUNKS = Gauge(
    "index_size_chunks",
    "Total chunks per repo",
    labelnames=["repo_id", "content_type"],
    registry=REGISTRY,
)


def record_query_latency(duration_s: float, query_type: str, cache_hit: bool) -> None:
    """Record a query latency observation."""
    QUERY_LATENCY.labels(query_type=query_type, cache_hit=str(cache_hit).lower()).observe(duration_s)
    QUERY_TOTAL.labels(query_type=query_type).inc()


def record_retrieval_latency(duration_s: float, backend: str) -> None:
    """Record a retrieval latency observation."""
    RETRIEVAL_LATENCY.labels(backend=backend).observe(duration_s)


def record_rerank_latency(duration_s: float) -> None:
    """Record a reranker latency observation."""
    RERANK_LATENCY.observe(duration_s)


def set_cache_hit_ratio(ratio: float) -> None:
    """Set the rolling cache hit ratio gauge."""
    CACHE_HIT_RATIO.set(ratio)


def set_index_size(count: int, repo_id: str, content_type: str) -> None:
    """Set the index size gauge for a repo/content_type pair."""
    INDEX_SIZE_CHUNKS.labels(repo_id=repo_id, content_type=content_type).set(count)


def reset_registry() -> None:
    """Reset all metrics by re-creating them. Used by tests for isolation."""
    global REGISTRY, QUERY_LATENCY, RETRIEVAL_LATENCY, RERANK_LATENCY
    global QUERY_TOTAL, CACHE_HIT_RATIO, INDEX_SIZE_CHUNKS

    REGISTRY = CollectorRegistry()

    QUERY_LATENCY = Histogram(
        "query_latency_seconds",
        "Total query latency",
        labelnames=["query_type", "cache_hit"],
        registry=REGISTRY,
    )
    RETRIEVAL_LATENCY = Histogram(
        "retrieval_latency_seconds",
        "Per-backend retrieval latency",
        labelnames=["backend"],
        registry=REGISTRY,
    )
    RERANK_LATENCY = Histogram(
        "rerank_latency_seconds",
        "Reranker inference latency",
        registry=REGISTRY,
    )
    QUERY_TOTAL = Counter(
        "query_total",
        "Total queries processed",
        labelnames=["query_type"],
        registry=REGISTRY,
    )
    CACHE_HIT_RATIO = Gauge(
        "cache_hit_ratio",
        "Rolling cache hit ratio",
        registry=REGISTRY,
    )
    INDEX_SIZE_CHUNKS = Gauge(
        "index_size_chunks",
        "Total chunks per repo",
        labelnames=["repo_id", "content_type"],
        registry=REGISTRY,
    )


# --- Router ---

metrics_router = APIRouter()


@metrics_router.get("/metrics")
async def metrics_endpoint() -> Response:
    """Expose Prometheus metrics in text format."""
    body = generate_latest(REGISTRY)
    return Response(content=body, media_type=CONTENT_TYPE_LATEST)
