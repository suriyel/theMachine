"""QueryLog model for query auditing and analytics."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.db.session import Base

if TYPE_CHECKING:
    from .api_key import APIKey


class QueryType(str, enum.Enum):
    """Query type classification."""

    NATURAL_LANGUAGE = "natural_language"
    SYMBOL = "symbol"


class QueryLog(Base):
    """Query execution log for auditing and analytics.

    Attributes:
        id: UUID primary key
        api_key_id: Foreign key to APIKey (nullable for anonymous queries)
        query_text: The submitted query text
        query_type: Query classification (natural language or symbol)
        repo_filter: Optional repository filter
        language_filter: Optional programming language filter
        result_count: Number of results returned
        latency_ms: Query execution time in milliseconds
        correlation_id: UUID for distributed tracing
        created_at: Timestamp when query was executed
    """

    __tablename__ = "query_logs"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Foreign key (nullable for anonymous queries)
    api_key_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("api_keys.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Query details
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    query_type: Mapped[QueryType] = mapped_column(
        Enum(QueryType, name="query_type"),
        nullable=False,
    )

    # Filters
    repo_filter: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    language_filter: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Results
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)

    # Tracing
    correlation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        default=uuid.uuid4,
        index=True,
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    # Relationships
    api_key: Mapped[Optional["APIKey"]] = relationship(
        "APIKey",
        back_populates="query_logs",
    )

    def __repr__(self) -> str:
        return f"<QueryLog(id={self.id}, type={self.query_type.value}, latency={self.latency_ms}ms)>"
