"""Tests for Feature #4 — Git Clone & Update (GitCloner).

Wave 1 update: Added branch parameter, detect_default_branch, list_remote_branches tests.

Test Inventory from feature detailed design:
- T1-T2: happy path (clone, update)
- T3-T5: error (clone failure, update failure, disk error)
- T6-T8: boundary (timeout, git not found, corrupted .git)
- T9-T10: cleanup behavior
- T11-T12: _run_git internals
- T13-T18: Wave 1 — branch parameter, detect_default_branch, list_remote_branches

Security: N/A — internal utility with no user-facing input.

Negative tests: T3-T8, T10, T12, T18 = 9/21 = 43% >= 40%
"""

import logging
import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.shared.exceptions import CloneError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def storage_path(tmp_path: Path) -> str:
    """Provide a temporary storage path for GitCloner."""
    return str(tmp_path)


@pytest.fixture()
def cloner(storage_path: str):
    """Create a GitCloner instance with a temp storage path."""
    from src.indexing.git_cloner import GitCloner

    return GitCloner(storage_path=storage_path)


# ---------------------------------------------------------------------------
# T1: Happy path — fresh clone
# [unit] — mocks subprocess
# ---------------------------------------------------------------------------

def test_clone_or_update_clones_new_repo(cloner, storage_path: str):
    """T1: Given a new repo_id, clone_or_update performs git clone and returns dest_path."""
    repo_id = "abc123"
    url = "https://github.com/octocat/Hello-World"
    expected_dest = os.path.join(storage_path, repo_id)

    with patch("src.indexing.git_cloner.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="Cloning...\n", stderr="")
        result = cloner.clone_or_update(repo_id, url)

    assert result == expected_dest
    # Verify git clone was called with correct args
    call_args = mock_run.call_args_list[0]
    cmd = call_args[0][0]
    assert cmd[0] == "git"
    assert cmd[1] == "clone"
    assert cmd[2] == url
    assert cmd[3] == expected_dest


# ---------------------------------------------------------------------------
# T2: Happy path — update existing clone
# [unit] — mocks subprocess
# ---------------------------------------------------------------------------

def test_clone_or_update_updates_existing_repo(cloner, storage_path: str):
    """T2: Given a previously cloned repo (.git exists), performs fetch+reset, not clone."""
    repo_id = "existing-repo"
    url = "https://github.com/octocat/Hello-World"
    dest_path = os.path.join(storage_path, repo_id)

    # Create a .git directory to simulate existing clone
    os.makedirs(os.path.join(dest_path, ".git"))

    with patch("src.indexing.git_cloner.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = cloner.clone_or_update(repo_id, url)

    assert result == dest_path
    # Should have called fetch and reset, NOT clone
    assert mock_run.call_count == 2
    fetch_cmd = mock_run.call_args_list[0][0][0]
    reset_cmd = mock_run.call_args_list[1][0][0]
    assert fetch_cmd == ["git", "fetch", "origin"]
    assert reset_cmd == ["git", "reset", "--hard", "origin/HEAD"]
    # Verify cwd was set to dest_path for both calls
    assert mock_run.call_args_list[0][1]["cwd"] == dest_path
    assert mock_run.call_args_list[1][1]["cwd"] == dest_path


# ---------------------------------------------------------------------------
# T3: Error — clone failure with cleanup
# [unit] — mocks subprocess
# ---------------------------------------------------------------------------

def test_clone_failure_raises_clone_error_and_cleans_up(cloner, storage_path: str):
    """T3: Given unreachable URL, clone_or_update raises CloneError and cleans up."""
    repo_id = "fail-repo"
    url = "https://invalid.example.com/no-repo"
    dest_path = os.path.join(storage_path, repo_id)

    with patch("src.indexing.git_cloner.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=128,
            stdout="",
            stderr="fatal: Could not resolve host: invalid.example.com",
        )
        with pytest.raises(CloneError, match="Could not resolve host"):
            cloner.clone_or_update(repo_id, url)

    # Verify partial files were cleaned up
    assert not os.path.exists(dest_path)


# ---------------------------------------------------------------------------
# T4: Error — update (fetch) failure
# [unit] — mocks subprocess
# ---------------------------------------------------------------------------

def test_update_failure_raises_clone_error(cloner, storage_path: str):
    """T4: Given git fetch fails during update, CloneError is raised."""
    repo_id = "update-fail"
    url = "https://github.com/octocat/Hello-World"
    dest_path = os.path.join(storage_path, repo_id)
    os.makedirs(os.path.join(dest_path, ".git"))

    with patch("src.indexing.git_cloner.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="fatal: Connection refused",
        )
        with pytest.raises(CloneError, match="Connection refused"):
            cloner.clone_or_update(repo_id, url)


# ---------------------------------------------------------------------------
# T5: Error — disk space failure with cleanup
# [unit] — mocks subprocess
# ---------------------------------------------------------------------------

def test_disk_space_error_raises_clone_error_and_cleans_up(cloner, storage_path: str):
    """T5: Given disk-full during clone, CloneError raised and cleanup runs."""
    repo_id = "disk-full"
    url = "https://github.com/octocat/Hello-World"
    dest_path = os.path.join(storage_path, repo_id)

    with patch("src.indexing.git_cloner.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=128,
            stdout="",
            stderr="fatal: No space left on device",
        )
        with pytest.raises(CloneError, match="No space left"):
            cloner.clone_or_update(repo_id, url)

    assert not os.path.exists(dest_path)


# ---------------------------------------------------------------------------
# T6: Boundary — timeout
# [unit] — mocks subprocess
# ---------------------------------------------------------------------------

def test_timeout_raises_clone_error(cloner, storage_path: str):
    """T6: Given git clone hangs beyond timeout, CloneError is raised."""
    repo_id = "timeout-repo"
    url = "https://github.com/octocat/Hello-World"

    with patch("src.indexing.git_cloner.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["git", "clone"], timeout=300
        )
        with pytest.raises(CloneError, match="timed out"):
            cloner.clone_or_update(repo_id, url)


# ---------------------------------------------------------------------------
# T7: Error — git binary not found
# [unit] — mocks subprocess
# ---------------------------------------------------------------------------

def test_git_not_found_raises_clone_error(cloner, storage_path: str):
    """T7: Given git is not installed, CloneError('git not found') is raised."""
    repo_id = "no-git"
    url = "https://github.com/octocat/Hello-World"

    with patch("src.indexing.git_cloner.subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError("No such file or directory: 'git'")
        with pytest.raises(CloneError, match="git not found"):
            cloner.clone_or_update(repo_id, url)


# ---------------------------------------------------------------------------
# T8: Boundary — corrupted .git directory (update fails)
# [unit] — mocks subprocess
# ---------------------------------------------------------------------------

def test_corrupted_git_dir_raises_clone_error(cloner, storage_path: str):
    """T8: Given .git exists but is corrupted, update fails with CloneError."""
    repo_id = "corrupt-repo"
    url = "https://github.com/octocat/Hello-World"
    dest_path = os.path.join(storage_path, repo_id)
    os.makedirs(os.path.join(dest_path, ".git"))

    with patch("src.indexing.git_cloner.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=128,
            stdout="",
            stderr="fatal: not a git repository",
        )
        with pytest.raises(CloneError, match="not a git repository"):
            cloner.clone_or_update(repo_id, url)


# ---------------------------------------------------------------------------
# T9: Happy path — cleanup on non-existent path (no-op)
# [unit] — direct call
# ---------------------------------------------------------------------------

def test_cleanup_partial_noop_on_missing_path(cloner):
    """T9: _cleanup_partial on non-existent path is a no-op, no error."""
    # Should not raise
    cloner._cleanup_partial("/nonexistent/path/that/does/not/exist")


# ---------------------------------------------------------------------------
# T10: Error — cleanup itself fails (logs warning)
# [unit] — mocks shutil.rmtree
# ---------------------------------------------------------------------------

def test_cleanup_failure_logs_warning_no_exception(cloner, storage_path: str, caplog):
    """T10: If rmtree fails during cleanup, a warning is logged but no exception raised."""
    dest_path = os.path.join(storage_path, "cleanup-fail")
    os.makedirs(dest_path)

    with patch("src.indexing.git_cloner.shutil.rmtree") as mock_rmtree:
        mock_rmtree.side_effect = OSError("Permission denied")
        with caplog.at_level(logging.WARNING):
            cloner._cleanup_partial(dest_path)  # Must not raise

    assert "Permission denied" in caplog.text


# ---------------------------------------------------------------------------
# T11: Happy path — _run_git returns stdout
# [unit] — mocks subprocess
# ---------------------------------------------------------------------------

def test_run_git_returns_stdout(cloner):
    """T11: _run_git returns stdout on success."""
    with patch("src.indexing.git_cloner.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="git version 2.43.0\n", stderr=""
        )
        result = cloner._run_git(["--version"])

    assert result == "git version 2.43.0\n"


# ---------------------------------------------------------------------------
# T12: Error — _run_git with non-zero exit
# [unit] — mocks subprocess
# ---------------------------------------------------------------------------

def test_run_git_nonzero_exit_raises_clone_error(cloner):
    """T12: _run_git raises CloneError with stderr content on non-zero exit."""
    with patch("src.indexing.git_cloner.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="error: unknown option"
        )
        with pytest.raises(CloneError, match="error: unknown option"):
            cloner._run_git(["bad-command"])


# ---------------------------------------------------------------------------
# Real Tests — actual git subprocess
# [integration] — uses real git binary and filesystem
# ---------------------------------------------------------------------------

@pytest.mark.real
def test_real_clone_public_repo(tmp_path: Path):
    """Real test: clone a small public repo using actual git.

    Uses a tiny repo to minimize clone time.
    """
    from src.indexing.git_cloner import GitCloner

    storage = str(tmp_path / "repos")
    os.makedirs(storage)
    cloner = GitCloner(storage_path=storage)

    repo_id = "test-clone"
    url = "https://github.com/octocat/Hello-World"

    result = cloner.clone_or_update(repo_id, url)

    assert result == os.path.join(storage, repo_id)
    assert os.path.isdir(os.path.join(result, ".git"))
    # Verify we got actual files (not empty dir)
    files = os.listdir(result)
    assert len(files) > 1  # At minimum .git + README


@pytest.mark.real
def test_real_update_after_clone(tmp_path: Path):
    """Real test: clone then update the same repo — verifies fetch+reset path."""
    from src.indexing.git_cloner import GitCloner

    storage = str(tmp_path / "repos")
    os.makedirs(storage)
    cloner = GitCloner(storage_path=storage)

    repo_id = "test-update"
    url = "https://github.com/octocat/Hello-World"

    # First clone
    result1 = cloner.clone_or_update(repo_id, url)
    assert os.path.isdir(os.path.join(result1, ".git"))

    # Second call should update, not re-clone
    result2 = cloner.clone_or_update(repo_id, url)
    assert result2 == result1
    assert os.path.isdir(os.path.join(result2, ".git"))


@pytest.mark.real
def test_real_clone_invalid_url_raises_clone_error(tmp_path: Path):
    """Real test: clone with unreachable URL raises CloneError."""
    from src.indexing.git_cloner import GitCloner

    storage = str(tmp_path / "repos")
    os.makedirs(storage)
    cloner = GitCloner(storage_path=storage)

    with pytest.raises(CloneError):
        cloner.clone_or_update("bad-repo", "https://invalid.example.com/no-repo.git")

    # Verify cleanup happened
    assert not os.path.exists(os.path.join(storage, "bad-repo"))


# ---------------------------------------------------------------------------
# Wave 1: Branch parameter tests
# ---------------------------------------------------------------------------

# [unit] T13: clone with explicit branch passes --branch flag
def test_clone_with_branch_passes_branch_flag(cloner, storage_path: str):
    """VS-2: clone_or_update with branch='develop' passes --branch develop to git clone."""
    repo_id = "branch-repo"
    url = "https://github.com/octocat/Hello-World"
    expected_dest = os.path.join(storage_path, repo_id)

    with patch("src.indexing.git_cloner.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = cloner.clone_or_update(repo_id, url, branch="develop")

    assert result == expected_dest
    call_args = mock_run.call_args_list[0]
    cmd = call_args[0][0]
    assert cmd == ["git", "clone", "--branch", "develop", url, expected_dest]


# [unit] T14: clone without branch does NOT pass --branch flag
def test_clone_without_branch_no_branch_flag(cloner, storage_path: str):
    """VS-1: clone_or_update without branch does not pass --branch flag."""
    repo_id = "no-branch-repo"
    url = "https://github.com/octocat/Hello-World"
    expected_dest = os.path.join(storage_path, repo_id)

    with patch("src.indexing.git_cloner.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        cloner.clone_or_update(repo_id, url)

    cmd = mock_run.call_args_list[0][0][0]
    assert "--branch" not in cmd
    assert cmd == ["git", "clone", url, expected_dest]


# [unit] T15: update with branch resets to origin/{branch}
def test_update_with_branch_resets_to_origin_branch(cloner, storage_path: str):
    """VS-3: update with branch='main' resets to origin/main."""
    repo_id = "update-branch"
    url = "https://github.com/octocat/Hello-World"
    dest_path = os.path.join(storage_path, repo_id)
    os.makedirs(os.path.join(dest_path, ".git"))

    with patch("src.indexing.git_cloner.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        cloner.clone_or_update(repo_id, url, branch="main")

    reset_cmd = mock_run.call_args_list[1][0][0]
    assert reset_cmd == ["git", "reset", "--hard", "origin/main"]


# [unit] T16: detect_default_branch parses symbolic-ref output
def test_detect_default_branch(cloner, storage_path: str):
    """VS-1: detect_default_branch returns branch name from symbolic-ref."""
    repo_path = os.path.join(storage_path, "test-repo")
    os.makedirs(os.path.join(repo_path, ".git"))

    with patch("src.indexing.git_cloner.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="refs/remotes/origin/main\n", stderr=""
        )
        result = cloner.detect_default_branch(repo_path)

    assert result == "main"


# [unit] T17: list_remote_branches returns sorted list with origin/ stripped
def test_list_remote_branches(cloner, storage_path: str):
    """VS-5: list_remote_branches returns sorted branch names without origin/ prefix."""
    repo_path = os.path.join(storage_path, "test-repo")
    os.makedirs(os.path.join(repo_path, ".git"))

    branch_output = (
        "  origin/HEAD -> origin/main\n"
        "  origin/develop\n"
        "  origin/feature/xyz\n"
        "  origin/main\n"
    )

    with patch("src.indexing.git_cloner.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout=branch_output, stderr=""
        )
        result = cloner.list_remote_branches(repo_path)

    assert result == ["develop", "feature/xyz", "main"]
    # HEAD entry should be excluded
    assert "HEAD -> origin/main" not in result


# [unit] T18: list_remote_branches on failure raises CloneError
def test_list_remote_branches_failure_raises_clone_error(cloner, storage_path: str):
    """Error: list_remote_branches raises CloneError when git branch -r fails."""
    repo_path = os.path.join(storage_path, "test-repo")
    os.makedirs(os.path.join(repo_path, ".git"))

    with patch("src.indexing.git_cloner.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=128, stdout="", stderr="fatal: not a git repository"
        )
        with pytest.raises(CloneError, match="not a git repository"):
            cloner.list_remote_branches(repo_path)
