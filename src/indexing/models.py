"""Data models for the indexing module."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ContentType(str, Enum):
    """Type of content extracted from a file."""

    README = "readme"
    SOURCE = "source"
    CHANGELOG = "changelog"
    DOCUMENTATION = "documentation"
    EXAMPLE = "example"


@dataclass
class RawContent:
    """Raw content extracted from a file for chunking.

    Attributes:
        repo_id: Repository UUID
        file_path: Path to the file
        content_type: Type of content
        language: Programming language (None for docs)
        content: File content as string
        size_bytes: Size of content in bytes
    """

    repo_id: str
    file_path: Path
    content_type: ContentType
    language: str | None
    content: str
    size_bytes: int = field(default=0)

    def __post_init__(self):
        if self.size_bytes == 0:
            self.size_bytes = len(self.content.encode("utf-8"))
