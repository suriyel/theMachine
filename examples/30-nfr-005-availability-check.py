#!/usr/bin/env python3
"""Example: NFR-005 Service Availability 99.9% Verification

Demonstrates how to use the AvailabilityReportAnalyzer to verify
that the query service achieves 99.9% uptime from health check monitoring data.

Usage:
    # 1. Export an uptime report JSON from your monitoring system:
    #    {"checks": [{"status": "success"}, {"status": "failure"}, ...]}
    #
    # 2. Analyze the report:
    #    python examples/30-nfr-005-availability-check.py uptime_report.json

    # Or use programmatic stats (no JSON file needed):
    python examples/30-nfr-005-availability-check.py
"""

import json
import sys
import tempfile

from src.loadtest.availability_report_analyzer import AvailabilityReportAnalyzer


def demo_json_analysis(json_path: str) -> None:
    """Analyze a real uptime report JSON file."""
    analyzer = AvailabilityReportAnalyzer()
    result = analyzer.analyze(json_path, min_uptime_ratio=0.999)
    print(result.summary())


def demo_programmatic_analysis() -> None:
    """Analyze availability stats provided programmatically."""
    analyzer = AvailabilityReportAnalyzer()

    # Simulated 30-day monitoring at 1-minute intervals: 43200 checks, 43157 successful
    result = analyzer.analyze_from_stats(
        {
            "total_checks": 43200,
            "successful_checks": 43157,
        },
        min_uptime_ratio=0.999,
        min_total_checks=43200,
    )
    print("Programmatic analysis (30-day window, 1-min intervals):")
    print(f"  {result.summary()}")
    print(f"  Total checks: {result.total_checks}")
    print(f"  Successful: {result.successful_checks}")
    print(f"  Uptime ratio: {result.uptime_ratio:.6f}")
    print(f"  Threshold: {result.min_uptime_ratio}")


def demo_json_roundtrip() -> None:
    """Create a sample JSON uptime report and analyze it."""
    checks = [{"status": "success"} for _ in range(999)]
    checks.append({"status": "failure"})  # 1 failure in 1000 checks

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"checks": checks}, f)
        tmp_path = f.name

    analyzer = AvailabilityReportAnalyzer()
    result = analyzer.analyze(tmp_path, min_uptime_ratio=0.999)
    print("JSON roundtrip demo (1000 checks, 1 failure):")
    print(f"  {result.summary()}")
    print(f"  Uptime: {result.uptime_ratio:.4f} (threshold: {result.min_uptime_ratio})")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        json_path = sys.argv[1]
        print(f"Analyzing uptime report: {json_path}")
        demo_json_analysis(json_path)
    else:
        print("No JSON path provided — running programmatic demos.\n")
        demo_programmatic_analysis()
        print()
        demo_json_roundtrip()
