"""Example: Content Extraction — classify and read repository files.

Demonstrates ContentExtractor walking a directory tree, classifying files
into code/doc/example/rule types, and skipping binary/oversized files.
"""

import os
import tempfile

from src.indexing.content_extractor import ContentExtractor, ContentType


def main():
    # Create a temporary repository structure
    with tempfile.TemporaryDirectory() as repo_dir:
        # Source code files
        _write(repo_dir, "src/main.py", "def main(): print('hello')")
        _write(repo_dir, "src/utils.java", "class Utils {}")

        # Documentation
        _write(repo_dir, "README.md", "# My Project\nA demo repo.")
        os.makedirs(os.path.join(repo_dir, "docs"), exist_ok=True)
        _write(repo_dir, "docs/guide.md", "# User Guide\nStep 1...")

        # Examples
        os.makedirs(os.path.join(repo_dir, "examples"), exist_ok=True)
        _write(repo_dir, "examples/basic.py", "print('basic example')")

        # Rules
        _write(repo_dir, "CONTRIBUTING.md", "# Contributing\nFork and PR.")

        # Binary (should be skipped)
        with open(os.path.join(repo_dir, "icon.png"), "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n\x00\x00")

        # Unknown type (should be skipped)
        _write(repo_dir, "Makefile", "all: build")

        # Run extraction
        extractor = ContentExtractor()
        results = extractor.extract(repo_dir)

        # Display results
        print(f"Extracted {len(results)} files:\n")
        for ef in sorted(results, key=lambda x: x.path):
            print(f"  [{ef.content_type.value:7s}] {ef.path} ({ef.size} bytes)")

        # Summary by type
        print()
        counts = {}
        for ef in results:
            counts[ef.content_type] = counts.get(ef.content_type, 0) + 1
        for ct in ContentType:
            if ct in counts:
                print(f"  {ct.value}: {counts[ct]} file(s)")

        print(f"\nSkipped: icon.png (binary), Makefile (unknown type)")


def _write(base: str, rel_path: str, content: str):
    full = os.path.join(base, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    main()
