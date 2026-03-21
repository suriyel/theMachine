"""Repository model — tracks registered Git repositories."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.models.base import Base


class Repository(Base):
    """A registered Git repository for indexing."""

    __tablename__ = "repository"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    default_branch: Mapped[str | None] = mapped_column(String, nullable=True)
    indexed_branch: Mapped[str | None] = mapped_column(String, nullable=True)
    clone_path: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    last_indexed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.now()
    )

    def __init__(self, **kwargs: object) -> None:
        if "status" not in kwargs:
            kwargs["status"] = "pending"
        super().__init__(**kwargs)
