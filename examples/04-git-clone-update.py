"""Example: Git Clone or Update

This example demonstrates how to use the GitCloner to clone or update
Git repositories for indexing.

Usage:
    python examples/04-git-clone-update.py

The script clones a public repository to demonstrate the GitCloner API.
"""

import asyncio
import os
import shutil
import sys
import tempfile
from pathlib import Path


# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.indexing.git_cloner import GitCloner
from src.indexing.exceptions import GitCloneFailedError, GitFetchError


class MockRepo:
    """Mock repository object for demonstration."""

    def __init__(self, repo_id: str, url: str, name: str):
        self.id = repo_id
        self.url = url
        self.name = name


async def main():
    """Demonstrate GitCloner usage."""
    # Create temporary workspace
    workspace = tempfile.mkdtemp(prefix="ccr_git_demo_")
    print(f"Using workspace: {workspace}")

    cloner = GitCloner(workspace_dir=workspace)

    try:
        # Example 1: Clone a new repository
        print("\n--- Example 1: Full Clone ---")
        repo = MockRepo(
            repo_id="550e8400-e29b-41d4-a716-446655440000",
            url="https://github.com/octocat/Hello-World.git",
            name="octocat/Hello-World",
        )

        print(f"Cloning {repo.url}...")
        repo_path = await cloner.clone_or_update(repo)
        print(f"✓ Repository cloned to: {repo_path}")
        print(f"  Directory exists: {repo_path.exists()}")
        print(f"  Is git repo: {(repo_path / '.git').exists()}")

        # Example 2: Update existing repository (fetch)
        print("\n--- Example 2: Fetch Updates ---")
        print(f"Fetching updates for {repo.name}...")
        # This will call _fetch_updates since repo already exists
        repo_path = await cloner.clone_or_update(repo)
        print(f"✓ Repository updated at: {repo_path}")

        # Example 3: Error handling - invalid URL
        print("\n--- Example 3: Error Handling ---")
        invalid_repo = MockRepo(
            repo_id="550e8400-e29b-41d4-a716-446655440001",
            url="https://github.com/this/does/not/exist.git",
            name="invalid",
        )

        try:
            await cloner.clone_or_update(invalid_repo)
            print("✗ Should have raised an error")
        except GitCloneFailedError as e:
            print(f"✓ Caught expected error: {type(e).__name__}")
            print(f"  Message: {str(e)[:80]}...")

        print("\n--- All examples completed successfully ---")

    finally:
        # Cleanup
        print(f"\nCleaning up workspace: {workspace}")
        shutil.rmtree(workspace, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
