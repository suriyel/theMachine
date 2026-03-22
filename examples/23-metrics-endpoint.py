#!/usr/bin/env python3
"""Example: Metrics Endpoint (Feature #23).

Demonstrates the Prometheus-compatible /metrics endpoint by:
1. Creating the FastAPI app with metrics router
2. Recording query, retrieval, and rerank latency observations
3. Setting gauge values for cache hit ratio and index size
4. Fetching /metrics and printing Prometheus text output
"""

from fastapi.testclient import TestClient

from src.query.app import create_app
from src.query.metrics_registry import (
    record_query_latency,
    record_rerank_latency,
    record_retrieval_latency,
    reset_registry,
    set_cache_hit_ratio,
    set_index_size,
)


def main():
    # Start fresh
    reset_registry()

    # Create app and test client
    app = create_app()
    client = TestClient(app)

    # Record some observations
    record_query_latency(0.042, "nl", False)
    record_query_latency(0.128, "symbol", True)
    record_retrieval_latency(0.015, "es_code")
    record_retrieval_latency(0.008, "qdrant_code")
    record_rerank_latency(0.035)
    set_cache_hit_ratio(0.65)
    set_index_size(12500, "my-repo", "code")
    set_index_size(3200, "my-repo", "doc")

    # Fetch /metrics
    response = client.get("/metrics")
    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers['content-type']}")
    print()

    # Print selected metrics (not the full output which is verbose)
    for line in response.text.splitlines():
        if line.startswith("#"):
            continue
        if any(
            keyword in line
            for keyword in [
                "query_latency_seconds_count",
                "query_latency_seconds_sum",
                "query_total",
                "retrieval_latency_seconds_count",
                "rerank_latency_seconds_count",
                "rerank_latency_seconds_sum",
                "cache_hit_ratio ",
                "index_size_chunks{",
            ]
        ):
            print(line)


if __name__ == "__main__":
    main()
