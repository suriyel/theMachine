"""IndexJob model — tracks indexing job lifecycle."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.models.base import Base


class IndexJob(Base):
    """An indexing job for a repository."""

    __tablename__ = "index_job"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    repo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("repository.id"), nullable=False
    )
    branch: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    phase: Mapped[str | None] = mapped_column(String, nullable=True, default="queued")
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    total_files: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processed_files: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunks_indexed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def __init__(self, **kwargs: object) -> None:
        if "status" not in kwargs:
            kwargs["status"] = "pending"
        if "phase" not in kwargs:
            kwargs["phase"] = "queued"
        super().__init__(**kwargs)
