#!/usr/bin/env python3
"""Example: NFR-002 Query Throughput Verification

Demonstrates how to use the ThroughputReportAnalyzer to verify
that sustained QPS >= 1000 with < 1% error rate from a Locust stats CSV.

Usage:
    # 1. Run a Locust load test (requires running query-api):
    #    locust -f src/loadtest/locustfile.py --host http://localhost:8000 \
    #        --users 500 --spawn-rate 50 --run-time 5m --headless \
    #        --csv=loadtest-results
    #
    # 2. Analyze the results:
    #    python examples/27-nfr-002-throughput-check.py loadtest-results_stats.csv

    # Or use programmatic stats (no CSV needed):
    python examples/27-nfr-002-throughput-check.py
"""

import sys

from src.loadtest.throughput_report_analyzer import ThroughputReportAnalyzer
from src.loadtest.throughput_verification_result import ThroughputVerificationResult


def demo_csv_analysis(csv_path: str) -> None:
    """Analyze a real Locust stats CSV file for throughput."""
    analyzer = ThroughputReportAnalyzer()
    result = analyzer.analyze(csv_path, qps_threshold=1000.0, error_rate_threshold=0.01)
    print(result.summary())


def demo_programmatic_analysis() -> None:
    """Analyze throughput stats provided programmatically."""
    analyzer = ThroughputReportAnalyzer()

    # Simulated stats from two query endpoints
    stats = [
        {"qps": 650.0, "total_requests": 195000, "failure_count": 80},
        {"qps": 480.0, "total_requests": 144000, "failure_count": 45},
    ]

    result = analyzer.analyze_from_stats(
        stats, qps_threshold=1000.0, error_rate_threshold=0.01
    )
    print("Programmatic analysis (aggregated from 2 endpoints):")
    print(f"  {result.summary()}")
    print(f"  Combined QPS: {result.qps:.1f}")
    print(f"  Total requests: {result.total_requests}")
    print(f"  Error rate: {result.error_rate:.4%}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
        print(f"Analyzing Locust stats CSV: {csv_path}")
        demo_csv_analysis(csv_path)
    else:
        print("No CSV path provided — running programmatic demo.\n")
        demo_programmatic_analysis()
