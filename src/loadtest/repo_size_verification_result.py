"""Verification result dataclass for NFR-004 single repository size checks."""

from dataclasses import dataclass


@dataclass
class RepoSizeVerificationResult:
    """Result of a repository size verification check."""

    passed: bool
    total_repos: int
    repos_within_limit: int
    repos_completed: int
    max_observed_bytes: int
    completion_ratio: float
    max_size_bytes: int
    min_completion_ratio: float

    def summary(self) -> str:
        """Return a human-readable summary of the verification result."""
        verdict = "PASS" if self.passed else "FAIL"
        return (
            f"NFR-004: {verdict} — "
            f"repos={self.total_repos}, within_limit={self.repos_within_limit}, "
            f"completed={self.repos_completed} (ratio={self.completion_ratio:.4f}), "
            f"max_observed={self.max_observed_bytes} bytes, "
            f"threshold={self.max_size_bytes} bytes, "
            f"min_completion_ratio={self.min_completion_ratio:.2f}"
        )
