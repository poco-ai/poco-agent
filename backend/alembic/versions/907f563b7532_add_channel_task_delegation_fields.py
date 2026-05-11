"""add channel task delegation fields

Revision ID: 907f563b7532
Revises: accd5cb3b1da
Create Date: 2026-05-11 17:11:00.298006

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "907f563b7532"
down_revision: Union[str, Sequence[str], None] = "accd5cb3b1da"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "server_channel_tasks",
        sa.Column("display_number", sa.Integer(), nullable=True),
    )
    op.add_column(
        "server_channel_tasks",
        sa.Column("assignee_agent_identity_id", sa.Uuid(), nullable=True),
    )
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                row_number() OVER (
                    PARTITION BY channel_id
                    ORDER BY created_at ASC, id ASC
                ) AS display_number
            FROM server_channel_tasks
        )
        UPDATE server_channel_tasks AS task
        SET display_number = ranked.display_number
        FROM ranked
        WHERE task.id = ranked.id
        """
    )
    op.alter_column("server_channel_tasks", "display_number", nullable=False)
    op.create_index(
        op.f("ix_server_channel_tasks_assignee_agent_identity_id"),
        "server_channel_tasks",
        ["assignee_agent_identity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_server_channel_tasks_display_number"),
        "server_channel_tasks",
        ["display_number"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_server_channel_tasks_channel_display_number",
        "server_channel_tasks",
        ["channel_id", "display_number"],
    )
    op.create_check_constraint(
        "ck_server_channel_tasks_single_assignee",
        "server_channel_tasks",
        """
        num_nonnulls(
            assignee_user_id,
            assignee_preset_id,
            assignee_agent_identity_id
        ) <= 1
        """,
    )
    op.create_foreign_key(
        "fk_server_channel_tasks_assignee_agent_identity_id",
        "server_channel_tasks",
        "agent_identities",
        ["assignee_agent_identity_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_server_channel_tasks_assignee_agent_identity_id",
        "server_channel_tasks",
        type_="foreignkey",
    )
    op.drop_constraint(
        "ck_server_channel_tasks_single_assignee",
        "server_channel_tasks",
        type_="check",
    )
    op.drop_constraint(
        "uq_server_channel_tasks_channel_display_number",
        "server_channel_tasks",
        type_="unique",
    )
    op.drop_index(
        op.f("ix_server_channel_tasks_display_number"),
        table_name="server_channel_tasks",
    )
    op.drop_index(
        op.f("ix_server_channel_tasks_assignee_agent_identity_id"),
        table_name="server_channel_tasks",
    )
    op.drop_column("server_channel_tasks", "assignee_agent_identity_id")
    op.drop_column("server_channel_tasks", "display_number")
