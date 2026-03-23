#!/usr/bin/env python3
"""Example: NFR-008 Single-Node Failure Tolerance Verification

Demonstrates how to use the FailureToleranceReportAnalyzer to verify
that the query service continues serving requests without failures when
any single node is killed during a load test.

Usage:
    # 1. Run a load test against a multi-node query cluster,
    #    capture total/failed requests and node counts into a JSON report:
    #    {
    #      "total_requests": 1000,
    #      "failed_requests": 0,
    #      "nodes_killed": 1,
    #      "nodes_initial": 3
    #    }
    #
    # 2. Analyze the report:
    #    python examples/32-nfr-007-failure-tolerance.py report.json

    # Or use programmatic stats (no JSON file needed):
    python examples/32-nfr-007-failure-tolerance.py
"""

import json
import sys
import tempfile
import os

from src.loadtest.failure_tolerance_report_analyzer import FailureToleranceReportAnalyzer


def demo_passing_case() -> None:
    """Demonstrate a passing failure-tolerance verification (1 node killed, 0 failures)."""
    analyzer = FailureToleranceReportAnalyzer()
    result = analyzer.analyze_from_stats({
        "total_requests": 500,
        "failed_requests": 0,
        "nodes_killed": 1,
        "nodes_initial": 3,
    })
    print("Passing case (1/3 nodes killed, 0 failures):")
    print(f"  {result.summary()}")
    print(f"  nodes_killed: {result.nodes_killed}, nodes_initial: {result.nodes_initial}")
    print(f"  failed: {result.failed_requests}/{result.total_requests} requests")


def demo_failing_case_no_node_killed() -> None:
    """Demonstrate a failing case — no node was actually killed."""
    analyzer = FailureToleranceReportAnalyzer()
    result = analyzer.analyze_from_stats({
        "total_requests": 500,
        "failed_requests": 0,
        "nodes_killed": 0,
        "nodes_initial": 3,
    })
    print("Failing case (nodes_killed=0 — test did not kill any node):")
    print(f"  {result.summary()}")


def demo_failing_case_requests_failed() -> None:
    """Demonstrate a failing case — requests failed during the node kill."""
    analyzer = FailureToleranceReportAnalyzer()
    result = analyzer.analyze_from_stats({
        "total_requests": 500,
        "failed_requests": 12,
        "nodes_killed": 1,
        "nodes_initial": 3,
    })
    print("Failing case (12 requests failed during node kill):")
    print(f"  {result.summary()}")


def demo_json_file_analysis(json_path: str) -> None:
    """Analyze a failure-tolerance JSON report from disk."""
    analyzer = FailureToleranceReportAnalyzer()
    result = analyzer.analyze(json_path)
    print(f"JSON file analysis ({json_path}):")
    print(f"  {result.summary()}")


def demo_json_roundtrip() -> None:
    """Create a sample JSON report and analyze it."""
    data = {
        "total_requests": 1000,
        "failed_requests": 0,
        "nodes_killed": 1,
        "nodes_initial": 3,
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        tmp_path = f.name
    try:
        analyzer = FailureToleranceReportAnalyzer()
        result = analyzer.analyze(tmp_path)
        print("JSON roundtrip demo (1/3 nodes killed, 0 failures):")
        print(f"  {result.summary()}")
    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    if len(sys.argv) == 2:
        demo_json_file_analysis(sys.argv[1])
    else:
        print("No JSON path provided — running programmatic demos.\n")
        demo_passing_case()
        print()
        demo_failing_case_no_node_killed()
        print()
        demo_failing_case_requests_failed()
        print()
        demo_json_roundtrip()
