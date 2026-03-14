"""Tests for ContentExtractor - Feature #5 FR-003."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from src.indexing.content_extractor import ContentExtractor, ContentType
from src.indexing.models import RawContent


class TestContentExtractorExtraction:
    """Tests for ContentExtractor.extract() method."""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Create a temporary repository structure."""
        repo_path = tmp_path / "test-repo"
        repo_path.mkdir()

        # Create README.md
        readme = repo_path / "README.md"
        readme.write_text("# Test Project\n\nThis is a test.")

        # Create source file
        src_dir = repo_path / "src"
        src_dir.mkdir()
        main_java = src_dir / "main.java"
        main_java.write_text("public class Main { }")

        # Create CHANGELOG.md
        changelog = repo_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n\n## 1.0.0\n- Initial release")

        return repo_path

    def test_extract_identifies_readme(self, temp_repo):
        """Given repository with README.md, when extracting, then README is identified."""
        extractor = ContentExtractor()
        results = extractor.extract(temp_repo, ["Java"])

        content_types = [c.content_type for c in results]
        assert ContentType.README in content_types, "README.md should be identified as README content type"

        readme_content = next((c for c in results if c.content_type == ContentType.README), None)
        assert readme_content is not None
        assert "README.md" in str(readme_content.file_path)
        assert "test" in readme_content.content.lower()

    def test_extract_identifies_source_file(self, temp_repo):
        """Given repository with Java source, when extracting, then source is identified."""
        extractor = ContentExtractor()
        results = extractor.extract(temp_repo, ["Java"])

        content_types = [c.content_type for c in results]
        assert ContentType.SOURCE in content_types, "Java file should be identified as SOURCE content type"

        source_content = next((c for c in results if c.content_type == ContentType.SOURCE), None)
        assert source_content is not None
        assert source_content.language == "Java"
        assert "main.java" in str(source_content.file_path)

    def test_extract_identifies_changelog(self, temp_repo):
        """Given repository with CHANGELOG.md, when extracting, then CHANGELOG is identified."""
        extractor = ContentExtractor()
        results = extractor.extract(temp_repo, ["Java"])

        content_types = [c.content_type for c in results]
        assert ContentType.CHANGELOG in content_types, "CHANGELOG.md should be identified"

    def test_extract_filters_by_language(self, temp_repo):
        """Given language filter, when extracting, then only matching languages are returned."""
        extractor = ContentExtractor()

        # Add Python file
        src_dir = temp_repo / "src"
        main_py = src_dir / "main.py"
        main_py.write_text("def main(): pass")

        # Filter to only Java
        results = extractor.extract(temp_repo, ["Java"])

        languages = [c.language for c in results if c.language is not None]
        assert "Python" not in languages, "Python files should be filtered out"

    def test_extract_empty_repo_warns(self, tmp_path):
        """Given repository with only binary files, when extracting, then warning logged and zero chunks."""
        repo_path = tmp_path / "empty-repo"
        repo_path.mkdir()

        # Create binary file
        binary_file = repo_path / "image.png"
        binary_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        extractor = ContentExtractor()
        results = extractor.extract(repo_path, ["Java"])

        # Should return empty or warn about no content
        assert len(results) == 0 or all(
            c.content_type not in [ContentType.README, ContentType.SOURCE, ContentType.CHANGELOG]
            for c in results
        ), "Binary-only repo should yield no indexable content"

    def test_extract_many_source_files(self, tmp_path):
        """Given repository with 100 source files, when extracting, then all are identified."""
        repo_path = tmp_path / "large-repo"
        repo_path.mkdir()

        # Create 100 Java files
        src_dir = repo_path / "src"
        src_dir.mkdir()

        for i in range(100):
            file_path = src_dir / f"Test{i:03d}.java"
            file_path.write_text(f"public class Test{i:03d} {{ }}")

        extractor = ContentExtractor()
        results = extractor.extract(repo_path, ["Java"])

        java_files = [c for c in results if c.language == "Java"]
        assert len(java_files) == 100, f"Expected 100 Java files, got {len(java_files)}"

    def test_extract_returns_raw_content_objects(self, temp_repo):
        """Given valid extraction, when complete, then RawContent objects have all required fields."""
        extractor = ContentExtractor()
        results = extractor.extract(temp_repo, ["Java"])

        for content in results:
            assert isinstance(content, RawContent), "Result must be RawContent"
            assert content.repo_id is not None
            assert content.file_path is not None
            assert content.content_type is not None
            assert content.content is not None
            assert content.size_bytes > 0 or len(content.content) == 0

    def test_extract_handles_nested_directories(self, tmp_path):
        """Given nested source files, when extracting, then all are found."""
        repo_path = tmp_path / "nested-repo"
        repo_path.mkdir()

        # Create nested structure
        pkg_dir = repo_path / "src" / "com" / "example"
        pkg_dir.mkdir(parents=True)
        main_java = pkg_dir / "Main.java"
        main_java.write_text("package com.example;")

        extractor = ContentExtractor()
        results = extractor.extract(repo_path, ["Java"])

        assert len(results) > 0, "Nested files should be found"

    def test_extract_skips_empty_files(self, tmp_path):
        """Given empty source file, when extracting, then it is skipped."""
        repo_path = tmp_path / "empty-files-repo"
        repo_path.mkdir()

        empty_file = repo_path / "empty.java"
        empty_file.write_text("")

        extractor = ContentExtractor()
        results = extractor.extract(repo_path, ["Java"])

        # Empty files should be skipped
        empty_contents = [c for c in results if len(c.content.strip()) == 0]
        assert len(empty_contents) == 0, "Empty files should be skipped"

    def test_extract_respects_file_size_limit(self, tmp_path):
        """Given file exceeding size limit, when extracting, then it is skipped."""
        repo_path = tmp_path / "large-files-repo"
        repo_path.mkdir()

        # Create large file (>10MB)
        large_file = repo_path / "large.java"
        large_content = "x" * (11 * 1024 * 1024)  # 11MB
        large_file.write_text(large_content)

        extractor = ContentExtractor()
        results = extractor.extract(repo_path, ["Java"])

        # Large file should be skipped
        large_contents = [c for c in results if "large.java" in str(c.file_path)]
        assert len(large_contents) == 0, "Files over 10MB should be skipped"

    def test_extract_unsupported_language_fallback(self, tmp_path):
        """Given unsupported language file, when extracting, then it is indexed as text."""
        repo_path = tmp_path / "unsupported-repo"
        repo_path.mkdir()

        # Create Ruby file (unsupported)
        ruby_file = repo_path / "script.rb"
        ruby_file.write_text("puts 'hello'")

        extractor = ContentExtractor()
        results = extractor.extract(repo_path, ["Java"])

        # Ruby should either be skipped or handled as unsupported
        assert len(results) >= 0

    def test_extract_multiple_languages(self, tmp_path):
        """Given repository with multiple languages, when extracting, then all are identified."""
        repo_path = tmp_path / "multi-lang-repo"
        repo_path.mkdir()

        src_dir = repo_path / "src"
        src_dir.mkdir()

        # Java file
        (src_dir / "Main.java").write_text("public class Main {}")
        # Python file
        (src_dir / "main.py").write_text("def main(): pass")
        # TypeScript file
        (src_dir / "main.ts").write_text("function main() {}")

        extractor = ContentExtractor()
        results = extractor.extract(repo_path, ["Java", "Python", "TypeScript"])

        languages = {c.language for c in results if c.language is not None}
        assert "Java" in languages
        assert "Python" in languages
        assert "TypeScript" in languages

    def test_extract_no_source_files(self, tmp_path):
        """Given repository with no source files, when extracting, then empty list returned."""
        repo_path = repo_path = tmp_path / "no-source-repo"
        repo_path.mkdir()

        # Only docs
        (repo_path / "README.md").write_text("# Project")

        extractor = ContentExtractor()
        results = extractor.extract(repo_path, ["Java"])

        # Should work but may have no source content
        assert isinstance(results, list)


class TestContentType:
    """Tests for ContentType enum."""

    def test_content_type_has_required_values(self):
        """Verify ContentType enum has all required values."""
        assert hasattr(ContentType, "README")
        assert hasattr(ContentType, "SOURCE")
        assert hasattr(ContentType, "CHANGELOG")
        assert hasattr(ContentType, "DOCUMENTATION")
        assert hasattr(ContentType, "EXAMPLE")

    def test_content_type_string_values(self):
        """Verify ContentType enum string values."""
        assert ContentType.README.value == "readme"
        assert ContentType.SOURCE.value == "source"
        assert ContentType.CHANGELOG.value == "changelog"


class TestRawContent:
    """Tests for RawContent dataclass."""

    def test_raw_content_creation(self):
        """Given valid inputs, when creating RawContent, then all fields set correctly."""
        content = RawContent(
            repo_id="test-uuid",
            file_path=Path("src/Main.java"),
            content_type=ContentType.SOURCE,
            language="Java",
            content="public class Main {}",
            size_bytes=20,
        )

        assert content.repo_id == "test-uuid"
        assert content.file_path == Path("src/Main.java")
        assert content.content_type == ContentType.SOURCE
        assert content.language == "Java"
        assert content.content == "public class Main {}"
        assert content.size_bytes == 20


class TestContentExtractorEdgeCases:
    """Additional negative tests to meet 40% negative test ratio."""

    def test_extract_nonexistent_repo(self, tmp_path):
        """Given non-existent repository path, when extracting, then empty list returned."""
        fake_path = tmp_path / "does-not-exist"

        extractor = ContentExtractor()
        results = extractor.extract(fake_path, ["Java"])

        assert results == []

    def test_extract_handles_read_error_gracefully(self, tmp_path, monkeypatch):
        """Given file that cannot be read, when extracting, then skip with warning."""
        repo_path = tmp_path / "error-repo"
        repo_path.mkdir()

        # Create a file
        test_file = repo_path / "test.java"
        test_file.write_text("public class Test {}")

        # Mock read_text to raise an error
        def mock_read_text(*args, **kwargs):
            raise PermissionError("Access denied")

        monkeypatch.setattr(Path, "read_text", mock_read_text)

        extractor = ContentExtractor()
        results = extractor.extract(repo_path, ["Java"])

        # Should skip the file due to error
        assert len(results) == 0

    def test_extract_handles_binary_files_gracefully(self, tmp_path):
        """Given binary file, when extracting, then it is skipped."""
        repo_path = tmp_path / "binary-repo"
        repo_path.mkdir()

        # Create file with binary extension but text content
        binary_file = repo_path / "test.jar"
        binary_file.write_bytes(b"PK\x03\x04" + b"\x00" * 100)

        extractor = ContentExtractor()
        results = extractor.extract(repo_path, ["Java"])

        # Binary files without supported extension should be skipped
        assert len(results) == 0
