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


class ChunkType(str, Enum):
    """Type of code chunk."""

    FILE = "file"
    CLASS = "class"
    FUNCTION = "function"
    INTERFACE = "interface"
    TYPE = "type"


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


@dataclass
class CodeChunk:
    """A chunk of code at a specific granularity level.

    Attributes:
        repo_id: Repository UUID
        file_path: Path to the source file
        chunk_type: Granularity level (file, class, function, interface, type)
        symbol_name: Name of the symbol (class, function, etc.) if applicable
        symbol_type: Type of symbol (class, function, interface, type)
        start_line: Starting line number (1-indexed)
        end_line: Ending line number (1-indexed)
        content: The actual code content of the chunk
    """

    repo_id: str
    file_path: Path
    chunk_type: ChunkType
    symbol_name: str | None = None
    symbol_type: str | None = None
    start_line: int = 1
    end_line: int = 1
    content: str = ""
