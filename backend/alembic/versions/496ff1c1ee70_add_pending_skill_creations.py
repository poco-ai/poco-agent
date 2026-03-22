"""add pending skill creations

Revision ID: 496ff1c1ee70
Revises: merge_heads
Create Date: 2026-03-15 11:36:11.858816

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "496ff1c1ee70"
down_revision: Union[str, Sequence[str], None] = "merge_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "pending_skill_creations",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("tool_use_id", sa.String(length=255), nullable=True),
        sa.Column("detected_name", sa.String(length=255), nullable=False),
        sa.Column("resolved_name", sa.String(length=255), nullable=True),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("workspace_files_prefix", sa.Text(), nullable=True),
        sa.Column("skill_relative_path", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=50),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("skill_id", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
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
            ["session_id"], ["agent_sessions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id",
            "skill_relative_path",
            name="uq_pending_skill_creations_session_skill_path",
        ),
    )
    op.create_index(
        op.f("ix_pending_skill_creations_session_id"),
        "pending_skill_creations",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_pending_skill_creations_status"),
        "pending_skill_creations",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_pending_skill_creations_user_id"),
        "pending_skill_creations",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_pending_skill_creations_user_id_status_created_at",
        "pending_skill_creations",
        ["user_id", "status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_pending_skill_creations_user_id_status_created_at",
        table_name="pending_skill_creations",
    )
    op.drop_index(
        op.f("ix_pending_skill_creations_user_id"), table_name="pending_skill_creations"
    )
    op.drop_index(
        op.f("ix_pending_skill_creations_status"), table_name="pending_skill_creations"
    )
    op.drop_index(
        op.f("ix_pending_skill_creations_session_id"),
        table_name="pending_skill_creations",
    )
    op.drop_table("pending_skill_creations")
