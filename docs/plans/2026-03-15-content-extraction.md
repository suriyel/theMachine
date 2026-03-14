# Implementation Plan — Feature #5: Content Extraction (FR-003)

**Date**: 2026-03-15
**Feature**: Content Extraction (FR-003)
**Status**: Planning

## 1. Overview

This feature identifies and extracts indexable content from cloned repositories including:
- Documentation files (README.md, CHANGELOG.md, CONTRIBUTING.md, etc.)
- Source code files (.java, .py, .ts, .js, .c, .cpp)
- Release notes and example files

The ContentExtractor class will be added to `src/indexing/content_extractor.py`.

## 2. Design Reference

From `docs/plans/2026-03-14-code-context-retrieval-design.md` Section 4.1:

```python
class ContentExtractor:
    -supported_extensions: dict[str, str]
    +extract(repo_path: Path, languages: list[str]): list[RawContent]
    -_classify_file(path: Path): ContentType
```

## 3. Implementation Details

### 3.1 New Files

| File | Purpose |
|------|---------|
| `src/indexing/content_extractor.py` | ContentExtractor class |
| `src/indexing/models.py` | RawContent dataclass |
| `tests/test_content_extractor.py` | Unit tests |
| `examples/05-content-extraction.py` | Usage example |

### 3.2 Data Structures

```python
# src/indexing/models.py
from dataclasses import dataclass
from pathlib import Path
from enum import Enum

class ContentType(str, Enum):
    README = "readme"
    SOURCE = "source"
    CHANGELOG = "changelog"
    DOCUMENTATION = "documentation"
    EXAMPLE = "example"

@dataclass
class RawContent:
    """Raw content extracted from a file for chunking."""
    repo_id: str
    file_path: Path
    content_type: ContentType
    language: str | None
    content: str
    size_bytes: int
```

### 3.3 ContentExtractor Class

```python
class ContentExtractor:
    """Extract indexable content from cloned repositories."""

    # File extensions mapped to languages
    SUPPORTED_EXTENSIONS = {
        ".java": "Java",
        ".py": "Python",
        ".ts": "TypeScript",
        ".js": "JavaScript",
        ".c": "C",
        ".cpp": "C++",
    }

    # Documentation file patterns
    README_PATTERNS = [
        "README.md", "README.rst", "README.txt", "README",
        "README.MD", "README.RST", "README.TXT",
    ]

    CHANGELOG_PATTERNS = [
        "CHANGELOG.md", "CHANGELOG.rst", "CHANGELOG.txt", "CHANGELOG",
        "CHANGES.md", "CHANGES.rst", "HISTORY.md", "HISTORY.rst",
    ]

    def __init__(self):
        """Initialize ContentExtractor."""
        pass

    def extract(
        self,
        repo_path: Path,
        languages: list[str]
    ) -> list[RawContent]:
        """Extract all indexable content from repository.

        Args:
            repo_path: Path to cloned repository
            languages: List of target languages to filter

        Returns:
            List of RawContent objects
        """
        pass
```

### 3.4 Implementation Steps

1. **Create models** — Add `RawContent` dataclass and `ContentType` enum
2. **Implement ContentExtractor** — Add `extract()` method with file discovery
3. **Implement `_classify_file()`** — Classify files by type (README, source, etc.)
4. **Add file reading** — Read file content with encoding handling
5. **Add logging** — Log warnings for unsupported files
6. **Write unit tests** — Test classification, extraction, edge cases
7. **Write example** — Demonstrate usage

## 4. Verification Steps

From `feature-list.json`:

1. Given a cloned repository with README.md, src/main.java, and CHANGELOG.md, when content extraction runs, then all three content types are identified and queued for chunking
2. Given a cloned repository with only binary files, when content extraction runs, then warning is logged and job completes with zero chunks
3. Given a cloned repository with 100 source files, when content extraction runs, then all 100 files are identified by language extension

## 5. Quality Gates

- Line coverage >= 90%
- Branch coverage >= 80%
- Negative test ratio >= 40%
- Low-value assertion ratio <= 20%

## 6. Dependencies

- Feature #4 (Git Clone or Update) — Must complete first (already passing)

## 7. Notes

- Binary files should be skipped with a warning
- Empty files should be skipped
- Encoding errors should be handled gracefully
- File size limit: skip files > 10MB
