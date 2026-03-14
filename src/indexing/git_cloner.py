"""GitCloner - Clone or update Git repositories for indexing."""

import os
import time
from pathlib import Path
from typing import Optional

import git

from src.indexing.exceptions import GitCloneFailedError, GitFetchError


class GitCloner:
    """Service for cloning or updating Git repositories.

    This class handles:
    - Full clone of new repositories
    - Fetch updates for existing repositories
    - Retry logic with exponential backoff
    - Error handling for network and auth failures
    """

    MAX_RETRIES = 3
    INITIAL_BACKOFF = 1  # seconds

    def __init__(self, workspace_dir: Optional[str] = None):
        """Initialize GitCloner with workspace directory.

        Args:
            workspace_dir: Path to store cloned repositories.
                          Defaults to WORKSPACE_DIR env var or ./workspace
        """
        if workspace_dir:
            self.workspace_dir = Path(workspace_dir)
        else:
            self.workspace_dir = Path(
                os.environ.get("WORKSPACE_DIR", "./workspace")
            )

        # Create workspace if it doesn't exist
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

    def _get_repo_path(self, repo_id: str) -> Path:
        """Get the path where a repository should be cloned.

        Args:
            repo_id: Repository UUID

        Returns:
            Path to the repository directory
        """
        return self.workspace_dir / repo_id

    async def clone_or_update(self, repo) -> Path:
        """Clone a repository if not exists, or fetch updates if already cloned.

        Args:
            repo: Repository object with id and url attributes

        Returns:
            Path to the cloned/updated repository

        Raises:
            GitCloneFailedError: If clone operation fails
            GitFetchError: If fetch operation fails
        """
        repo_path = self._get_repo_path(str(repo.id))

        if repo_path.exists():
            await self._fetch_updates(repo_path)
        else:
            await self._full_clone(repo.url, repo_path)

        return repo_path

    async def _full_clone(self, url: str, dest: Path) -> None:
        """Perform a full git clone.

        Args:
            url: Git repository URL
            dest: Destination path for the cloned repository

        Raises:
            GitCloneFailedError: If clone fails after all retries
        """
        # Create parent directory if needed
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Auth failure should not retry
        auth_error_messages = [
            "authentication",
            "auth",
            "permission denied",
            "could not read",
            "bad credentials",
        ]

        for attempt in range(self.MAX_RETRIES):
            try:
                git.Repo.clone_from(url, str(dest))
                return
            except git.GitCommandError as e:
                error_msg = str(e).lower()

                # Check if it's an auth failure - don't retry
                if any(msg in error_msg for msg in auth_error_messages):
                    raise GitCloneFailedError(
                        f"Authentication failed for {url}: {e}"
                    ) from e

                # Check if it's a "not found" error - don't retry
                if "not found" in error_msg or "404" in error_msg:
                    raise GitCloneFailedError(
                        f"Repository not found: {url}"
                    ) from e

                if attempt < self.MAX_RETRIES - 1:
                    backoff = self.INITIAL_BACKOFF * (2 ** attempt)
                    time.sleep(backoff)
                else:
                    raise GitCloneFailedError(
                        f"Failed to clone {url} after {self.MAX_RETRIES} attempts: {e}"
                    ) from e
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    backoff = self.INITIAL_BACKOFF * (2 ** attempt)
                    time.sleep(backoff)
                else:
                    raise GitCloneFailedError(
                        f"Failed to clone {url}: {e}"
                    ) from e

    async def _fetch_updates(self, repo_path: Path) -> None:
        """Fetch latest changes from remote.

        Args:
            repo_path: Path to the existing repository

        Raises:
            GitFetchError: If fetch fails
        """
        try:
            repo = git.Repo(str(repo_path))

            # Fetch from origin
            origin = repo.remotes.origin
            origin.fetch()

            # Get current branch and pull latest changes
            if repo.active_branch.tracking_branch():
                origin.pull()

        except git.GitCommandError as e:
            raise GitFetchError(
                f"Failed to fetch updates for {repo_path}: {e}"
            ) from e
        except Exception as e:
            raise GitFetchError(
                f"Failed to fetch updates for {repo_path}: {e}"
            ) from e
