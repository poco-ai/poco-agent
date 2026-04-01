"""add execution settings and mcp connections

Revision ID: c8a7d1d2e3f4
Revises: 7f5a1b2c3d4e
Create Date: 2026-04-01 15:30:00.000000

"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c8a7d1d2e3f4"
down_revision: str | Sequence[str] | None = "7f5a1b2c3d4e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_execution_settings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column(
            "schema_version",
            sa.String(length=32),
            nullable=False,
            server_default="v1",
        ),
        sa.Column(
            "settings",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.add_column(
        "skills",
        sa.Column("manifest_version", sa.String(length=32), nullable=True),
    )
    op.add_column("skills", sa.Column("manifest", sa.JSON(), nullable=True))
    op.add_column(
        "skills",
        sa.Column("entry_checksum", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "skills",
        sa.Column(
            "lifecycle_state",
            sa.String(length=32),
            nullable=False,
            server_default="active",
        ),
    )

    op.add_column("agent_runs", sa.Column("config_layers", sa.JSON(), nullable=True))
    op.add_column(
        "agent_runs", sa.Column("resolved_hook_specs", sa.JSON(), nullable=True)
    )
    op.add_column(
        "agent_runs",
        sa.Column("permission_policy_snapshot", sa.JSON(), nullable=True),
    )

    op.add_column(
        "tool_executions",
        sa.Column("policy_action", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "tool_executions",
        sa.Column("policy_rule_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "tool_executions",
        sa.Column("policy_reason", sa.String(length=1000), nullable=True),
    )

    op.create_table(
        "agent_run_mcp_connections",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=True),
        sa.Column("server_name", sa.String(length=255), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("last_error", sa.String(length=2000), nullable=True),
        sa.Column("connection_metadata", sa.JSON(), nullable=True),
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
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["session_id"], ["agent_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_run_mcp_connections_run_id",
        "agent_run_mcp_connections",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        "ix_agent_run_mcp_connections_session_id",
        "agent_run_mcp_connections",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "ix_agent_run_mcp_connections_run_id_server_name",
        "agent_run_mcp_connections",
        ["run_id", "server_name"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_agent_run_mcp_connections_run_id_server_name",
        table_name="agent_run_mcp_connections",
    )
    op.drop_index(
        "ix_agent_run_mcp_connections_session_id",
        table_name="agent_run_mcp_connections",
    )
    op.drop_index(
        "ix_agent_run_mcp_connections_run_id",
        table_name="agent_run_mcp_connections",
    )
    op.drop_table("agent_run_mcp_connections")

    op.drop_column("tool_executions", "policy_reason")
    op.drop_column("tool_executions", "policy_rule_id")
    op.drop_column("tool_executions", "policy_action")

    op.drop_column("agent_runs", "permission_policy_snapshot")
    op.drop_column("agent_runs", "resolved_hook_specs")
    op.drop_column("agent_runs", "config_layers")

    op.drop_column("skills", "lifecycle_state")
    op.drop_column("skills", "entry_checksum")
    op.drop_column("skills", "manifest")
    op.drop_column("skills", "manifest_version")

    op.drop_table("user_execution_settings")
