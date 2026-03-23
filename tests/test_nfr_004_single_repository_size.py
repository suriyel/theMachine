"""Tests for NFR-004: Single Repository Size verification components.

Components: RepoSizeReportAnalyzer, RepoSizeVerificationResult.

# [no integration test] — pure function, no external I/O
# All components operate on in-memory data or local JSON files via tmp_path.
# Security: N/A — internal utility with no user-facing input
"""

import json

import pytest

from src.loadtest.repo_size_verification_result import RepoSizeVerificationResult
from src.loadtest.repo_size_report_analyzer import RepoSizeReportAnalyzer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ONE_GB = 1_073_741_824  # 1 GiB in bytes


def _repo(size_bytes: int, status: str = "completed", name: str | None = None) -> dict:
    """Create a single repo dict with size_bytes and status."""
    return {"name": name or f"repo-{size_bytes}", "size_bytes": size_bytes, "status": status}


def _write_json(tmp_path, repos: list[dict], filename: str = "size_report.json") -> str:
    """Write a JSON size report and return its path."""
    path = tmp_path / filename
    data = {"repositories": repos}
    path.write_text(json.dumps(data))
    return str(path)


# ---------------------------------------------------------------------------
# [unit] Happy Path — analyze (JSON file)
# ---------------------------------------------------------------------------


class TestAnalyzeHappyPath:
    """Tests A-E from Test Inventory: happy path pass/fail scenarios."""

    # Test A: 3 repos (500MB, 800MB, 1GB exact), all completed -> passed=True
    def test_passes_with_three_repos_up_to_1gb(self, tmp_path):
        repos = [
            _repo(500_000_000, "completed"),
            _repo(800_000_000, "completed"),
            _repo(ONE_GB, "completed"),
        ]
        path = _write_json(tmp_path, repos)
        analyzer = RepoSizeReportAnalyzer()
        result = analyzer.analyze(path, max_size_bytes=ONE_GB)

        assert result.passed is True
        assert result.total_repos == 3
        assert result.repos_within_limit == 3
        assert result.repos_completed == 3
        assert result.max_observed_bytes == ONE_GB

    # Test B: 5 repos (100MB-900MB), all completed -> passed=True
    def test_passes_with_five_repos_well_under_limit(self, tmp_path):
        repos = [
            _repo(100_000_000, "completed"),
            _repo(300_000_000, "completed"),
            _repo(500_000_000, "completed"),
            _repo(700_000_000, "completed"),
            _repo(900_000_000, "completed"),
        ]
        path = _write_json(tmp_path, repos)
        analyzer = RepoSizeReportAnalyzer()
        result = analyzer.analyze(path, max_size_bytes=ONE_GB)

        assert result.passed is True
        assert result.total_repos == 5
        assert result.repos_within_limit == 5
        assert result.repos_completed == 5
        assert result.max_observed_bytes == 900_000_000

    # Test C: 3 repos, one at 1.5GB (over limit) -> passed=False
    def test_fails_with_oversized_repo(self, tmp_path):
        repos = [
            _repo(500_000_000, "completed"),
            _repo(1_500_000_000, "completed"),  # over 1GB
            _repo(500_000_000, "completed"),
        ]
        path = _write_json(tmp_path, repos)
        analyzer = RepoSizeReportAnalyzer()
        result = analyzer.analyze(path, max_size_bytes=ONE_GB)

        assert result.passed is False
        assert result.total_repos == 3
        assert result.repos_within_limit == 2
        assert result.max_observed_bytes == 1_500_000_000

    # Test D: 3 repos within limit, one status="oom" -> passed=False
    def test_fails_with_oom_status(self, tmp_path):
        repos = [
            _repo(500_000_000, "completed"),
            _repo(800_000_000, "oom"),
            _repo(600_000_000, "completed"),
        ]
        path = _write_json(tmp_path, repos)
        analyzer = RepoSizeReportAnalyzer()
        result = analyzer.analyze(path, max_size_bytes=ONE_GB)

        assert result.passed is False
        assert result.repos_within_limit == 3
        assert result.repos_completed == 2
        assert abs(result.completion_ratio - 2 / 3) < 1e-9

    # Test E: 3 repos within limit, one status="timeout" -> passed=False
    def test_fails_with_timeout_status(self, tmp_path):
        repos = [
            _repo(500_000_000, "completed"),
            _repo(800_000_000, "timeout"),
            _repo(600_000_000, "completed"),
        ]
        path = _write_json(tmp_path, repos)
        analyzer = RepoSizeReportAnalyzer()
        result = analyzer.analyze(path, max_size_bytes=ONE_GB)

        assert result.passed is False
        assert result.repos_completed == 2
        assert abs(result.completion_ratio - 2 / 3) < 1e-9


# ---------------------------------------------------------------------------
# [unit] Boundary Tests
# ---------------------------------------------------------------------------


class TestAnalyzeBoundary:
    """Tests F-J from Test Inventory: boundary conditions."""

    # Test F: 1 repo exactly at 1GB, completed -> passed=True (uses <=)
    def test_passes_at_exact_size_limit(self, tmp_path):
        repos = [_repo(ONE_GB, "completed")]
        path = _write_json(tmp_path, repos)
        analyzer = RepoSizeReportAnalyzer()
        result = analyzer.analyze(path, max_size_bytes=ONE_GB)

        assert result.passed is True
        assert result.repos_within_limit == 1
        assert result.max_observed_bytes == ONE_GB

    # Test G: 1 repo 1 byte over limit -> passed=False
    def test_fails_one_byte_over_limit(self, tmp_path):
        repos = [_repo(ONE_GB + 1, "completed")]
        path = _write_json(tmp_path, repos)
        analyzer = RepoSizeReportAnalyzer()
        result = analyzer.analyze(path, max_size_bytes=ONE_GB)

        assert result.passed is False
        assert result.repos_within_limit == 0
        assert result.total_repos == 1

    # Test H: stats with repos_within_limit=0, total_repos=1 -> no ZeroDivisionError
    def test_zero_repos_within_limit_no_division_error(self):
        analyzer = RepoSizeReportAnalyzer()
        result = analyzer.analyze_from_stats(
            {"total_repos": 1, "repos_within_limit": 0, "repos_completed": 0, "max_observed_bytes": 2_000_000_000},
            max_size_bytes=ONE_GB,
        )

        assert result.passed is False
        assert result.completion_ratio == 0.0

    # Test H2: stats with repos_within_limit>0, exercises else branch in analyze_from_stats
    def test_stats_with_repos_within_limit_positive(self):
        analyzer = RepoSizeReportAnalyzer()
        result = analyzer.analyze_from_stats(
            {"total_repos": 3, "repos_within_limit": 3, "repos_completed": 3, "max_observed_bytes": ONE_GB},
            max_size_bytes=ONE_GB,
        )

        assert result.passed is True
        assert result.completion_ratio == 1.0
        assert result.repos_within_limit == 3
        assert result.repos_completed == 3

    # Test I: 2 repos within limit, min_completion_ratio=0.5, 1 completed -> passed=True (uses >=)
    def test_passes_at_exact_completion_ratio_threshold(self, tmp_path):
        repos = [
            _repo(500_000_000, "completed"),
            _repo(600_000_000, "error"),
        ]
        path = _write_json(tmp_path, repos)
        analyzer = RepoSizeReportAnalyzer()
        result = analyzer.analyze(path, max_size_bytes=ONE_GB, min_completion_ratio=0.5)

        assert result.passed is True
        assert result.repos_completed == 1
        assert abs(result.completion_ratio - 0.5) < 1e-9

    # Test J: 2 repos within limit, min_completion_ratio=0.5, 0 completed -> passed=False
    def test_fails_below_completion_ratio_threshold(self, tmp_path):
        repos = [
            _repo(500_000_000, "oom"),
            _repo(600_000_000, "timeout"),
        ]
        path = _write_json(tmp_path, repos)
        analyzer = RepoSizeReportAnalyzer()
        result = analyzer.analyze(path, max_size_bytes=ONE_GB, min_completion_ratio=0.5)

        assert result.passed is False
        assert result.repos_completed == 0
        assert result.completion_ratio == 0.0


# ---------------------------------------------------------------------------
# [unit] Error Handling Tests
# ---------------------------------------------------------------------------


class TestAnalyzeErrors:
    """Tests K-P from Test Inventory: error handling."""

    # Test K: nonexistent file -> FileNotFoundError
    def test_file_not_found(self):
        analyzer = RepoSizeReportAnalyzer()
        with pytest.raises(FileNotFoundError):
            analyzer.analyze("/nonexistent/report.json")

    # Test L: invalid JSON -> ValueError
    def test_malformed_json(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{not valid json!!!")
        analyzer = RepoSizeReportAnalyzer()
        with pytest.raises(ValueError, match="malformed JSON"):
            analyzer.analyze(str(path))

    # Test M: missing 'repositories' key -> ValueError
    def test_missing_repositories_key(self, tmp_path):
        path = tmp_path / "no_repos.json"
        path.write_text(json.dumps({"other": []}))
        analyzer = RepoSizeReportAnalyzer()
        with pytest.raises(ValueError, match="repositories"):
            analyzer.analyze(str(path))

    # Test N: empty repos list -> ValueError
    def test_empty_repositories_list(self, tmp_path):
        path = tmp_path / "empty.json"
        path.write_text(json.dumps({"repositories": []}))
        analyzer = RepoSizeReportAnalyzer()
        with pytest.raises(ValueError, match="empty"):
            analyzer.analyze(str(path))

    # Test O: stats missing keys -> ValueError
    def test_stats_missing_keys(self):
        analyzer = RepoSizeReportAnalyzer()
        with pytest.raises(ValueError, match="total_repos"):
            analyzer.analyze_from_stats({"repos_completed": 10})

    # Test P: stats with negative value -> ValueError
    def test_stats_negative_value(self):
        analyzer = RepoSizeReportAnalyzer()
        with pytest.raises(ValueError, match="non-negative"):
            analyzer.analyze_from_stats(
                {"total_repos": -1, "repos_within_limit": 0, "repos_completed": 0, "max_observed_bytes": 0}
            )


# ---------------------------------------------------------------------------
# [unit] Summary Tests
# ---------------------------------------------------------------------------


class TestVerificationResultSummary:
    """Tests Q-R from Test Inventory: summary() output."""

    # Test Q: passed=True -> summary contains "NFR-004", "PASS", repo counts, max observed
    def test_summary_pass_format(self):
        result = RepoSizeVerificationResult(
            passed=True,
            total_repos=3,
            repos_within_limit=3,
            repos_completed=3,
            max_observed_bytes=ONE_GB,
            completion_ratio=1.0,
            max_size_bytes=ONE_GB,
            min_completion_ratio=1.0,
        )
        s = result.summary()
        assert "NFR-004" in s
        assert "PASS" in s
        assert "3" in s
        assert str(ONE_GB) in s

    # Test R: passed=False -> summary contains "FAIL", thresholds
    def test_summary_fail_format(self):
        result = RepoSizeVerificationResult(
            passed=False,
            total_repos=3,
            repos_within_limit=2,
            repos_completed=2,
            max_observed_bytes=1_500_000_000,
            completion_ratio=1.0,
            max_size_bytes=ONE_GB,
            min_completion_ratio=1.0,
        )
        s = result.summary()
        assert "NFR-004" in s
        assert "FAIL" in s
        assert str(ONE_GB) in s


# ---------------------------------------------------------------------------
# [integration] Real Test — JSON file I/O roundtrip
# ---------------------------------------------------------------------------


@pytest.mark.real
class TestRealRepoSizeReportFeature29:
    """Real test: exercises actual JSON file I/O for feature #29."""

    def test_real_json_roundtrip_analyze_feature_29(self, tmp_path):
        """Real test: write a JSON size report, parse it, verify size metrics extracted."""
        repos = [
            _repo(500_000_000, "completed", "small-repo"),
            _repo(ONE_GB, "completed", "large-repo"),
            _repo(800_000_000, "completed", "medium-repo"),
        ]
        path = _write_json(tmp_path, repos)
        analyzer = RepoSizeReportAnalyzer()
        result = analyzer.analyze(path, max_size_bytes=ONE_GB)

        assert result.passed is True
        assert result.total_repos == 3
        assert result.repos_within_limit == 3
        assert result.repos_completed == 3
        assert result.max_observed_bytes == ONE_GB
        assert result.max_size_bytes == ONE_GB
        assert result.min_completion_ratio == 1.0
        assert result.completion_ratio == 1.0
