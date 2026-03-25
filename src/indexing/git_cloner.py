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

    def clone_or_update(
        self, repo_id: str, url: str, branch: str | None = None
    ) -> str:
        """Clone a repository or update it if already cloned.

        Args:
            repo_id: Unique identifier for the repository.
            url: Git repository URL.
            branch: Optional branch to clone/checkout. If None, uses
                the repository's default branch.

        Returns:
            Path to the local clone directory.

        Raises:
            CloneError: If the git operation fails.
        """
        dest_path = str(Path(self._storage_path) / repo_id)

        if Path(dest_path, ".git").is_dir():
            self._update(dest_path, branch=branch)
        else:
            self._clone(url, dest_path, branch=branch)

        return dest_path

    def detect_default_branch(self, repo_path: str) -> str:
        """Detect the default branch of a cloned repository.

        Uses git symbolic-ref to read origin/HEAD.

        Returns:
            Branch name (e.g. "main").

        Raises:
            CloneError: If the command fails.
        """
        output = self._run_git(
            ["symbolic-ref", "refs/remotes/origin/HEAD"], cwd=repo_path
        )
        # Output is like "refs/remotes/origin/main\n"
        return output.strip().split("/")[-1]

    def list_remote_branches(self, repo_path: str) -> list[str]:
        """List remote branches for a cloned repository.

        Returns:
            Sorted list of branch names with origin/ prefix stripped.
            Excludes HEAD pointer entries.

        Raises:
            CloneError: If the command fails.
        """
        output = self._run_git(["branch", "-r"], cwd=repo_path)
        branches = []
        for line in output.strip().splitlines():
            line = line.strip()
            # Skip HEAD -> origin/main entries
            if "->" in line:
                continue
            # Strip origin/ prefix
            if line.startswith("origin/"):
                branches.append(line[len("origin/"):])
        return sorted(branches)

    async def list_remote_branches_by_url(self, url: str) -> list[str]:
        """List remote branches from a repository URL using git ls-remote.

        This is an async wrapper for the synchronous git command, intended
        for use by the web router's htmx branch listing endpoint.

        Args:
            url: Git repository URL (HTTPS or SSH).

        Returns:
            Sorted list of branch names. Returns empty list on failure.
        """
        try:
            output = self._run_git(["ls-remote", "--heads", url])
        except CloneError:
            logger.warning("Failed to list remote branches for %s", url)
            return []

        branches = []
        for line in output.strip().splitlines():
            # Format: <sha>\trefs/heads/<branch>
            parts = line.split("\t")
            if len(parts) == 2 and parts[1].startswith("refs/heads/"):
                branches.append(parts[1][len("refs/heads/"):])
        return sorted(branches)

    def _clone(
        self, url: str, dest_path: str, branch: str | None = None
    ) -> None:
        """Perform a fresh git clone."""
        try:
            cmd = ["clone"]
            if branch is not None:
                cmd.extend(["--branch", branch])
            cmd.extend([url, dest_path])
            self._run_git(cmd)
        except CloneError:
            self._cleanup_partial(dest_path)
            raise

    def _update(self, dest_path: str, branch: str | None = None) -> None:
        """Fetch and reset an existing clone to latest branch HEAD."""
        self._run_git(["fetch", "origin"], cwd=dest_path)
        target = f"origin/{branch}" if branch is not None else "origin/HEAD"
        self._run_git(["reset", "--hard", target], cwd=dest_path)

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
