"""GitCloner — clones and updates Git repositories for indexing."""

import logging
import shutil
import subprocess
from pathlib import Path

from src.shared.exceptions import CloneError

logger = logging.getLogger(__name__)


class GitCloner:
    """Clones new repositories and fetches updates for existing ones."""

    def __init__(self, storage_path: str) -> None:
        self._storage_path = storage_path

    def clone_or_update(self, repo_id: str, url: str) -> str:
        """Clone a repository or update it if already cloned.

        Args:
            repo_id: Unique identifier for the repository.
            url: Git repository URL.

        Returns:
            Path to the local clone directory.

        Raises:
            CloneError: If the git operation fails.
        """
        dest_path = str(Path(self._storage_path) / repo_id)

        if Path(dest_path, ".git").is_dir():
            self._update(dest_path)
        else:
            self._clone(url, dest_path)

        return dest_path

    def _clone(self, url: str, dest_path: str) -> None:
        """Perform a fresh git clone."""
        try:
            self._run_git(["clone", url, dest_path])
        except CloneError:
            self._cleanup_partial(dest_path)
            raise

    def _update(self, dest_path: str) -> None:
        """Fetch and reset an existing clone to latest HEAD."""
        self._run_git(["fetch", "origin"], cwd=dest_path)
        self._run_git(["reset", "--hard", "origin/HEAD"], cwd=dest_path)

    def _cleanup_partial(self, dest_path: str) -> None:
        """Remove a partially cloned directory. No-op if path doesn't exist."""
        if Path(dest_path).exists():
            try:
                shutil.rmtree(dest_path)
            except OSError as exc:
                logger.warning("cleanup failed for %s: %s", dest_path, exc)

    def _run_git(self, args: list[str], cwd: str | None = None) -> str:
        """Execute a git command and return stdout.

        Raises:
            CloneError: If the command fails or times out.
        """
        cmd = ["git"] + args
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=cwd,
            )
        except subprocess.TimeoutExpired as exc:
            raise CloneError(f"git {args[0]} timed out after {exc.timeout}s") from exc
        except FileNotFoundError as exc:
            raise CloneError("git not found — is git installed?") from exc

        if result.returncode != 0:
            raise CloneError(
                f"git {args[0]} failed: {result.stderr.strip()}"
            )

        return result.stdout
