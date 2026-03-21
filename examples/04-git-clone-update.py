"""Example: Git Clone & Update with GitCloner.

Demonstrates:
- Cloning a public Git repository to a local directory
- Updating (fetch + reset) an already-cloned repository
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

        # 2. Update the same repository (fetch + reset, no re-clone)
        print("\n2. Updating the same repository ...")
        dest2 = cloner.clone_or_update("hello-world", "https://github.com/octocat/Hello-World")
        print(f"   -> path unchanged: {dest2 == dest}")
        print(f"   -> .git still exists: {os.path.isdir(os.path.join(dest2, '.git'))}")

        # 3. Attempt to clone an unreachable URL
        print("\n3. Cloning unreachable URL ...")
        try:
            cloner.clone_or_update("bad-repo", "https://invalid.example.com/no-repo.git")
        except CloneError as e:
            print(f"   -> CloneError: {e}")
            print(f"   -> partial cleanup: {not os.path.exists(os.path.join(storage_path, 'bad-repo'))}")

    print("\nDone. Temporary directory cleaned up.")


if __name__ == "__main__":
    main()
