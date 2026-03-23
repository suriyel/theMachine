#!/usr/bin/env python3
"""Example: NFR-006 Linear Scalability >= 70% Verification

Demonstrates how to use the ScalabilityReportAnalyzer to verify
that adding query nodes yields >= 70% of theoretical throughput increase.

Usage:
    # 1. Run Locust load tests against N-node and (N+1)-node deployments,
    #    producing two stats CSV files.
    #
    # 2. Analyze the CSV files:
    #    python examples/31-nfr-006-scalability-check.py baseline.csv scaled.csv 2 3

    # Or use programmatic stats (no CSV files needed):
    python examples/31-nfr-006-scalability-check.py
"""

import csv
import sys
import tempfile

from src.loadtest.scalability_report_analyzer import ScalabilityReportAnalyzer


LOCUST_CSV_HEADERS = [
    "Type", "Name", "Request Count", "Failure Count", "Median Response Time",
    "Average Response Time", "Min Response Time", "Max Response Time",
    "Average Content Size", "Requests/s", "Failures/s",
    "50%", "66%", "75%", "80%", "90%", "95%", "98%", "99%", "99.9%", "99.99%", "100%",
]


def _write_sample_csv(requests_per_sec: float) -> str:
    """Create a sample Locust stats CSV with given QPS."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
    writer = csv.DictWriter(f, fieldnames=LOCUST_CSV_HEADERS)
    writer.writeheader()
    writer.writerow({
        "Type": "", "Name": "Aggregated",
        "Request Count": "300000", "Failure Count": "0",
        "Median Response Time": "200", "Average Response Time": "250",
        "Min Response Time": "10", "Max Response Time": "5000",
        "Average Content Size": "1024",
        "Requests/s": str(requests_per_sec), "Failures/s": "0.0",
        "50%": "200", "66%": "300", "75%": "350", "80%": "400",
        "90%": "500", "95%": "600", "98%": "800", "99%": "900",
        "99.9%": "1500", "99.99%": "2000", "100%": "5000",
    })
    f.close()
    return f.name


def demo_csv_analysis(baseline_csv: str, scaled_csv: str,
                      baseline_nodes: int, scaled_nodes: int) -> None:
    """Analyze scalability from two Locust CSV files."""
    analyzer = ScalabilityReportAnalyzer()
    result = analyzer.analyze(
        baseline_csv, scaled_csv, baseline_nodes, scaled_nodes,
    )
    print(result.summary())


def demo_programmatic_analysis() -> None:
    """Analyze scalability stats provided programmatically."""
    analyzer = ScalabilityReportAnalyzer()

    # Scenario: 2-node baseline at 1000 QPS, 3-node scaled at 1400 QPS
    # Efficiency = (1400-1000) / (1000/2) = 400/500 = 80%
    result = analyzer.analyze_from_stats(
        baseline_qps=1000.0, scaled_qps=1400.0,
        baseline_nodes=2, scaled_nodes=3,
    )
    print("Programmatic analysis (2 -> 3 nodes, 80% efficiency):")
    print(f"  {result.summary()}")
    print(f"  Baseline: {result.baseline_qps:.1f} QPS ({result.baseline_nodes} nodes)")
    print(f"  Scaled: {result.scaled_qps:.1f} QPS ({result.scaled_nodes} nodes)")
    print(f"  Efficiency: {result.efficiency:.2%}")


def demo_csv_roundtrip() -> None:
    """Create sample CSVs and analyze scalability."""
    baseline_csv = _write_sample_csv(1000.0)
    scaled_csv = _write_sample_csv(1350.0)

    analyzer = ScalabilityReportAnalyzer()
    result = analyzer.analyze(baseline_csv, scaled_csv, baseline_nodes=2, scaled_nodes=3)
    print("CSV roundtrip demo (2 -> 3 nodes, 70% efficiency — at threshold):")
    print(f"  {result.summary()}")


if __name__ == "__main__":
    if len(sys.argv) == 5:
        baseline_csv = sys.argv[1]
        scaled_csv = sys.argv[2]
        baseline_nodes = int(sys.argv[3])
        scaled_nodes = int(sys.argv[4])
        print(f"Analyzing: {baseline_csv} vs {scaled_csv} ({baseline_nodes} -> {scaled_nodes} nodes)")
        demo_csv_analysis(baseline_csv, scaled_csv, baseline_nodes, scaled_nodes)
    else:
        print("No CSV paths provided — running programmatic demos.\n")
        demo_programmatic_analysis()
        print()
        demo_csv_roundtrip()
