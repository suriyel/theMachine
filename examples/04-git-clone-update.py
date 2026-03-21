"""Example: Git Clone & Update with GitCloner.

Demonstrates:
- Cloning a public Git repository to a local directory
- Cloning with a specific branch (Wave 1)
- Updating (fetch + reset) an already-cloned repository
- Detecting default branch and listing remote branches (Wave 1)
- Error handling for unreachable URLs
- Cleanup of partial files on failure

Requires: git binary installed and available on PATH.
"""

import os
import tempfile

from src.indexing.git_cloner import GitCloner
from src.shared.exceptions import CloneError


def main() -> None:
    # Use a temporary directory as the storage path
    with tempfile.TemporaryDirectory() as storage_path:
        cloner = GitCloner(storage_path=storage_path)

        # 1. Clone a small public repository
        print("1. Cloning https://github.com/octocat/Hello-World ...")
        dest = cloner.clone_or_update("hello-world", "https://github.com/octocat/Hello-World")
        print(f"   -> cloned to: {dest}")
        print(f"   -> .git exists: {os.path.isdir(os.path.join(dest, '.git'))}")
        files = [f for f in os.listdir(dest) if f != ".git"]
        print(f"   -> files: {files}")

        # 2. Detect default branch and list remote branches (Wave 1)
        print("\n2. Detecting default branch ...")
        default_branch = cloner.detect_default_branch(dest)
        print(f"   -> default_branch: {default_branch}")

        print("\n3. Listing remote branches ...")
        branches = cloner.list_remote_branches(dest)
        print(f"   -> branches: {branches}")

        # 4. Update the same repository (fetch + reset, no re-clone)
        print("\n4. Updating the same repository ...")
        dest2 = cloner.clone_or_update(
            "hello-world", "https://github.com/octocat/Hello-World",
            branch=default_branch,
        )
        print(f"   -> path unchanged: {dest2 == dest}")
        print(f"   -> .git still exists: {os.path.isdir(os.path.join(dest2, '.git'))}")

        # 5. Attempt to clone an unreachable URL
        print("\n5. Cloning unreachable URL ...")
        try:
            cloner.clone_or_update("bad-repo", "https://invalid.example.com/no-repo.git")
        except CloneError as e:
            print(f"   -> CloneError: {e}")
            print(f"   -> partial cleanup: {not os.path.exists(os.path.join(storage_path, 'bad-repo'))}")

    print("\nDone. Temporary directory cleaned up.")


if __name__ == "__main__":
    main()
