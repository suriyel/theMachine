"""APIKey model for API authentication."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.db.session import Base

if TYPE_CHECKING:
    from .query_log import QueryLog


class KeyStatus(str, enum.Enum):
    """API key status."""

    ACTIVE = "active"
    REVOKED = "revoked"


class APIKey(Base):
    """API key for authentication.

    Stores hashed API keys (not plaintext) for secure authentication.

    Attributes:
        id: UUID primary key
        key_hash: SHA-256 hash of the API key
        name: Human-readable key description
        status: Current key status
        created_at: Record creation timestamp
        revoked_at: Timestamp when key was revoked
    """

    __tablename__ = "api_keys"
    __table_args__ = {"extend_existing": True}

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Core fields
    key_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[KeyStatus] = mapped_column(
        Enum(KeyStatus, name="key_status"),
        nullable=False,
        default=KeyStatus.ACTIVE,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    query_logs: Mapped[list["QueryLog"]] = relationship(
        "QueryLog",
        back_populates="api_key",
        cascade="all, delete-orphan",
    )

    def revoke(self) -> None:
        """Revoke this API key."""
        self.status = KeyStatus.REVOKED
        self.revoked_at = datetime.utcnow()

    def is_active(self) -> bool:
        """Check if this key is active."""
        return self.status == KeyStatus.ACTIVE

    def __repr__(self) -> str:
        return f"<APIKey(id={self.id}, name={self.name!r}, status={self.status.value})>"
