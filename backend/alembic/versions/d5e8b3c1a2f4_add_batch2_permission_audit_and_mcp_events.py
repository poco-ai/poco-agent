"""Add batch2 permission audit and mcp events

Revision ID: d5e8b3c1a2f4
Revises: c8a7d1d2e3f4
Create Date: 2026-04-02
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "d5e8b3c1a2f4"
down_revision: Union[str, None] = "c8a7d1d2e3f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "permission_audit_events",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("tool_name", sa.String(128), nullable=False),
        sa.Column("tool_input", sa.JSON(), nullable=True),
        sa.Column("policy_action", sa.String(16), nullable=False),
        sa.Column("policy_rule_id", sa.String(128), nullable=True),
        sa.Column("policy_reason", sa.Text(), nullable=True),
        sa.Column("audit_mode", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("context", sa.JSON(), nullable=True),
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
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_permission_audit_events_run_id",
        "permission_audit_events",
        ["run_id"],
    )
    op.create_index(
        "ix_permission_audit_events_session_id",
        "permission_audit_events",
        ["session_id"],
    )

    op.create_table(
        "agent_run_mcp_connection_events",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "connection_id",
            sa.UUID(),
            sa.ForeignKey("agent_run_mcp_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("from_state", sa.String(32), nullable=True),
        sa.Column("to_state", sa.String(32), nullable=False),
        sa.Column("event_source", sa.String(32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
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
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_mcp_connection_events_connection_id",
        "agent_run_mcp_connection_events",
        ["connection_id"],
    )
    op.create_index(
        "ix_mcp_connection_events_run_id",
        "agent_run_mcp_connection_events",
        ["run_id"],
    )

    op.add_column(
        "agent_run_mcp_connections",
        sa.Column(
            "health",
            sa.String(16),
            nullable=True,
            server_default="healthy",
        ),
    )


def downgrade() -> None:
    op.drop_column("agent_run_mcp_connections", "health")
    op.drop_table("agent_run_mcp_connection_events")
    op.drop_table("permission_audit_events")
