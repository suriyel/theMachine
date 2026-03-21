"""QueryLog model — tracks query audit trail."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.models.base import Base


class QueryLog(Base):
    """A log entry for a query executed against the system."""

    __tablename__ = "query_log"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("api_key.id"), nullable=True
    )
    query_text: Mapped[str] = mapped_column(String, nullable=False)
    query_type: Mapped[str | None] = mapped_column(String, nullable=True)
    repo_filter: Mapped[str | None] = mapped_column(String, nullable=True)
    language_filter: Mapped[str | None] = mapped_column(String, nullable=True)
    result_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retrieval_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    rerank_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.now()
    )
