#!/usr/bin/env python3
"""Example: NFR-001 Query Latency Verification

Demonstrates how to use the LatencyReportAnalyzer to verify
that p95 query latency is under 1000ms from a Locust stats CSV.

Usage:
    # 1. Run a Locust load test (requires running query-api):
    #    locust -f src/loadtest/locustfile.py --host http://localhost:8000 \
    #        --users 100 --spawn-rate 10 --run-time 5m --headless \
    #        --csv=loadtest-results
    #
    # 2. Analyze the results:
    #    python examples/26-nfr-001-latency-check.py loadtest-results_stats.csv

    # Or use programmatic stats (no CSV needed):
    python examples/26-nfr-001-latency-check.py
"""

import sys

from src.loadtest.latency_report_analyzer import LatencyReportAnalyzer
from src.loadtest.query_generator import QueryGenerator
from src.loadtest.verification_result import VerificationResult


def demo_csv_analysis(csv_path: str) -> None:
    """Analyze a real Locust stats CSV file."""
    analyzer = LatencyReportAnalyzer()
    result = analyzer.analyze(csv_path, p95_threshold_ms=1000.0)
    print(result.summary())
    print(f"  Verdict: {'PASS ✓' if result.passed else 'FAIL ✗'}")


def demo_programmatic_analysis() -> None:
    """Analyze latency stats provided programmatically."""
    analyzer = LatencyReportAnalyzer()

    # Simulated stats from two endpoints
    stats = [
        {
            "p95_ms": 450.0,
            "p99_ms": 620.0,
            "median_ms": 180.0,
            "avg_ms": 210.0,
            "total_requests": 8000,
            "failure_count": 12,
        },
        {
            "p95_ms": 380.0,
            "p99_ms": 510.0,
            "median_ms": 150.0,
            "avg_ms": 175.0,
            "total_requests": 4000,
            "failure_count": 3,
        },
    ]

    result = analyzer.analyze_from_stats(stats, p95_threshold_ms=1000.0)
    print("Programmatic analysis:")
    print(f"  {result.summary()}")


def demo_query_generation() -> None:
    """Generate diverse query payloads for load testing."""
    gen = QueryGenerator()
    payloads = gen.generate_payloads(count=10, mix_ratio=0.7)

    print("\nSample query payloads (10 total, 70% NL / 30% symbol):")
    for i, p in enumerate(payloads, 1):
        print(f"  {i}. [{p['query_type']:6s}] {p['query']}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
        print(f"Analyzing Locust stats CSV: {csv_path}")
        demo_csv_analysis(csv_path)
    else:
        print("No CSV path provided — running programmatic demo.\n")
        demo_programmatic_analysis()
        demo_query_generation()
