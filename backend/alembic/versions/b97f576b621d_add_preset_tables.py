"""add preset tables

Revision ID: b97f576b621d
Revises: adaae42d2d49
Create Date: 2026-03-30 21:25:15.632662

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b97f576b621d"
down_revision: Union[str, Sequence[str], None] = "adaae42d2d49"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "presets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "icon",
            sa.String(length=100),
            server_default=sa.text("'default'"),
            nullable=False,
        ),
        sa.Column("color", sa.String(length=20), nullable=True),
        sa.Column("prompt_template", sa.Text(), nullable=True),
        sa.Column(
            "browser_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "memory_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "skill_ids",
            sa.ARRAY(sa.Integer()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "mcp_server_ids",
            sa.ARRAY(sa.Integer()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "plugin_ids",
            sa.ARRAY(sa.Integer()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "subagent_configs",
            sa.JSON(),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "name", "is_deleted", name="uq_preset_user_name"
        ),
    )
    op.create_index(op.f("ix_presets_user_id"), "presets", ["user_id"], unique=False)

    op.create_table(
        "project_presets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("preset_id", sa.Integer(), nullable=False),
        sa.Column(
            "is_default",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "sort_order",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["preset_id"], ["presets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_project_preset_default",
        "project_presets",
        ["project_id"],
        unique=True,
        postgresql_where=sa.text("is_default = true"),
    )
    op.create_index(
        op.f("ix_project_presets_preset_id"),
        "project_presets",
        ["preset_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_presets_project_id"),
        "project_presets",
        ["project_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_project_presets_project_id"),
        table_name="project_presets",
    )
    op.drop_index(
        op.f("ix_project_presets_preset_id"),
        table_name="project_presets",
    )
    op.drop_index("ix_project_preset_default", table_name="project_presets")
    op.drop_table("project_presets")
    op.drop_index(op.f("ix_presets_user_id"), table_name="presets")
    op.drop_table("presets")
