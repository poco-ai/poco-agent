"""add activity logs

Revision ID: b6dbbf02d4c1
Revises: f4b1d8e2c6a7
Create Date: 2026-04-16 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "b6dbbf02d4c1"
down_revision: Union[str, Sequence[str], None] = "f4b1d8e2c6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "workspaces",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )

    op.create_table(
        "activity_logs",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.String(length=255), nullable=True),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("target_type", sa.String(length=100), nullable=False),
        sa.Column("target_id", sa.String(length=255), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "CREATE INDEX ix_activity_logs_workspace_id_created_at "
        "ON activity_logs (workspace_id, created_at DESC)"
    )
    op.create_index(
        "ix_activity_logs_target_type_target_id",
        "activity_logs",
        ["target_type", "target_id"],
        unique=False,
    )
    op.create_index(op.f("ix_activity_logs_action"), "activity_logs", ["action"], unique=False)
    op.create_index(
        op.f("ix_activity_logs_actor_user_id"),
        "activity_logs",
        ["actor_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_activity_logs_target_id"),
        "activity_logs",
        ["target_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_activity_logs_target_type"),
        "activity_logs",
        ["target_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_activity_logs_workspace_id"),
        "activity_logs",
        ["workspace_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_activity_logs_workspace_id"), table_name="activity_logs")
    op.drop_index(op.f("ix_activity_logs_target_type"), table_name="activity_logs")
    op.drop_index(op.f("ix_activity_logs_target_id"), table_name="activity_logs")
    op.drop_index(op.f("ix_activity_logs_actor_user_id"), table_name="activity_logs")
    op.drop_index(op.f("ix_activity_logs_action"), table_name="activity_logs")
    op.drop_index("ix_activity_logs_target_type_target_id", table_name="activity_logs")
    op.execute("DROP INDEX ix_activity_logs_workspace_id_created_at")
    op.drop_table("activity_logs")
    op.drop_column("workspaces", "is_deleted")
