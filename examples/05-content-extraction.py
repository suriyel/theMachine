"""Example: Content Extraction - Feature #5 FR-003

This example demonstrates how to use the ContentExtractor to extract
indexable content from a cloned Git repository.

Run: python examples/05-content-extraction.py
"""

import tempfile
from pathlib import Path

from src.indexing.content_extractor import ContentExtractor


def main():
    """Demonstrate content extraction from a repository."""
    print("=" * 60)
    print("Content Extraction Example - Feature #5 FR-003")
    print("=" * 60)

    # Create a temporary repository structure
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_path = Path(tmp_dir) / "test-repo"
        repo_path.mkdir()

        # Create README.md
        readme = repo_path / "README.md"
        readme.write_text("""# Test Project

This is a test repository for demonstrating content extraction.

## Features
- Feature 1
- Feature 2
""")

        # Create source files
        src_dir = repo_path / "src"
        src_dir.mkdir()

        main_java = src_dir / "Main.java"
        main_java.write_text("""package com.example;

public class Main {
    public static void main(String[] args) {
        System.out.println("Hello World");
    }
}
""")

        util_java = src_dir / "Util.java"
        util_java.write_text("""package com.example;

public class Util {
    public static String format(String input) {
        return input.trim();
    }
}
""")

        # Create CHANGELOG.md
        changelog = repo_path / "CHANGELOG.md"
        changelog.write_text("""# Changelog

## [1.0.0] - 2024-01-01
- Initial release
- Added Main class
- Added Util class
""")

        # Create Python file
        main_py = src_dir / "main.py"
        main_py.write_text("""def main():
    print('Hello from Python')

if __name__ == '__main__':
    main()
""")

        # Extract content
        print(f"\nRepository path: {repo_path}")
        print("\nExtracting content...")

        extractor = ContentExtractor()
        results = extractor.extract(repo_path, languages=["Java", "Python"])

        print(f"\nExtracted {len(results)} content items:\n")

        # Display results
        for i, content in enumerate(results, 1):
            print(f"{i}. {content.file_path}")
            print(f"   Type: {content.content_type.value}")
            print(f"   Language: {content.language}")
            print(f"   Size: {content.size_bytes} bytes")
            # Show first 50 chars of content
            preview = content.content[:50].replace('\n', ' ')
            print(f"   Preview: {preview}...")
            print()

        # Filter by content type
        print("\n--- Content Type Summary ---")
        source_files = [c for c in results if c.content_type.value == "source"]
        readme_files = [c for c in results if c.content_type.value == "readme"]
        changelog_files = [c for c in results if c.content_type.value == "changelog"]

        print(f"Source files: {len(source_files)}")
        print(f"README files: {len(readme_files)}")
        print(f"CHANGELOG files: {len(changelog_files)}")

        # Filter by language
        print("\n--- Language Summary ---")
        java_files = [c for c in results if c.language == "Java"]
        python_files = [c for c in results if c.language == "Python"]

        print(f"Java files: {len(java_files)}")
        print(f"Python files: {len(python_files)}")

        print("\n" + "=" * 60)
        print("Content extraction complete!")
        print("=" * 60)


if __name__ == "__main__":
    main()
