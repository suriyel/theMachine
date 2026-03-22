"""Verification result dataclass for NFR latency checks."""

from dataclasses import dataclass


@dataclass
class VerificationResult:
    """Result of a latency threshold verification check."""

    passed: bool
    p95_ms: float
    p99_ms: float
    median_ms: float
    avg_ms: float
    total_requests: int
    failure_rate: float
    threshold_ms: float

    def summary(self) -> str:
        """Return a human-readable summary of the verification result."""
        verdict = "PASS" if self.passed else "FAIL"
        return (
            f"NFR-001: {verdict} — "
            f"p95={self.p95_ms:.0f}ms (threshold={self.threshold_ms:.0f}ms), "
            f"p99={self.p99_ms:.0f}ms, median={self.median_ms:.0f}ms, "
            f"requests={self.total_requests}, "
            f"failure_rate={self.failure_rate:.4f}"
        )
