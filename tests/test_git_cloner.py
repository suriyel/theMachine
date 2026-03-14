"""Tests for GitCloner - Feature #4 FR-002.

These tests verify git clone/update functionality for repository indexing.
"""
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.indexing.git_cloner import GitCloner
from src.indexing.exceptions import (
    GitCloneError,
    GitCloneFailedError,
    GitFetchError,
)


class TestGitClonerInit:
    """[unit] Tests for GitCloner initialization."""

    def test_git_cloner_accepts_workspace_dir(self):
        """GitCloner should accept custom workspace directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cloner = GitCloner(workspace_dir=tmpdir)
            assert cloner.workspace_dir == Path(tmpdir)

    def test_git_cloner_creates_workspace_if_not_exists(self):
        """GitCloner should create workspace directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = os.path.join(tmpdir, "new_workspace")
            cloner = GitCloner(workspace_dir=workspace)
            assert os.path.exists(workspace)

    def test_git_cloner_default_workspace(self):
        """GitCloner should use default workspace from env var or ./workspace."""
        cloner = GitCloner()
        assert cloner.workspace_dir is not None


class TestCloneOrUpdate:
    """[unit] Tests for clone_or_update method."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace directory."""
        tmpdir = tempfile.mkdtemp()
        yield tmpdir
        shutil.rmtree(tmpdir, ignore_errors=True)

    @pytest.fixture
    def mock_repo(self):
        """Create mock Repository object."""
        repo = MagicMock()
        repo.id = "550e8400-e29b-41d4-a716-446655440000"
        repo.url = "https://github.com/test/repo.git"
        repo.name = "test-repo"
        return repo

    @pytest.mark.asyncio
    async def test_clone_or_update_full_clone_new_repo(self, temp_workspace, mock_repo):
        """Given repository not yet cloned, when clone_or_update runs, then full clone is performed."""
        cloner = GitCloner(workspace_dir=temp_workspace)

        with patch.object(cloner, '_full_clone', new_callable=AsyncMock) as mock_full:
            with patch('pathlib.Path.exists', return_value=False):
                result = await cloner.clone_or_update(mock_repo)

                mock_full.assert_called_once_with(
                    mock_repo.url,
                    Path(temp_workspace) / str(mock_repo.id)
                )

    @pytest.mark.asyncio
    async def test_clone_or_update_fetch_existing_repo(self, temp_workspace, mock_repo):
        """Given previously cloned repository, when clone_or_update runs, then fetch is performed."""
        cloner = GitCloner(workspace_dir=temp_workspace)
        repo_path = Path(temp_workspace) / str(mock_repo.id)

        with patch.object(cloner, '_fetch_updates', new_callable=AsyncMock) as mock_fetch:
            with patch('pathlib.Path.exists', return_value=True):
                result = await cloner.clone_or_update(mock_repo)

                mock_fetch.assert_called_once_with(repo_path)

    @pytest.mark.asyncio
    async def test_clone_or_update_returns_path(self, temp_workspace, mock_repo):
        """clone_or_update should return the path to cloned repository."""
        cloner = GitCloner(workspace_dir=temp_workspace)

        with patch.object(cloner, '_full_clone', new_callable=AsyncMock):
            with patch('pathlib.Path.exists', return_value=False):
                result = await cloner.clone_or_update(mock_repo)
                assert result == Path(temp_workspace) / str(mock_repo.id)


class TestFullClone:
    """[unit] Tests for _full_clone method."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace directory."""
        tmpdir = tempfile.mkdtemp()
        yield tmpdir
        shutil.rmtree(tmpdir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_full_clone_calls_git_clone(self, temp_workspace):
        """_full_clone should call git.Repo.clone_from."""
        cloner = GitCloner(workspace_dir=temp_workspace)
        url = "https://github.com/test/repo.git"
        dest = Path(temp_workspace) / "dest"

        with patch('git.Repo.clone_from') as mock_clone:
            mock_clone.return_value = MagicMock()
            await cloner._full_clone(url, dest)

            mock_clone.assert_called_once()

    @pytest.mark.asyncio
    async def test_full_clone_raises_on_auth_failure(self, temp_workspace):
        """Given invalid credentials, _full_clone should raise GitCloneFailedError immediately."""
        cloner = GitCloner(workspace_dir=temp_workspace)
        url = "https://bad credentials@github.com/test/repo.git"
        dest = Path(temp_workspace) / "dest"

        with patch('git.Repo.clone_from') as mock_clone:
            import git
            mock_clone.side_effect = git.GitCommandError("clone", 128, "Authentication failed")

            with pytest.raises(GitCloneFailedError) as exc_info:
                await cloner._full_clone(url, dest)

            assert "Authentication failed" in str(exc_info.value)


class TestFetchUpdates:
    """[unit] Tests for _fetch_updates method."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace directory."""
        tmpdir = tempfile.mkdtemp()
        yield tmpdir
        shutil.rmtree(tmpdir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_fetch_updates_calls_git_pull(self, temp_workspace):
        """_fetch_updates should call git pull to get latest changes."""
        cloner = GitCloner(workspace_dir=temp_workspace)
        dest = Path(temp_workspace) / "repo"

        mock_repo = MagicMock()
        mock_repo.remotes.origin.pull.return_value = []

        with patch('git.Repo', return_value=mock_repo):
            await cloner._fetch_updates(dest)

            mock_repo.remotes.origin.pull.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_updates_raises_on_error(self, temp_workspace):
        """_fetch_updates should raise GitFetchError on failure."""
        cloner = GitCloner(workspace_dir=temp_workspace)
        dest = Path(temp_workspace) / "repo"

        with patch('git.Repo') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.remotes.origin.pull.side_effect = Exception("Network error")
            mock_repo_class.return_value = mock_repo

            with pytest.raises(GitFetchError):
                await cloner._fetch_updates(dest)


class TestGitClonerRetry:
    """[unit] Tests for retry logic."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace directory."""
        tmpdir = tempfile.mkdtemp()
        yield tmpdir
        shutil.rmtree(tmpdir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_full_clone_retries_on_network_timeout(self, temp_workspace):
        """Given network timeout, _full_clone should retry 3 times before failing."""
        cloner = GitCloner(workspace_dir=temp_workspace)
        url = "https://github.com/test/repo.git"
        dest = Path(temp_workspace) / "dest"

        with patch('git.Repo.clone_from') as mock_clone:
            mock_clone.side_effect = [
                Exception("Connection timeout"),
                Exception("Connection timeout"),
                Exception("Connection timeout"),
            ]

            with pytest.raises(GitCloneFailedError):
                await cloner._full_clone(url, dest)

            assert mock_clone.call_count == 3

    @pytest.mark.asyncio
    async def test_full_clone_succeeds_on_retry(self, temp_workspace):
        """_full_clone should succeed if retry succeeds."""
        cloner = GitCloner(workspace_dir=temp_workspace)
        url = "https://github.com/test/repo.git"
        dest = Path(temp_workspace) / "dest"

        with patch('git.Repo.clone_from') as mock_clone:
            mock_clone.side_effect = [
                Exception("Connection timeout"),
                MagicMock(),  # Success on second try
            ]

            await cloner._full_clone(url, dest)

            assert mock_clone.call_count == 2

    @pytest.mark.asyncio
    async def test_auth_failure_does_not_retry(self, temp_workspace):
        """Given auth failure, _full_clone should NOT retry - fail immediately."""
        cloner = GitCloner(workspace_dir=temp_workspace)
        url = "https://badcreds@github.com/test/repo.git"
        dest = Path(temp_workspace) / "dest"

        with patch('git.Repo.clone_from') as mock_clone:
            import git
            mock_clone.side_effect = git.GitCommandError("clone", 128, "Authentication failed")

            with pytest.raises(GitCloneFailedError):
                await cloner._full_clone(url, dest)

            assert mock_clone.call_count == 1  # No retries for auth failure


class TestGitClonerIntegration:
    """[integration] Integration tests for GitCloner with real git operations."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace directory."""
        tmpdir = tempfile.mkdtemp()
        yield tmpdir
        shutil.rmtree(tmpdir, ignore_errors=True)

    @pytest.mark.asyncio
    @pytest.mark.real_test
    async def test_clone_public_repository(self, temp_workspace):
        """Given a public repository, when cloning, then it should succeed."""
        cloner = GitCloner(workspace_dir=temp_workspace)
        url = "https://github.com/octocat/Hello-World.git"
        dest = Path(temp_workspace) / "hello-world"

        result = await cloner._full_clone(url, dest)

        assert dest.exists()
        assert (dest / ".git").exists()

    @pytest.mark.asyncio
    @pytest.mark.real_test
    async def test_clone_invalid_url_raises_error(self, temp_workspace):
        """Given an invalid repository URL, when cloning, then it should raise error."""
        cloner = GitCloner(workspace_dir=temp_workspace)
        url = "https://github.com/this/does/not/exist.git"
        dest = Path(temp_workspace) / "invalid"

        with pytest.raises(GitCloneFailedError):
            await cloner._full_clone(url, dest)
