"""add project runtime config and local mounts

Revision ID: d17c3fd8fad7
Revises: 833daf707b32
Create Date: 2026-04-01 22:17:11.936841

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d17c3fd8fad7"
down_revision: Union[str, Sequence[str], None] = "833daf707b32"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "projects",
        sa.Column("default_model", sa.String(length=255), nullable=True),
    )
    op.create_table(
        "project_local_mounts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("mount_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("host_path", sa.Text(), nullable=False),
        sa.Column("access_mode", sa.String(length=2), nullable=False),
        sa.Column(
            "sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False
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
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_project_local_mounts_project_id",
        "project_local_mounts",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_project_local_mounts_project_mount_id",
        "project_local_mounts",
        ["project_id", "mount_id"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_project_local_mounts_project_mount_id", table_name="project_local_mounts"
    )
    op.drop_index(
        "ix_project_local_mounts_project_id", table_name="project_local_mounts"
    )
    op.drop_table("project_local_mounts")
    op.drop_column("projects", "default_model")
