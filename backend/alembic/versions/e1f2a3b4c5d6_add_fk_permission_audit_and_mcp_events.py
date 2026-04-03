"""Add FK permission audit and mcp events

Revision ID: e1f2a3b4c5d6
Revises: d5e8b3c1a2f4
Create Date: 2026-04-02
"""

from typing import Sequence, Union

from alembic import op

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "d5e8b3c1a2f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_permission_audit_events_run_id_agent_runs",
        "permission_audit_events",
        "agent_runs",
        ["run_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_permission_audit_events_session_id_agent_sessions",
        "permission_audit_events",
        "agent_sessions",
        ["session_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_mcp_connection_events_run_id_agent_runs",
        "agent_run_mcp_connection_events",
        "agent_runs",
        ["run_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_mcp_connection_events_run_id_agent_runs",
        "agent_run_mcp_connection_events",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_permission_audit_events_session_id_agent_sessions",
        "permission_audit_events",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_permission_audit_events_run_id_agent_runs",
        "permission_audit_events",
        type_="foreignkey",
    )
