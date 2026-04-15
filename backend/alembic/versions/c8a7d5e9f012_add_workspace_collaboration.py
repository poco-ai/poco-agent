"""add workspace collaboration

Revision ID: c8a7d5e9f012
Revises: b6dbbf02d4c1
Create Date: 2026-04-16 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c8a7d5e9f012"
down_revision: Union[str, Sequence[str], None] = "b6dbbf02d4c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "presets",
        sa.Column("scope", sa.String(length=50), server_default="personal", nullable=False),
    )
    op.add_column("presets", sa.Column("workspace_id", sa.Uuid(), nullable=True))
    op.add_column("presets", sa.Column("owner_user_id", sa.String(length=255), nullable=True))
    op.add_column("presets", sa.Column("created_by", sa.String(length=255), nullable=True))
    op.add_column("presets", sa.Column("updated_by", sa.String(length=255), nullable=True))
    op.add_column(
        "presets",
        sa.Column("access_policy", sa.String(length=50), server_default="private", nullable=False),
    )
    op.add_column("presets", sa.Column("forked_from_preset_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_presets_scope"), "presets", ["scope"], unique=False)
    op.create_index(op.f("ix_presets_workspace_id"), "presets", ["workspace_id"], unique=False)
    op.create_index(
        op.f("ix_presets_forked_from_preset_id"),
        "presets",
        ["forked_from_preset_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_presets_workspace_id_workspaces",
        "presets",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_presets_forked_from_preset_id_presets",
        "presets",
        "presets",
        ["forked_from_preset_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "projects",
        sa.Column("scope", sa.String(length=50), server_default="personal", nullable=False),
    )
    op.add_column("projects", sa.Column("workspace_id", sa.Uuid(), nullable=True))
    op.add_column("projects", sa.Column("owner_user_id", sa.String(length=255), nullable=True))
    op.add_column("projects", sa.Column("created_by", sa.String(length=255), nullable=True))
    op.add_column("projects", sa.Column("updated_by", sa.String(length=255), nullable=True))
    op.add_column(
        "projects",
        sa.Column("access_policy", sa.String(length=50), server_default="private", nullable=False),
    )
    op.add_column("projects", sa.Column("forked_from_project_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_projects_scope"), "projects", ["scope"], unique=False)
    op.create_index(op.f("ix_projects_workspace_id"), "projects", ["workspace_id"], unique=False)
    op.create_index(
        op.f("ix_projects_forked_from_project_id"),
        "projects",
        ["forked_from_project_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_projects_workspace_id_workspaces",
        "projects",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_projects_forked_from_project_id_projects",
        "projects",
        "projects",
        ["forked_from_project_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "workspace_boards",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workspace_boards_workspace_id"), "workspace_boards", ["workspace_id"])
    op.create_index(op.f("ix_workspace_boards_created_by"), "workspace_boards", ["created_by"])

    op.create_table(
        "workspace_board_fields",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("board_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("field_type", sa.String(length=50), nullable=False),
        sa.Column("options", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["board_id"], ["workspace_boards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workspace_board_fields_board_id"), "workspace_board_fields", ["board_id"])

    op.create_table(
        "workspace_issues",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("board_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="todo", nullable=False),
        sa.Column("type", sa.String(length=50), server_default="task", nullable=False),
        sa.Column("priority", sa.String(length=50), server_default="medium", nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assignee_user_id", sa.String(length=255), nullable=True),
        sa.Column("assignee_preset_id", sa.Integer(), nullable=True),
        sa.Column("reporter_user_id", sa.String(length=255), nullable=True),
        sa.Column("related_project_id", sa.Uuid(), nullable=True),
        sa.Column("creator_user_id", sa.String(length=255), nullable=False),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assignee_preset_id"], ["presets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["board_id"], ["workspace_boards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["related_project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in [
        "workspace_id",
        "board_id",
        "status",
        "priority",
        "assignee_user_id",
        "assignee_preset_id",
        "related_project_id",
        "creator_user_id",
    ]:
        op.create_index(op.f(f"ix_workspace_issues_{column}"), "workspace_issues", [column])

    op.create_table(
        "workspace_issue_field_values",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("issue_id", sa.Uuid(), nullable=False),
        sa.Column("field_id", sa.Uuid(), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["field_id"], ["workspace_board_fields.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["issue_id"], ["workspace_issues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workspace_issue_field_values_issue_id"), "workspace_issue_field_values", ["issue_id"])
    op.create_index(op.f("ix_workspace_issue_field_values_field_id"), "workspace_issue_field_values", ["field_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("workspace_issue_field_values")
    op.drop_table("workspace_issues")
    op.drop_table("workspace_board_fields")
    op.drop_table("workspace_boards")
    op.drop_constraint("fk_projects_forked_from_project_id_projects", "projects", type_="foreignkey")
    op.drop_constraint("fk_projects_workspace_id_workspaces", "projects", type_="foreignkey")
    op.drop_column("projects", "forked_from_project_id")
    op.drop_column("projects", "access_policy")
    op.drop_column("projects", "updated_by")
    op.drop_column("projects", "created_by")
    op.drop_column("projects", "owner_user_id")
    op.drop_column("projects", "workspace_id")
    op.drop_column("projects", "scope")
    op.drop_constraint("fk_presets_forked_from_preset_id_presets", "presets", type_="foreignkey")
    op.drop_constraint("fk_presets_workspace_id_workspaces", "presets", type_="foreignkey")
    op.drop_column("presets", "forked_from_preset_id")
    op.drop_column("presets", "access_policy")
    op.drop_column("presets", "updated_by")
    op.drop_column("presets", "created_by")
    op.drop_column("presets", "owner_user_id")
    op.drop_column("presets", "workspace_id")
    op.drop_column("presets", "scope")
