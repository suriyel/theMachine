"""Verification result dataclass for NFR-003 repository capacity checks."""

from dataclasses import dataclass


@dataclass
class CapacityVerificationResult:
    """Result of a repository capacity verification check."""

    passed: bool
    total_repos: int
    indexed_repos: int
    indexed_ratio: float
    min_repos: int
    max_repos: int
    min_indexed_ratio: float

    def summary(self) -> str:
        """Return a human-readable summary of the verification result."""
        verdict = "PASS" if self.passed else "FAIL"
        return (
            f"NFR-003: {verdict} — "
            f"repos={self.total_repos}/{self.indexed_repos} indexed "
            f"(ratio={self.indexed_ratio:.4f}), "
            f"range=[{self.min_repos},{self.max_repos}], "
            f"min_ratio={self.min_indexed_ratio:.2f}"
        )
