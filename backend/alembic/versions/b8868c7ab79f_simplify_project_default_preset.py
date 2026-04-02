"""simplify project default preset

Revision ID: b8868c7ab79f
Revises: d17c3fd8fad7
Create Date: 2026-04-02 16:24:16.935071

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b8868c7ab79f"
down_revision: Union[str, Sequence[str], None] = "d17c3fd8fad7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "projects", sa.Column("default_preset_id", sa.Integer(), nullable=True)
    )
    op.create_index(
        op.f("ix_projects_default_preset_id"),
        "projects",
        ["default_preset_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_projects_default_preset_id",
        "projects",
        "presets",
        ["default_preset_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        """
        UPDATE projects
        SET default_preset_id = project_presets.preset_id
        FROM project_presets
        WHERE project_presets.project_id = projects.id
          AND project_presets.is_default = true
        """
    )
    op.drop_index("ix_project_preset_default", table_name="project_presets")
    op.drop_table("project_presets")


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        "project_presets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("preset_id", sa.Integer(), nullable=False),
        sa.Column(
            "is_default",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
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
        sa.ForeignKeyConstraint(
            ["preset_id"],
            ["presets.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_project_presets_project_id",
        "project_presets",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_project_presets_preset_id",
        "project_presets",
        ["preset_id"],
        unique=False,
    )
    op.create_index(
        "ix_project_preset_default",
        "project_presets",
        ["project_id"],
        unique=True,
        postgresql_where=sa.text("is_default = true"),
    )
    op.execute(
        """
        INSERT INTO project_presets (
            project_id,
            preset_id,
            is_default,
            sort_order
        )
        SELECT
            id,
            default_preset_id,
            true,
            0
        FROM projects
        WHERE default_preset_id IS NOT NULL
        """
    )
    op.drop_constraint("fk_projects_default_preset_id", "projects", type_="foreignkey")
    op.drop_index(op.f("ix_projects_default_preset_id"), table_name="projects")
    op.drop_column("projects", "default_preset_id")
