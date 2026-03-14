"""ContentExtractor - Extract indexable content from cloned repositories."""

import logging
from pathlib import Path
from typing import Optional

from src.indexing.models import ContentType, RawContent

logger = logging.getLogger(__name__)

# File extensions mapped to languages
SUPPORTED_EXTENSIONS = {
    ".java": "Java",
    ".py": "Python",
    ".ts": "TypeScript",
    ".js": "JavaScript",
    ".c": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".h": "C",
    ".hpp": "C++",
}

# Documentation file patterns
README_PATTERNS = [
    "README.md",
    "README.rst",
    "README.txt",
    "README",
    "README.MD",
    "README.RST",
    "README.TXT",
]

CHANGELOG_PATTERNS = [
    "CHANGELOG.md",
    "CHANGELOG.rst",
    "CHANGELOG.txt",
    "CHANGELOG",
    "CHANGES.md",
    "CHANGES.rst",
    "HISTORY.md",
    "HISTORY.rst",
]

DOCUMENTATION_PATTERNS = [
    "CONTRIBUTING.md",
    "CONTRIBUTING.rst",
    "LICENSE",
    "LICENSE.md",
    "INSTALL.md",
    "SETUP.md",
    "QUICKSTART.md",
    "DOCS.md",
    "DOCUMENTATION.md",
]

EXAMPLE_PATTERNS = [
    "examples",
    "example",
    "samples",
    "sample",
]

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class ContentExtractor:
    """Extract indexable content from cloned repositories.

    This class identifies and extracts content from repositories including:
    - Documentation files (README, CHANGELOG, CONTRIBUTING, etc.)
    - Source code files (.java, .py, .ts, .js, .c, .cpp)
    - Example files and release notes

    Attributes:
        max_file_size: Maximum file size to process (default 10MB)
    """

    def __init__(self, max_file_size: int = MAX_FILE_SIZE):
        """Initialize ContentExtractor.

        Args:
            max_file_size: Maximum file size in bytes to process
        """
        self.max_file_size = max_file_size

    def extract(
        self,
        repo_path: Path,
        languages: list[str],
        repo_id: Optional[str] = None,
    ) -> list[RawContent]:
        """Extract all indexable content from repository.

        Args:
            repo_path: Path to cloned repository
            languages: List of target languages to filter
            repo_id: Repository UUID (optional, defaults to repo name)

        Returns:
            List of RawContent objects
        """
        if not repo_path.exists():
            logger.warning(f"Repository path does not exist: {repo_path}")
            return []

        if repo_id is None:
            repo_id = repo_path.name

        results: list[RawContent] = []

        # Walk the directory tree
        for file_path in repo_path.rglob("*"):
            if not file_path.is_file():
                continue

            # Skip hidden files and directories
            if any(part.startswith(".") for part in file_path.parts):
                continue

            # Skip node_modules, __pycache__, etc.
            skip_dirs = {"node_modules", "__pycache__", ".git", "venv", ".venv", "dist", "build", "target"}
            if any(skip_dir in file_path.parts for skip_dir in skip_dirs):
                continue

            # Determine content type
            content_type = self._classify_file(file_path)

            if content_type is None:
                continue

            # Determine language
            language = self._get_language(file_path)

            # Filter by language if specified
            if languages and language is not None and language not in languages:
                continue

            # Read content
            try:
                content = self._read_file(file_path)
                if content is None:
                    continue
            except Exception as e:
                logger.warning(f"Failed to read {file_path}: {e}")
                continue

            # Skip empty files
            if not content.strip():
                logger.debug(f"Skipping empty file: {file_path}")
                continue

            # Create RawContent
            raw_content = RawContent(
                repo_id=str(repo_id),
                file_path=file_path.relative_to(repo_path),
                content_type=content_type,
                language=language,
                content=content,
            )
            results.append(raw_content)

        logger.info(f"Extracted {len(results)} content items from {repo_path}")
        return results

    def _classify_file(self, file_path: Path) -> Optional[ContentType]:
        """Classify a file by its path.

        Args:
            file_path: Path to the file

        Returns:
            ContentType or None if not indexable
        """
        name = file_path.name
        stem = file_path.stem
        suffix = file_path.suffix.lower()

        # Check for README
        if name in README_PATTERNS or stem.upper().startswith("README"):
            return ContentType.README

        # Check for CHANGELOG
        if name in CHANGELOG_PATTERNS or stem.upper().startswith("CHANGELOG"):
            return ContentType.CHANGELOG

        # Check for documentation
        if name in DOCUMENTATION_PATTERNS or stem.upper() in ["LICENSE", "CONTRIBUTING"]:
            return ContentType.DOCUMENTATION

        # Check for examples directory/file
        parent_name = file_path.parent.name
        if parent_name in EXAMPLE_PATTERNS:
            return ContentType.EXAMPLE

        # Check for supported source extensions
        if suffix in SUPPORTED_EXTENSIONS:
            return ContentType.SOURCE

        # Not indexable
        return None

    def _get_language(self, file_path: Path) -> Optional[str]:
        """Get the programming language for a file.

        Args:
            file_path: Path to the file

        Returns:
            Language string or None for non-source files
        """
        suffix = file_path.suffix.lower()
        return SUPPORTED_EXTENSIONS.get(suffix)

    def _read_file(self, file_path: Path) -> Optional[str]:
        """Read file content with encoding handling.

        Args:
            file_path: Path to the file

        Returns:
            File content as string or None if cannot read
        """
        try:
            # Check file size
            size = file_path.stat().st_size
            if size > self.max_file_size:
                logger.warning(f"File exceeds size limit ({size} > {self.max_file_size}): {file_path}")
                return None

            # Try UTF-8 first
            try:
                return file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                # Try other common encodings
                for encoding in ["latin-1", "cp1252", "iso-8859-1"]:
                    try:
                        return file_path.read_text(encoding=encoding)
                    except UnicodeDecodeError:
                        continue

                logger.warning(f"Could not decode file (tried utf-8, latin-1, cp1252): {file_path}")
                return None

        except Exception as e:
            logger.warning(f"Failed to read file {file_path}: {e}")
            return None
