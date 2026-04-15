"""add agent assignments

Revision ID: 3b7f9c2d4e11
Revises: c8a7d5e9f012
Create Date: 2026-04-16 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "3b7f9c2d4e11"
down_revision: str | Sequence[str] | None = "c8a7d5e9f012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "presets",
        sa.Column(
            "container_mode",
            sa.String(length=50),
            nullable=False,
            server_default="ephemeral",
        ),
    )

    op.create_table(
        "agent_assignments",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("issue_id", sa.UUID(), nullable=False),
        sa.Column("preset_id", sa.Integer(), nullable=False),
        sa.Column("trigger_mode", sa.String(length=50), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=True),
        sa.Column("container_id", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("schedule_cron", sa.String(length=100), nullable=True),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["issue_id"], ["workspace_issues.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["preset_id"], ["presets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["session_id"], ["agent_sessions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("issue_id", name="uq_agent_assignments_issue_id"),
    )
    op.create_index(
        "ix_agent_assignments_workspace_status",
        "agent_assignments",
        ["workspace_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_agent_assignments_trigger_mode_status",
        "agent_assignments",
        ["trigger_mode", "status"],
        unique=False,
    )
    op.create_index(
        "ix_agent_assignments_session_id",
        "agent_assignments",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_agent_assignments_session_id", table_name="agent_assignments")
    op.drop_index(
        "ix_agent_assignments_trigger_mode_status", table_name="agent_assignments"
    )
    op.drop_index("ix_agent_assignments_workspace_status", table_name="agent_assignments")
    op.drop_table("agent_assignments")
    op.drop_column("presets", "container_mode")
