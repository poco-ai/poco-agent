"""add system capability policy flags

Revision ID: 20260420_cap_policy_flags
Revises: 20260420_sys_role
Create Date: 2026-04-20 00:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260420_cap_policy_flags"
down_revision = "20260420_sys_role"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table_name in ("skills", "mcp_servers", "plugins"):
        op.add_column(
            table_name,
            sa.Column(
                "default_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )
        op.add_column(
            table_name,
            sa.Column(
                "force_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )


def downgrade() -> None:
    for table_name in ("plugins", "mcp_servers", "skills"):
        op.drop_column(table_name, "force_enabled")
        op.drop_column(table_name, "default_enabled")
