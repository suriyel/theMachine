"""
NFR-004: Single Repository Size Tests

Tests for repository size test runner script - validates system can handle
repositories up to 1GB without failure.

[unit] — script subprocess tests
"""

import subprocess
import pytest
import os


class TestRepoSizeTestRunner:
    """Unit tests for the repository size test runner script"""

    def test_runner_script_exists(self):
        """Runner script should exist in scripts directory"""
        script_path = "scripts/run_repo_size_test.py"
        assert os.path.exists(script_path), f"Runner script {script_path} should exist"

    def test_runner_accepts_help(self):
        """Runner should respond to --help"""
        result = subprocess.run(
            ["python3", "scripts/run_repo_size_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "Script should respond to --help"

    def test_runner_documents_nfr004(self):
        """Runner should document NFR-004 thresholds"""
        result = subprocess.run(
            ["python3", "scripts/run_repo_size_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "NFR-004" in result.stdout, "Script should reference NFR-004"
        assert "1" in result.stdout and "GB" in result.stdout or "1024" in result.stdout, \
            "Script should reference 1GB threshold"

    def test_runner_accepts_host_parameter(self):
        """Runner should accept --host parameter"""
        result = subprocess.run(
            ["python3", "scripts/run_repo_size_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "--host" in result.stdout, "Script should accept --host"

    def test_runner_accepts_validate_parameter(self):
        """Runner should accept --validate parameter"""
        result = subprocess.run(
            ["python3", "scripts/run_repo_size_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "--validate" in result.stdout, "Script should accept --validate"

    def test_runner_accepts_size_parameter(self):
        """Runner should accept --size parameter"""
        result = subprocess.run(
            ["python3", "scripts/run_repo_size_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "--size" in result.stdout, "Script should accept --size"

    def test_runner_accepts_chunks_parameter(self):
        """Runner should accept --chunks parameter"""
        result = subprocess.run(
            ["python3", "scripts/run_repo_size_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "--chunks" in result.stdout, "Script should accept --chunks"

    def test_runner_accepts_test_large_file_parameter(self):
        """Runner should accept --test-large-file parameter"""
        result = subprocess.run(
            ["python3", "scripts/run_repo_size_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "--test-large-file" in result.stdout, "Script should accept --test-large-file"


class TestRepoSizeThresholdValidation:
    """Tests for repository size threshold validation logic"""

    def test_validate_size_small_pass(self):
        """10 MB repository should pass"""
        result = subprocess.run(
            ["python3", "scripts/run_repo_size_test.py", "--validate",
             "--size", "10", "--chunks", "200"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Should pass with 10MB repo: {result.stderr}"

    def test_validate_size_medium_pass(self):
        """100 MB repository should pass"""
        result = subprocess.run(
            ["python3", "scripts/run_repo_size_test.py", "--validate",
             "--size", "100", "--chunks", "2000"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Should pass with 100MB repo: {result.stderr}"

    def test_validate_size_large_pass(self):
        """500 MB repository should pass"""
        result = subprocess.run(
            ["python3", "scripts/run_repo_size_test.py", "--validate",
             "--size", "500", "--chunks", "10000"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Should pass with 500MB repo: {result.stderr}"

    def test_validate_size_at_max_pass(self):
        """1 GB (1024 MB) repository should pass"""
        result = subprocess.run(
            ["python3", "scripts/run_repo_size_test.py", "--validate",
             "--size", "1024", "--chunks", "20000"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Should pass with 1GB repo: {result.stderr}"
        assert "PASS" in result.stdout or "pass" in result.stdout.lower()

    def test_validate_size_over_max_fail(self):
        """Over 1 GB repository should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_repo_size_test.py", "--validate",
             "--size", "2048", "--chunks", "40000"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, f"Should fail over 1GB: {result.stdout}"
        assert "FAIL" in result.stdout or "fail" in result.stdout.lower()

    def test_validate_zero_size_fail(self):
        """Zero size should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_repo_size_test.py", "--validate",
             "--size", "0", "--chunks", "0"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, "Should fail with zero size"

    def test_validate_negative_size_fail(self):
        """Negative size should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_repo_size_test.py", "--validate",
             "--size", "-100", "--chunks", "0"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, "Should fail with negative size"

    def test_validate_missing_size_fail(self):
        """Missing --size should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_repo_size_test.py", "--validate",
             "--chunks", "1000"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, "Should fail without --size"

    def test_validate_missing_chunks_fail(self):
        """Missing --chunks should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_repo_size_test.py", "--validate",
             "--size", "500"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, "Should fail without --chunks"

    def test_validate_zero_chunks_fail(self):
        """Zero chunks indexed should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_repo_size_test.py", "--validate",
             "--size", "500", "--chunks", "0"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, "Should fail with zero chunks indexed"


class TestLargeFileHandling:
    """Tests for large file handling"""

    def test_large_file_test_accepts_params(self):
        """Large file test should accept parameters"""
        result = subprocess.run(
            ["python3", "scripts/run_repo_size_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "--file-size" in result.stdout, "Script should accept --file-size"
        assert "--file-processed" in result.stdout, "Script should accept --file-processed"

    def test_large_file_processed_pass(self):
        """Large file processed successfully should pass"""
        result = subprocess.run(
            ["python3", "scripts/run_repo_size_test.py", "--test-large-file",
             "--file-size", "50", "--file-processed"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Should pass with processed file: {result.stderr}"

    def test_large_file_not_processed_fail(self):
        """Large file not processed should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_repo_size_test.py", "--test-large-file",
             "--file-size", "50"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, f"Should fail with unprocessed file: {result.stdout}"

    def test_large_file_missing_size_fail(self):
        """Large file test without size should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_repo_size_test.py", "--test-large-file",
             "--file-processed"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, "Should fail without --file-size"


# [no integration test] - NFR size testing requires external services
# and is tested via ST acceptance tests
