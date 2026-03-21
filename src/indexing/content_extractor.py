"""Content Extraction — classifies and reads repository files."""

import enum
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 1_048_576  # 1 MB

SUPPORTED_CODE_EXTENSIONS = {".py", ".java", ".js", ".ts", ".c", ".cpp"}

DOC_FILENAMES = {"readme.md", "changelog.md"}

DOC_EXTENSIONS = {".md", ".rst"}

RULE_FILENAMES = {"claude.md", "contributing.md", ".editorconfig"}

EXAMPLE_SUFFIXES = ("_example.", "_demo.")


class ContentType(enum.Enum):
    """Classification of a repository file."""

    CODE = "code"
    DOC = "doc"
    EXAMPLE = "example"
    RULE = "rule"
    UNKNOWN = "unknown"


@dataclass
class ExtractedFile:
    """A file extracted from a repository with its classification and content."""

    path: str
    content_type: ContentType
    content: str
    size: int


class ContentExtractor:
    """Walks a cloned repository, classifies files, and reads text content."""

    def extract(self, repo_path: str) -> list[ExtractedFile]:
        """Extract all classifiable, readable, non-binary files from repo_path."""
        results: list[ExtractedFile] = []

        for root, dirs, files in os.walk(repo_path):
            # Skip hidden directories (.git, .svn, etc.) but keep .cursor
            dirs[:] = [
                d for d in dirs if not d.startswith(".") or d == ".cursor"
            ]

            for filename in files:
                abs_path = os.path.join(root, filename)
                rel_path = os.path.relpath(abs_path, repo_path)

                content_type = self._classify_file(rel_path)
                if content_type == ContentType.UNKNOWN:
                    continue

                try:
                    file_size = os.path.getsize(abs_path)
                except OSError as exc:
                    logger.warning(
                        "Skipping unreadable file: %s (%s)", rel_path, exc
                    )
                    continue

                if file_size > MAX_FILE_SIZE:
                    logger.warning(
                        "Skipping oversized file: %s (%d bytes)",
                        rel_path,
                        file_size,
                    )
                    continue

                if self._is_binary(abs_path):
                    logger.warning("Skipping binary file: %s", rel_path)
                    continue

                try:
                    with open(abs_path, encoding="utf-8") as f:
                        content = f.read()
                except (UnicodeDecodeError, IOError, OSError) as exc:
                    logger.warning(
                        "Skipping unreadable file: %s (%s)", rel_path, exc
                    )
                    continue

                results.append(
                    ExtractedFile(
                        path=rel_path,
                        content_type=content_type,
                        content=content,
                        size=file_size,
                    )
                )

        return results

    def _classify_file(self, rel_path: str) -> ContentType:
        """Classify a file by its path and extension.

        Priority: rule > example > doc > code > unknown.
        """
        # Normalize path separators for matching
        normalized = rel_path.replace(os.sep, "/")
        filename = os.path.basename(rel_path)
        filename_lower = filename.lower()
        _, ext = os.path.splitext(filename_lower)

        # 1. Rule patterns (most specific)
        if filename_lower in RULE_FILENAMES:
            return ContentType.RULE
        if normalized.replace(os.sep, "/").startswith(".cursor/rules/"):
            return ContentType.RULE

        # 2. Example patterns
        if normalized.startswith("examples/"):
            return ContentType.EXAMPLE
        for suffix in EXAMPLE_SUFFIXES:
            if suffix in filename_lower:
                return ContentType.EXAMPLE

        # 3. Documentation patterns
        if filename_lower in DOC_FILENAMES:
            return ContentType.DOC
        if normalized.startswith("docs/") and ext in DOC_EXTENSIONS:
            return ContentType.DOC
        if filename_lower.startswith("release") and ext == ".md":
            return ContentType.DOC
        if ext in DOC_EXTENSIONS:
            return ContentType.DOC

        # 4. Source code patterns
        if ext in SUPPORTED_CODE_EXTENSIONS:
            return ContentType.CODE

        # 5. Unknown
        return ContentType.UNKNOWN

    def _is_binary(self, file_path: str) -> bool:
        """Check if a file is binary by looking for null bytes in first 8KB."""
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(8192)
            return b"\x00" in chunk
        except (IOError, OSError):
            return False
