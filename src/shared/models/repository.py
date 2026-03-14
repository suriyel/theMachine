"""Repository model for Git repository metadata."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, Enum, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.db.session import Base

if TYPE_CHECKING:
    from .index_job import IndexJob
    from .code_chunk import CodeChunk


class RepoStatus(str, enum.Enum):
    """Repository indexing status."""

    REGISTERED = "registered"
    INDEXING = "indexing"
    INDEXED = "indexed"
    ERROR = "error"


class Repository(Base):
    """Git repository metadata.

    Attributes:
        id: UUID primary key
        url: Git repository URL (unique)
        name: Display name
        languages: List of target languages
        status: Current indexing status
        created_at: Record creation timestamp
        updated_at: Record update timestamp
        last_indexed_at: Timestamp of last successful indexing
    """

    __tablename__ = "repositories"
    __table_args__ = (UniqueConstraint("url", name="uq_repositories_url"),)

    # Core fields
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    languages: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    status: Mapped[RepoStatus] = mapped_column(
        Enum(RepoStatus, name="repo_status"),
        nullable=False,
        default=RepoStatus.REGISTERED,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    last_indexed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    index_jobs: Mapped[List["IndexJob"]] = relationship(
        "IndexJob",
        back_populates="repository",
        cascade="all, delete-orphan",
    )
    code_chunks: Mapped[List["CodeChunk"]] = relationship(
        "CodeChunk",
        back_populates="repository",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Repository(id={self.id}, name={self.name!r}, status={self.status.value})>"
