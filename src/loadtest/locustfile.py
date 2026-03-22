"""Locust load test for NFR-001: Query Latency p95 < 1s.

Usage:
    locust -f src/loadtest/locustfile.py --host http://localhost:8000 \
        --users 100 --spawn-rate 10 --run-time 5m --headless \
        --csv=loadtest-results

Then analyze:
    python -c "
    from src.loadtest.latency_report_analyzer import LatencyReportAnalyzer
    result = LatencyReportAnalyzer().analyze('loadtest-results_stats.csv')
    print(result.summary())
    "
"""

import random

from src.loadtest.query_generator import QueryGenerator

try:
    from locust import HttpUser, between, task
except ImportError:
    raise ImportError(
        "locust is required for load testing. "
        "Install with: pip install 'locust>=2.29'"
    )


class QueryLatencyLoadTest(HttpUser):
    """Locust user class that sends diverse query requests to the API.

    Simulates realistic AI agent traffic with a 70/30 NL/symbol mix ratio
    per ASM-006 (80%+ AI agent traffic uses NL queries).
    """

    wait_time = between(0.1, 0.5)

    def on_start(self) -> None:
        """Generate a pool of query payloads on user start."""
        generator = QueryGenerator()
        self._payloads = generator.generate_payloads(count=200, mix_ratio=0.7)
        self._index = 0

    @task
    def query_api(self) -> None:
        """Send a query request to POST /api/v1/query."""
        payload = self._payloads[self._index % len(self._payloads)]
        self._index += 1

        request_body = {
            "query": payload["query"],
        }
        if payload.get("repo_id") is not None:
            request_body["repo_id"] = payload["repo_id"]

        self.client.post(
            "/api/v1/query",
            json=request_body,
            headers={"X-API-Key": "loadtest-key"},
        )
