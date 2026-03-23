"""Availability report analyzer — parses JSON uptime reports and checks availability thresholds."""

import json
import os

from src.loadtest.availability_verification_result import AvailabilityVerificationResult


class AvailabilityReportAnalyzer:
    """Analyzes uptime monitoring reports to verify NFR-007 availability requirements."""

    def analyze(
        self,
        json_path: str,
        min_uptime_ratio: float = 0.999,
        min_total_checks: int = 1,
    ) -> AvailabilityVerificationResult:
        """Analyze a JSON uptime report against availability thresholds.

        Args:
            json_path: Path to the JSON uptime report file.
            min_uptime_ratio: Minimum acceptable uptime ratio (default 0.999).
            min_total_checks: Minimum acceptable total check count (default 1).

        Returns:
            AvailabilityVerificationResult with pass/fail verdict and metrics.

        Raises:
            FileNotFoundError: If json_path does not exist.
            ValueError: If JSON is malformed, missing 'checks' key, or checks list is empty.
        """
        if not os.path.exists(json_path):
            raise FileNotFoundError(json_path)

        with open(json_path) as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError("malformed JSON in report file") from e

        if "checks" not in data:
            raise ValueError("missing 'checks' key in JSON")

        checks = data["checks"]
        if not checks:
            raise ValueError("checks list must not be empty")

        total_checks = len(checks)
        successful_checks = sum(1 for c in checks if c.get("status") == "success")
        uptime_ratio = successful_checks / total_checks

        passed = (
            total_checks >= min_total_checks
            and uptime_ratio >= min_uptime_ratio
        )

        return AvailabilityVerificationResult(
            passed=passed,
            total_checks=total_checks,
            successful_checks=successful_checks,
            uptime_ratio=uptime_ratio,
            min_uptime_ratio=min_uptime_ratio,
            min_total_checks=min_total_checks,
        )

    def analyze_from_stats(
        self,
        stats: dict,
        min_uptime_ratio: float = 0.999,
        min_total_checks: int = 1,
    ) -> AvailabilityVerificationResult:
        """Analyze from a stats dictionary.

        Args:
            stats: Dict with keys: total_checks (int), successful_checks (int).
            min_uptime_ratio: Minimum acceptable uptime ratio.
            min_total_checks: Minimum acceptable total check count.

        Returns:
            AvailabilityVerificationResult with pass/fail verdict and metrics.

        Raises:
            ValueError: If stats dict is missing required keys or has negative values.
        """
        if "total_checks" not in stats or "successful_checks" not in stats:
            raise ValueError("stats must contain 'total_checks' and 'successful_checks'")

        total_checks = stats["total_checks"]
        successful_checks = stats["successful_checks"]

        if total_checks < 0 or successful_checks < 0:
            raise ValueError("check counts must be non-negative")

        uptime_ratio = successful_checks / total_checks if total_checks > 0 else 0.0

        passed = (
            total_checks >= min_total_checks
            and uptime_ratio >= min_uptime_ratio
        )

        return AvailabilityVerificationResult(
            passed=passed,
            total_checks=total_checks,
            successful_checks=successful_checks,
            uptime_ratio=uptime_ratio,
            min_uptime_ratio=min_uptime_ratio,
            min_total_checks=min_total_checks,
        )
