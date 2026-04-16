"""add run scoped replay and workspace

Revision ID: f3b9c4d7e8a1
Revises: c9d83ea69bc6
Create Date: 2026-04-14 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f3b9c4d7e8a1"
down_revision: Union[str, Sequence[str], None] = "c9d83ea69bc6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tool_executions", sa.Column("run_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_tool_executions_run_id",
        "tool_executions",
        "agent_runs",
        ["run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_tool_executions_run_id_updated_at_id",
        "tool_executions",
        ["run_id", "updated_at", "id"],
        unique=False,
    )

    op.add_column("agent_runs", sa.Column("state_patch", sa.JSON(), nullable=True))
    op.add_column(
        "agent_runs", sa.Column("workspace_archive_url", sa.Text(), nullable=True)
    )
    op.add_column(
        "agent_runs", sa.Column("workspace_files_prefix", sa.Text(), nullable=True)
    )
    op.add_column(
        "agent_runs", sa.Column("workspace_manifest_key", sa.Text(), nullable=True)
    )
    op.add_column(
        "agent_runs", sa.Column("workspace_archive_key", sa.Text(), nullable=True)
    )
    op.add_column(
        "agent_runs",
        sa.Column("workspace_export_status", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agent_runs", "workspace_export_status")
    op.drop_column("agent_runs", "workspace_archive_key")
    op.drop_column("agent_runs", "workspace_manifest_key")
    op.drop_column("agent_runs", "workspace_files_prefix")
    op.drop_column("agent_runs", "workspace_archive_url")
    op.drop_column("agent_runs", "state_patch")

    op.drop_index(
        "ix_tool_executions_run_id_updated_at_id",
        table_name="tool_executions",
    )
    op.drop_constraint(
        "fk_tool_executions_run_id", "tool_executions", type_="foreignkey"
    )
    op.drop_column("tool_executions", "run_id")
