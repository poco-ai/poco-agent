"""add system role to users

Revision ID: 20260420_sys_role
Revises: f3b9c4d7e8a1
Create Date: 2026-04-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260420_sys_role"
down_revision = "f3b9c4d7e8a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "system_role",
            sa.String(length=50),
            nullable=False,
            server_default="user",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "system_role")
