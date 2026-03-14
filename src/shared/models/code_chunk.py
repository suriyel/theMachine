"""CodeChunk model for storing indexed code segments."""

import enum
import hashlib
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.db.session import Base

if TYPE_CHECKING:
    from .repository import Repository


class ChunkGranularity(str, enum.Enum):
    """Code chunk granularity level."""

    FILE = "file"
    CLASS = "class"
    FUNCTION = "function"
    SYMBOL = "symbol"


class CodeChunk(Base):
    """Indexed code chunk for retrieval.

    The primary key is a composite string: "repo_id:file_path:symbol_hash"
    This enables efficient lookups and prevents duplicates.

    Attributes:
        id: Composite string primary key
        repo_id: Foreign key to Repository
        file_path: Path to the source file
        language: Programming language
        granularity: Chunk granularity level
        symbol_name: Symbol identifier (nullable for file-level chunks)
        content: Actual code content
        start_line: Starting line number
        end_line: Ending line number
        indexed_at: When this chunk was indexed
    """

    __tablename__ = "code_chunks"

    # Composite primary key
    id: Mapped[str] = mapped_column(String(512), primary_key=True)

    # Foreign key
    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # File and symbol info
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    granularity: Mapped[ChunkGranularity] = mapped_column(
        Enum(ChunkGranularity, name="chunk_granularity"),
        nullable=False,
    )
    symbol_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Content and location
    content: Mapped[str] = mapped_column(Text, nullable=False)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)

    # Indexing timestamp
    indexed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    # Relationships
    repository: Mapped["Repository"] = relationship(
        "Repository",
        back_populates="code_chunks",
    )

    @classmethod
    def generate_id(
        cls,
        repo_id: uuid.UUID,
        file_path: str,
        symbol_name: Optional[str] = None,
    ) -> str:
        """Generate composite ID for a code chunk.

        Format: "repo_id:file_path:symbol_hash"
        """
        symbol_hash = (
            hashlib.sha256(symbol_name.encode()).hexdigest()[:16]
            if symbol_name
            else "nosymbol"
        )
        return f"{repo_id}:{file_path}:{symbol_hash}"

    def __repr__(self) -> str:
        return f"<CodeChunk(id={self.id[:50]}..., language={self.language})>"
