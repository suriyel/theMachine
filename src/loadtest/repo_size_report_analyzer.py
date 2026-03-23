"""Repo size report analyzer — parses JSON size reports and checks NFR-004 size thresholds."""

import json
import os

from src.loadtest.repo_size_verification_result import RepoSizeVerificationResult


class RepoSizeReportAnalyzer:
    """Analyzes repository size reports to verify NFR-004 single repository size requirements."""

    def analyze(
        self,
        json_path: str,
        max_size_bytes: int = 1_073_741_824,
        min_completion_ratio: float = 1.0,
    ) -> RepoSizeVerificationResult:
        """Analyze a JSON size report against size thresholds.

        Args:
            json_path: Path to the JSON size report file.
            max_size_bytes: Maximum acceptable repo size in bytes (default 1 GiB).
            min_completion_ratio: Minimum ratio of completed repos among within-limit repos.

        Returns:
            RepoSizeVerificationResult with pass/fail verdict and metrics.

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
        repos_within_limit = sum(1 for r in repos if r["size_bytes"] <= max_size_bytes)
        repos_completed = sum(
            1 for r in repos if r["size_bytes"] <= max_size_bytes and r["status"] == "completed"
        )
        max_observed_bytes = max(r["size_bytes"] for r in repos)

        if repos_within_limit == 0:
            completion_ratio = 0.0
        else:
            completion_ratio = repos_completed / repos_within_limit

        all_within_limit = repos_within_limit == total_repos
        passed = all_within_limit and completion_ratio >= min_completion_ratio

        return RepoSizeVerificationResult(
            passed=passed,
            total_repos=total_repos,
            repos_within_limit=repos_within_limit,
            repos_completed=repos_completed,
            max_observed_bytes=max_observed_bytes,
            completion_ratio=completion_ratio,
            max_size_bytes=max_size_bytes,
            min_completion_ratio=min_completion_ratio,
        )

    def analyze_from_stats(
        self,
        stats: dict,
        max_size_bytes: int = 1_073_741_824,
        min_completion_ratio: float = 1.0,
    ) -> RepoSizeVerificationResult:
        """Analyze from a stats dictionary.

        Args:
            stats: Dict with keys: total_repos, repos_within_limit, repos_completed, max_observed_bytes.
            max_size_bytes: Maximum acceptable repo size in bytes.
            min_completion_ratio: Minimum ratio of completed repos.

        Returns:
            RepoSizeVerificationResult with pass/fail verdict and metrics.

        Raises:
            ValueError: If stats dict is missing required keys or has negative values.
        """
        required = ["total_repos", "repos_within_limit", "repos_completed", "max_observed_bytes"]
        for key in required:
            if key not in stats:
                raise ValueError(
                    f"stats must contain 'total_repos', 'repos_within_limit', "
                    f"'repos_completed', and 'max_observed_bytes'"
                )

        total_repos = stats["total_repos"]
        repos_within_limit = stats["repos_within_limit"]
        repos_completed = stats["repos_completed"]
        max_observed_bytes = stats["max_observed_bytes"]

        if any(v < 0 for v in [total_repos, repos_within_limit, repos_completed, max_observed_bytes]):
            raise ValueError("all stat values must be non-negative")

        if repos_within_limit == 0:
            completion_ratio = 0.0
        else:
            completion_ratio = repos_completed / repos_within_limit

        all_within_limit = repos_within_limit == total_repos
        passed = all_within_limit and completion_ratio >= min_completion_ratio

        return RepoSizeVerificationResult(
            passed=passed,
            total_repos=total_repos,
            repos_within_limit=repos_within_limit,
            repos_completed=repos_completed,
            max_observed_bytes=max_observed_bytes,
            completion_ratio=completion_ratio,
            max_size_bytes=max_size_bytes,
            min_completion_ratio=min_completion_ratio,
        )
