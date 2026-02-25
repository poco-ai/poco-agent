"""empty message

Revision ID: 331320b4f8d1
Revises: b59418d33935
Create Date: 2026-02-20 12:41:58.092954

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "331320b4f8d1"
down_revision: Union[str, Sequence[str], None] = "b59418d33935"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    def drop_index_if_exists(table_name: str, index_name: str) -> None:
        if inspector.has_table(table_name):
            indexes = inspector.get_indexes(table_name)
            if any(idx.get("name") == index_name for idx in indexes):
                op.drop_index(op.f(index_name), table_name=table_name)

    def drop_column_if_exists(table_name: str, column_name: str) -> None:
        if inspector.has_table(table_name):
            columns = inspector.get_columns(table_name)
            if any(col.get("name") == column_name for col in columns):
                op.drop_column(table_name, column_name)

    drop_index_if_exists("agent_runs", "ix_agent_runs_workspace_ref_id")
    drop_index_if_exists("agent_runs", "ix_agent_runs_workspace_scope")
    drop_column_if_exists("agent_runs", "workspace_scope")
    drop_column_if_exists("agent_runs", "workspace_ref_id")

    drop_index_if_exists("agent_scheduled_tasks", "ix_agent_scheduled_tasks_project_id")
    drop_index_if_exists("agent_scheduled_tasks", "ix_agent_scheduled_tasks_workspace_scope")

    if inspector.has_table("agent_scheduled_tasks"):
        try:
            op.drop_constraint(
                op.f("agent_scheduled_tasks_project_id_fkey"),
                "agent_scheduled_tasks",
                type_="foreignkey",
            )
        except Exception:
            pass

    drop_column_if_exists("agent_scheduled_tasks", "project_id")
    drop_column_if_exists("agent_scheduled_tasks", "workspace_scope")

    drop_index_if_exists("agent_sessions", "ix_agent_sessions_workspace_ref_id")
    drop_index_if_exists("agent_sessions", "ix_agent_sessions_workspace_scope")
    drop_column_if_exists("agent_sessions", "workspace_scope")
    drop_column_if_exists("agent_sessions", "workspace_ref_id")

    if inspector.has_table("plugins"):
        columns = inspector.get_columns("plugins")
        if not any(col.get("name") == "source" for col in columns):
            op.add_column("plugins", sa.Column("source", sa.JSON(), nullable=True))

    if inspector.has_table("skills"):
        columns = inspector.get_columns("skills")
        if not any(col.get("name") == "source" for col in columns):
            op.add_column("skills", sa.Column("source", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    def drop_column_if_exists(table_name: str, column_name: str) -> None:
        if inspector.has_table(table_name):
            columns = inspector.get_columns(table_name)
            if any(col.get("name") == column_name for col in columns):
                op.drop_column(table_name, column_name)

    def add_column_if_not_exists(table_name: str, column_name: str, column_def) -> None:
        if inspector.has_table(table_name):
            columns = inspector.get_columns(table_name)
            if not any(col.get("name") == column_name for col in columns):
                op.add_column(table_name, column_def)

    drop_column_if_exists("skills", "source")
    drop_column_if_exists("plugins", "source")

    add_column_if_not_exists(
        "agent_sessions",
        "workspace_ref_id",
        sa.Column("workspace_ref_id", sa.UUID(), autoincrement=False, nullable=True),
    )
    add_column_if_not_exists(
        "agent_sessions",
        "workspace_scope",
        sa.Column(
            "workspace_scope",
            sa.VARCHAR(length=50),
            server_default=sa.text("'session'::character varying"),
            autoincrement=False,
            nullable=False,
        ),
    )

    if inspector.has_table("agent_sessions"):
        indexes = inspector.get_indexes("agent_sessions")
        if not any(idx.get("name") == "ix_agent_sessions_workspace_scope" for idx in indexes):
            op.create_index(
                op.f("ix_agent_sessions_workspace_scope"),
                "agent_sessions",
                ["workspace_scope"],
                unique=False,
            )
        if not any(idx.get("name") == "ix_agent_sessions_workspace_ref_id" for idx in indexes):
            op.create_index(
                op.f("ix_agent_sessions_workspace_ref_id"),
                "agent_sessions",
                ["workspace_ref_id"],
                unique=False,
            )

    add_column_if_not_exists(
        "agent_scheduled_tasks",
        "workspace_scope",
        sa.Column(
            "workspace_scope",
            sa.VARCHAR(length=50),
            server_default=sa.text("'session'::character varying"),
            autoincrement=False,
            nullable=False,
        ),
    )
    add_column_if_not_exists(
        "agent_scheduled_tasks",
        "project_id",
        sa.Column("project_id", sa.UUID(), autoincrement=False, nullable=True),
    )

    if inspector.has_table("agent_scheduled_tasks"):
        fks = inspector.get_foreign_keys("agent_scheduled_tasks")
        if not any(fk.get("name") == "agent_scheduled_tasks_project_id_fkey" for fk in fks):
            op.create_foreign_key(
                op.f("agent_scheduled_tasks_project_id_fkey"),
                "agent_scheduled_tasks",
                "projects",
                ["project_id"],
                ["id"],
                ondelete="SET NULL",
            )

        indexes = inspector.get_indexes("agent_scheduled_tasks")
        if not any(idx.get("name") == "ix_agent_scheduled_tasks_workspace_scope" for idx in indexes):
            op.create_index(
                op.f("ix_agent_scheduled_tasks_workspace_scope"),
                "agent_scheduled_tasks",
                ["workspace_scope"],
                unique=False,
            )
        if not any(idx.get("name") == "ix_agent_scheduled_tasks_project_id" for idx in indexes):
            op.create_index(
                op.f("ix_agent_scheduled_tasks_project_id"),
                "agent_scheduled_tasks",
                ["project_id"],
                unique=False,
            )

    add_column_if_not_exists(
        "agent_runs",
        "workspace_ref_id",
        sa.Column("workspace_ref_id", sa.UUID(), autoincrement=False, nullable=True),
    )
    add_column_if_not_exists(
        "agent_runs",
        "workspace_scope",
        sa.Column(
            "workspace_scope",
            sa.VARCHAR(length=50),
            server_default=sa.text("'session'::character varying"),
            autoincrement=False,
            nullable=False,
        ),
    )

    if inspector.has_table("agent_runs"):
        indexes = inspector.get_indexes("agent_runs")
        if not any(idx.get("name") == "ix_agent_runs_workspace_scope" for idx in indexes):
            op.create_index(
                op.f("ix_agent_runs_workspace_scope"),
                "agent_runs",
                ["workspace_scope"],
                unique=False,
            )
        if not any(idx.get("name") == "ix_agent_runs_workspace_ref_id" for idx in indexes):
            op.create_index(
                op.f("ix_agent_runs_workspace_ref_id"),
                "agent_runs",
                ["workspace_ref_id"],
                unique=False,
            )
