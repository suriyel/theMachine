"""Capacity report analyzer — parses JSON inventory and checks repository capacity thresholds."""

import json
import os

from src.loadtest.capacity_verification_result import CapacityVerificationResult


class CapacityReportAnalyzer:
    """Analyzes repository inventory reports to verify NFR-003 capacity requirements."""

    def analyze(
        self,
        json_path: str,
        min_repos: int = 100,
        max_repos: int = 1000,
        min_indexed_ratio: float = 0.8,
    ) -> CapacityVerificationResult:
        """Analyze a JSON inventory report against capacity thresholds.

        Args:
            json_path: Path to the JSON inventory report file.
            min_repos: Minimum acceptable repository count (default 100).
            max_repos: Maximum acceptable repository count (default 1000).
            min_indexed_ratio: Minimum acceptable indexed ratio (default 0.8).

        Returns:
            CapacityVerificationResult with pass/fail verdict and metrics.

        Raises:
            FileNotFoundError: If json_path does not exist.
            ValueError: If JSON is malformed, missing 'repositories' key, or list is empty.
        """
        if not os.path.exists(json_path):
            raise FileNotFoundError(json_path)

        with open(json_path) as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError("malformed JSON in report file") from e

        if "repositories" not in data:
            raise ValueError("missing 'repositories' key in JSON")

        repos = data["repositories"]
        if not repos:
            raise ValueError("repositories list must not be empty")

        total_repos = len(repos)
        indexed_repos = sum(1 for r in repos if r.get("status") == "indexed")
        indexed_ratio = indexed_repos / total_repos

        passed = (
            total_repos >= min_repos
            and total_repos <= max_repos
            and indexed_ratio >= min_indexed_ratio
        )

        return CapacityVerificationResult(
            passed=passed,
            total_repos=total_repos,
            indexed_repos=indexed_repos,
            indexed_ratio=indexed_ratio,
            min_repos=min_repos,
            max_repos=max_repos,
            min_indexed_ratio=min_indexed_ratio,
        )

    def analyze_from_stats(
        self,
        stats: dict,
        min_repos: int = 100,
        max_repos: int = 1000,
        min_indexed_ratio: float = 0.8,
    ) -> CapacityVerificationResult:
        """Analyze from a stats dictionary.

        Args:
            stats: Dict with keys: total_repos (int), indexed_repos (int).
            min_repos: Minimum acceptable repository count.
            max_repos: Maximum acceptable repository count.
            min_indexed_ratio: Minimum acceptable indexed ratio.

        Returns:
            CapacityVerificationResult with pass/fail verdict and metrics.

        Raises:
            ValueError: If stats dict is missing required keys or has negative values.
        """
        if "total_repos" not in stats or "indexed_repos" not in stats:
            raise ValueError("stats must contain 'total_repos' and 'indexed_repos'")

        total_repos = stats["total_repos"]
        indexed_repos = stats["indexed_repos"]

        if total_repos < 0 or indexed_repos < 0:
            raise ValueError("repo counts must be non-negative")

        indexed_ratio = indexed_repos / total_repos if total_repos > 0 else 0.0

        passed = (
            total_repos >= min_repos
            and total_repos <= max_repos
            and indexed_ratio >= min_indexed_ratio
        )

        return CapacityVerificationResult(
            passed=passed,
            total_repos=total_repos,
            indexed_repos=indexed_repos,
            indexed_ratio=indexed_ratio,
            min_repos=min_repos,
            max_repos=max_repos,
            min_indexed_ratio=min_indexed_ratio,
        )
