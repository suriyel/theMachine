"""Verification result dataclass for NFR-007 service availability checks."""

from dataclasses import dataclass


@dataclass
class AvailabilityVerificationResult:
    """Result of a service availability verification check."""

    passed: bool
    total_checks: int
    successful_checks: int
    uptime_ratio: float
    min_uptime_ratio: float
    min_total_checks: int

    def summary(self) -> str:
        """Return a human-readable summary of the verification result."""
        verdict = "PASS" if self.passed else "FAIL"
        return (
            f"NFR-007: {verdict} — "
            f"checks={self.total_checks}/{self.successful_checks} successful "
            f"(uptime={self.uptime_ratio:.6f}), "
            f"min_uptime={self.min_uptime_ratio}, "
            f"min_checks={self.min_total_checks}"
        )
