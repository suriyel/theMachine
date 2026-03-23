#!/usr/bin/env python3
"""Example: NFR-004 Single Repository Size Verification

Demonstrates how to use the RepoSizeReportAnalyzer to verify
that repositories up to 1 GB are indexed successfully without OOM or timeout.

Usage:
    # 1. Export a repository size report JSON from your indexing pipeline:
    #    {"repositories": [{"name": "repo", "size_bytes": 500000000, "status": "completed"}, ...]}
    #
    # 2. Analyze the report:
    #    python examples/29-nfr-004-repo-size-check.py size_report.json

    # Or use programmatic stats (no JSON file needed):
    python examples/29-nfr-004-repo-size-check.py
"""

import json
import sys
import tempfile

from src.loadtest.repo_size_report_analyzer import RepoSizeReportAnalyzer

ONE_GB = 1_073_741_824


def demo_json_analysis(json_path: str) -> None:
    """Analyze a real repository size report JSON file."""
    analyzer = RepoSizeReportAnalyzer()
    result = analyzer.analyze(json_path, max_size_bytes=ONE_GB)
    print(result.summary())


def demo_programmatic_analysis() -> None:
    """Analyze size stats provided programmatically."""
    analyzer = RepoSizeReportAnalyzer()

    # Simulated stats: 5 repos, all within 1 GB, all completed
    result = analyzer.analyze_from_stats(
        {
            "total_repos": 5,
            "repos_within_limit": 5,
            "repos_completed": 5,
            "max_observed_bytes": 900_000_000,
        },
        max_size_bytes=ONE_GB,
    )
    print("Programmatic analysis:")
    print(f"  {result.summary()}")
    print(f"  Total repos: {result.total_repos}")
    print(f"  Within limit: {result.repos_within_limit}")
    print(f"  Completed: {result.repos_completed}")
    print(f"  Max observed: {result.max_observed_bytes:,} bytes")
    print(f"  Completion ratio: {result.completion_ratio:.2%}")


def demo_json_roundtrip() -> None:
    """Create a sample JSON size report and analyze it."""
    repos = [
        {"name": "small-service", "size_bytes": 50_000_000, "status": "completed"},
        {"name": "medium-app", "size_bytes": 500_000_000, "status": "completed"},
        {"name": "large-monorepo", "size_bytes": ONE_GB, "status": "completed"},
        {"name": "oversized-repo", "size_bytes": 1_500_000_000, "status": "completed"},
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"repositories": repos}, f)
        tmp_path = f.name

    analyzer = RepoSizeReportAnalyzer()
    result = analyzer.analyze(tmp_path, max_size_bytes=ONE_GB)
    print("JSON roundtrip demo (4 repos, 1 oversized):")
    print(f"  {result.summary()}")
    print(f"  Repos within limit: {result.repos_within_limit}/{result.total_repos}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        json_path = sys.argv[1]
        print(f"Analyzing repository size report: {json_path}")
        demo_json_analysis(json_path)
    else:
        print("No JSON path provided — running programmatic demos.\n")
        demo_programmatic_analysis()
        print()
        demo_json_roundtrip()
