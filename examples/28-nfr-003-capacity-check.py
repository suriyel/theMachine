#!/usr/bin/env python3
"""Example: NFR-003 Repository Capacity Verification

Demonstrates how to use the CapacityReportAnalyzer to verify
that the system can index and serve queries across 100-1000 repositories.

Usage:
    # 1. Export a repository inventory JSON from your database:
    #    SELECT name, status FROM repositories → inventory.json
    #
    # 2. Analyze the inventory:
    #    python examples/28-nfr-003-capacity-check.py inventory.json

    # Or use programmatic stats (no JSON file needed):
    python examples/28-nfr-003-capacity-check.py
"""

import json
import sys
import tempfile

from src.loadtest.capacity_report_analyzer import CapacityReportAnalyzer


def demo_json_analysis(json_path: str) -> None:
    """Analyze a real repository inventory JSON file for capacity."""
    analyzer = CapacityReportAnalyzer()
    result = analyzer.analyze(json_path, min_repos=100, max_repos=1000, min_indexed_ratio=0.8)
    print(result.summary())


def demo_programmatic_analysis() -> None:
    """Analyze capacity stats provided programmatically."""
    analyzer = CapacityReportAnalyzer()

    # Simulated stats: 250 repos registered, 220 fully indexed
    result = analyzer.analyze_from_stats(
        {"total_repos": 250, "indexed_repos": 220},
        min_repos=100, max_repos=1000, min_indexed_ratio=0.8,
    )
    print("Programmatic analysis:")
    print(f"  {result.summary()}")
    print(f"  Total repos: {result.total_repos}")
    print(f"  Indexed repos: {result.indexed_repos}")
    print(f"  Indexed ratio: {result.indexed_ratio:.2%}")


def demo_json_roundtrip() -> None:
    """Create a sample JSON inventory and analyze it."""
    repos = [
        {"name": f"org/repo-{i}", "status": "indexed" if i < 180 else "pending"}
        for i in range(200)
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"repositories": repos}, f)
        tmp_path = f.name

    analyzer = CapacityReportAnalyzer()
    result = analyzer.analyze(tmp_path, min_repos=100, max_repos=1000, min_indexed_ratio=0.8)
    print("JSON roundtrip demo (200 repos, 180 indexed):")
    print(f"  {result.summary()}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        json_path = sys.argv[1]
        print(f"Analyzing repository inventory: {json_path}")
        demo_json_analysis(json_path)
    else:
        print("No JSON path provided — running programmatic demos.\n")
        demo_programmatic_analysis()
        print()
        demo_json_roundtrip()
