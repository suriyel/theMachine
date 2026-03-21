"""create core tables

Revision ID: d28628c2148c
Revises:
Create Date: 2026-03-21 09:48:02.362958

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd28628c2148c'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "repository",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False, unique=True),
        sa.Column("default_branch", sa.String(), nullable=True),
        sa.Column("indexed_branch", sa.String(), nullable=True),
        sa.Column("clone_path", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("last_indexed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "index_job",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "repo_id",
            sa.Uuid(),
            sa.ForeignKey("repository.id"),
            nullable=False,
        ),
        sa.Column("branch", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("phase", sa.String(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("total_files", sa.Integer(), nullable=True),
        sa.Column("processed_files", sa.Integer(), nullable=True),
        sa.Column("chunks_indexed", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "api_key",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("key_hash", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "api_key_repo_access",
        sa.Column(
            "api_key_id",
            sa.Uuid(),
            sa.ForeignKey("api_key.id"),
            primary_key=True,
        ),
        sa.Column(
            "repo_id",
            sa.Uuid(),
            sa.ForeignKey("repository.id"),
            primary_key=True,
        ),
    )

    op.create_table(
        "query_log",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "api_key_id",
            sa.Uuid(),
            sa.ForeignKey("api_key.id"),
            nullable=True,
        ),
        sa.Column("query_text", sa.String(), nullable=False),
        sa.Column("query_type", sa.String(), nullable=True),
        sa.Column("repo_filter", sa.String(), nullable=True),
        sa.Column("language_filter", sa.String(), nullable=True),
        sa.Column("result_count", sa.Integer(), nullable=True),
        sa.Column("retrieval_ms", sa.Float(), nullable=True),
        sa.Column("rerank_ms", sa.Float(), nullable=True),
        sa.Column("total_ms", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("query_log")
    op.drop_table("api_key_repo_access")
    op.drop_table("api_key")
    op.drop_table("index_job")
    op.drop_table("repository")
