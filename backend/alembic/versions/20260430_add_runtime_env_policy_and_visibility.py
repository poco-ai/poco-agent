"""add runtime env policy and visibility

Revision ID: 20260430_runtime_env_policy
Revises: 20260420_cap_policy_flags
Create Date: 2026-04-30 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260430_runtime_env_policy"
down_revision: str | Sequence[str] | None = "20260420_cap_policy_flags"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_env_vars",
        sa.Column(
            "expose_to_runtime",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "user_env_vars",
        sa.Column(
            "runtime_visibility",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'none'"),
        ),
    )
    op.create_table(
        "runtime_env_policies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "mode",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'opt_in'"),
        ),
        sa.Column(
            "allowlist_patterns",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
        sa.Column(
            "denylist_patterns",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
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
    )


def downgrade() -> None:
    op.drop_table("runtime_env_policies")
    op.drop_column("user_env_vars", "runtime_visibility")
    op.drop_column("user_env_vars", "expose_to_runtime")
