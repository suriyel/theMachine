"""IndexJob model for tracking repository indexing jobs."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.db.session import Base

if TYPE_CHECKING:
    from .repository import Repository


class JobStatus(str, enum.Enum):
    """Indexing job status."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TriggerType(str, enum.Enum):
    """Job trigger type."""

    SCHEDULED = "scheduled"
    MANUAL = "manual"


class IndexJob(Base):
    """Repository indexing job tracking.

    Attributes:
        id: UUID primary key
        repo_id: Foreign key to Repository
        status: Current job status
        trigger_type: How the job was triggered
        started_at: When the job started processing
        completed_at: When the job finished
        error_message: Error details if failed
        chunk_count: Number of chunks indexed
    """

    __tablename__ = "index_jobs"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Foreign key
    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Status fields
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"),
        nullable=False,
        default=JobStatus.QUEUED,
    )
    trigger_type: Mapped[TriggerType] = mapped_column(
        Enum(TriggerType, name="trigger_type"),
        nullable=False,
    )

    # Timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Result fields
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    repository: Mapped["Repository"] = relationship(
        "Repository",
        back_populates="index_jobs",
    )

    def __repr__(self) -> str:
        return f"<IndexJob(id={self.id}, repo_id={self.repo_id}, status={self.status.value})>"
