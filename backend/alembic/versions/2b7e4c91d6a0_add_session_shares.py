"""add session shares

Revision ID: 2b7e4c91d6a0
Revises: b21386d7517c
Create Date: 2026-06-09 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2b7e4c91d6a0"
down_revision: Union[str, Sequence[str], None] = "b21386d7517c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "session_shares",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("source_session_id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.String(length=255), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_revoked",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_session_id"],
            ["agent_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index(
        op.f("ix_session_shares_owner_user_id"),
        "session_shares",
        ["owner_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_session_shares_owner_user_id_created_at",
        "session_shares",
        ["owner_user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_session_shares_source_session_id"),
        "session_shares",
        ["source_session_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_session_shares_source_session_id"),
        table_name="session_shares",
    )
    op.drop_index(
        "ix_session_shares_owner_user_id_created_at",
        table_name="session_shares",
    )
    op.drop_index(
        op.f("ix_session_shares_owner_user_id"),
        table_name="session_shares",
    )
    op.drop_table("session_shares")
