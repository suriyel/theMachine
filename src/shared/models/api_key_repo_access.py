"""ApiKeyRepoAccess model — maps API keys to repositories."""

import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.models.base import Base


class ApiKeyRepoAccess(Base):
    """Associates an API key with a repository for scoped access."""

    __tablename__ = "api_key_repo_access"

    api_key_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("api_key.id"), primary_key=True
    )
    repo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("repository.id"), primary_key=True
    )
