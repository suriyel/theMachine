"""Tests for NFR-003: Repository Capacity verification components.

Components: CapacityReportAnalyzer, CapacityVerificationResult.

# [no integration test] — pure function, no external I/O
# All components operate on in-memory data or local JSON files via tmp_path.
# Security: N/A — internal utility with no user-facing input
"""

import json

import pytest

from src.loadtest.capacity_verification_result import CapacityVerificationResult
from src.loadtest.capacity_report_analyzer import CapacityReportAnalyzer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _repo_list(total: int, indexed_count: int) -> list[dict]:
    """Generate a list of repo dicts with the first `indexed_count` having status='indexed'."""
    repos = []
    for i in range(total):
        status = "indexed" if i < indexed_count else "pending"
        repos.append({"name": f"repo-{i}", "status": status})
    return repos


def _write_json(tmp_path, repos: list[dict], filename: str = "inventory.json") -> str:
    """Write a JSON inventory report and return its path."""
    path = tmp_path / filename
    data = {"repositories": repos}
    path.write_text(json.dumps(data))
    return str(path)


# ---------------------------------------------------------------------------
# [unit] Happy Path — analyze (JSON file)
# ---------------------------------------------------------------------------


class TestAnalyzeHappyPath:
    """Tests A-E from Test Inventory: happy path pass/fail scenarios."""

    # Test A: 150 repos, 140 indexed -> passed=True
    def test_passes_with_150_repos_140_indexed(self, tmp_path):
        repos = _repo_list(150, 140)
        path = _write_json(tmp_path, repos)
        analyzer = CapacityReportAnalyzer()
        result = analyzer.analyze(path, min_repos=100, max_repos=1000, min_indexed_ratio=0.8)

        assert result.passed is True
        assert result.total_repos == 150
        assert result.indexed_repos == 140
        assert abs(result.indexed_ratio - 140 / 150) < 1e-9

    # Test B: 1000 repos, 950 indexed -> passed=True (upper bound)
    def test_passes_at_max_boundary_1000_repos(self, tmp_path):
        repos = _repo_list(1000, 950)
        path = _write_json(tmp_path, repos)
        analyzer = CapacityReportAnalyzer()
        result = analyzer.analyze(path, min_repos=100, max_repos=1000, min_indexed_ratio=0.8)

        assert result.passed is True
        assert result.total_repos == 1000
        assert result.indexed_repos == 950
        assert abs(result.indexed_ratio - 0.95) < 1e-9

    # Test C: 50 repos, all indexed -> passed=False (below min)
    def test_fails_below_min_repos(self, tmp_path):
        repos = _repo_list(50, 50)
        path = _write_json(tmp_path, repos)
        analyzer = CapacityReportAnalyzer()
        result = analyzer.analyze(path, min_repos=100, max_repos=1000, min_indexed_ratio=0.8)

        assert result.passed is False
        assert result.total_repos == 50
        assert result.indexed_repos == 50
        assert abs(result.indexed_ratio - 1.0) < 1e-9

    # Test D: 200 repos, 100 indexed (ratio=0.5) -> passed=False
    def test_fails_low_indexed_ratio(self, tmp_path):
        repos = _repo_list(200, 100)
        path = _write_json(tmp_path, repos)
        analyzer = CapacityReportAnalyzer()
        result = analyzer.analyze(path, min_repos=100, max_repos=1000, min_indexed_ratio=0.8)

        assert result.passed is False
        assert result.total_repos == 200
        assert result.indexed_repos == 100
        assert abs(result.indexed_ratio - 0.5) < 1e-9

    # Test E: 1500 repos, all indexed -> passed=False (above max)
    def test_fails_above_max_repos(self, tmp_path):
        repos = _repo_list(1500, 1500)
        path = _write_json(tmp_path, repos)
        analyzer = CapacityReportAnalyzer()
        result = analyzer.analyze(path, min_repos=100, max_repos=1000, min_indexed_ratio=0.8)

        assert result.passed is False
        assert result.total_repos == 1500
        assert result.indexed_repos == 1500
        assert abs(result.indexed_ratio - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# [unit] Boundary Tests
# ---------------------------------------------------------------------------


class TestAnalyzeBoundary:
    """Tests F-I from Test Inventory: boundary conditions."""

    # Test F: 100 repos, 80 indexed (ratio=0.8 exactly) -> passed=True
    def test_passes_at_exact_min_repos_and_exact_ratio(self, tmp_path):
        repos = _repo_list(100, 80)
        path = _write_json(tmp_path, repos)
        analyzer = CapacityReportAnalyzer()
        result = analyzer.analyze(path, min_repos=100, max_repos=1000, min_indexed_ratio=0.8)

        assert result.passed is True
        assert result.total_repos == 100
        assert result.indexed_repos == 80
        assert abs(result.indexed_ratio - 0.8) < 1e-9

    # Test G: 100 repos, 79 indexed (ratio=0.79) -> passed=False
    def test_fails_just_below_ratio_threshold(self, tmp_path):
        repos = _repo_list(100, 79)
        path = _write_json(tmp_path, repos)
        analyzer = CapacityReportAnalyzer()
        result = analyzer.analyze(path, min_repos=100, max_repos=1000, min_indexed_ratio=0.8)

        assert result.passed is False
        assert result.total_repos == 100
        assert result.indexed_repos == 79
        assert abs(result.indexed_ratio - 0.79) < 1e-9

    # Test H: 1000 repos, 800 indexed, max_repos=1000 -> passed=True
    def test_passes_at_exact_max_repos(self, tmp_path):
        repos = _repo_list(1000, 800)
        path = _write_json(tmp_path, repos)
        analyzer = CapacityReportAnalyzer()
        result = analyzer.analyze(path, min_repos=100, max_repos=1000, min_indexed_ratio=0.8)

        assert result.passed is True
        assert result.total_repos == 1000
        assert result.indexed_repos == 800
        assert abs(result.indexed_ratio - 0.8) < 1e-9

    # Test I: total_repos=0 via analyze_from_stats -> passed=False, no ZeroDivisionError
    def test_zero_total_repos_no_division_error(self):
        analyzer = CapacityReportAnalyzer()
        result = analyzer.analyze_from_stats(
            {"total_repos": 0, "indexed_repos": 0},
            min_repos=100, max_repos=1000, min_indexed_ratio=0.8,
        )

        assert result.passed is False
        assert result.total_repos == 0
        assert result.indexed_repos == 0
        assert result.indexed_ratio == 0.0


# ---------------------------------------------------------------------------
# [unit] Error Handling Tests
# ---------------------------------------------------------------------------


class TestAnalyzeErrors:
    """Tests J-O from Test Inventory: error handling."""

    # Test J: nonexistent file -> FileNotFoundError
    def test_file_not_found(self):
        analyzer = CapacityReportAnalyzer()
        with pytest.raises(FileNotFoundError):
            analyzer.analyze("/nonexistent/report.json")

    # Test K: invalid JSON -> ValueError
    def test_malformed_json(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{not valid json!!!")
        analyzer = CapacityReportAnalyzer()
        with pytest.raises(ValueError, match="malformed JSON"):
            analyzer.analyze(str(path))

    # Test L: missing 'repositories' key -> ValueError
    def test_missing_repositories_key(self, tmp_path):
        path = tmp_path / "no_repos.json"
        path.write_text(json.dumps({"other": []}))
        analyzer = CapacityReportAnalyzer()
        with pytest.raises(ValueError, match="repositories"):
            analyzer.analyze(str(path))

    # Test M: empty repos list -> ValueError
    def test_empty_repositories_list(self, tmp_path):
        path = tmp_path / "empty.json"
        path.write_text(json.dumps({"repositories": []}))
        analyzer = CapacityReportAnalyzer()
        with pytest.raises(ValueError, match="empty"):
            analyzer.analyze(str(path))

    # Test N: stats missing keys -> ValueError
    def test_stats_missing_keys(self):
        analyzer = CapacityReportAnalyzer()
        with pytest.raises(ValueError, match="total_repos"):
            analyzer.analyze_from_stats({"indexed_repos": 10})

    # Test O: stats with negative total_repos -> ValueError
    def test_stats_negative_count(self):
        analyzer = CapacityReportAnalyzer()
        with pytest.raises(ValueError, match="non-negative"):
            analyzer.analyze_from_stats({"total_repos": -1, "indexed_repos": 0})


# ---------------------------------------------------------------------------
# [unit] Summary Tests
# ---------------------------------------------------------------------------


class TestVerificationResultSummary:
    """Tests P-Q from Test Inventory: summary() output."""

    # Test P: passed=True -> summary contains "NFR-003", "PASS", repo counts
    def test_summary_pass_format(self):
        result = CapacityVerificationResult(
            passed=True,
            total_repos=150,
            indexed_repos=140,
            indexed_ratio=140 / 150,
            min_repos=100,
            max_repos=1000,
            min_indexed_ratio=0.8,
        )
        s = result.summary()
        assert "NFR-003" in s
        assert "PASS" in s
        assert "150" in s
        assert "140" in s

    # Test Q: passed=False -> summary contains "FAIL", thresholds
    def test_summary_fail_format(self):
        result = CapacityVerificationResult(
            passed=False,
            total_repos=50,
            indexed_repos=50,
            indexed_ratio=1.0,
            min_repos=100,
            max_repos=1000,
            min_indexed_ratio=0.8,
        )
        s = result.summary()
        assert "NFR-003" in s
        assert "FAIL" in s
        assert "100" in s  # min_repos threshold
        assert "1000" in s  # max_repos threshold


# ---------------------------------------------------------------------------
# [integration] Real Test — JSON file I/O roundtrip
# ---------------------------------------------------------------------------


@pytest.mark.real
class TestRealCapacityReportFeature28:
    """Real test: exercises actual JSON file I/O for feature #28."""

    def test_real_json_roundtrip_analyze_feature_28(self, tmp_path):
        """Real test: write a JSON inventory, parse it, verify capacity metrics extracted."""
        repos = _repo_list(200, 180)
        path = _write_json(tmp_path, repos)
        analyzer = CapacityReportAnalyzer()
        result = analyzer.analyze(path, min_repos=100, max_repos=1000, min_indexed_ratio=0.8)

        assert result.passed is True
        assert result.total_repos == 200
        assert result.indexed_repos == 180
        assert result.indexed_ratio == pytest.approx(180 / 200)
        assert result.min_repos == 100
        assert result.max_repos == 1000
        assert result.min_indexed_ratio == 0.8
