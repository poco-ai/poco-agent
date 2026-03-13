"""Merge migrations

This migration merges two parallel migration branches:
- 0537f90d9fc7: add user model provider settings
- 66b67a534707: add description to mcp servers

Revision ID: merge_heads
Revises: (0537f90d9fc7, 66b67a534707)
Create Date: 2026-03-13 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'merge_heads'
down_revision = ('0537f90d9fc7', '66b67a534707')
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Both branches have already been applied, no action needed
    pass


def downgrade() -> None:
    # To downgrade, we need to undo the migrations in reverse order
    # First undo the mcp_servers branch, then the model provider settings
    op.execute(
        "DELETE FROM alembic_version WHERE version_num = 'merge_heads'"
    )
    # The individual migrations will handle their own downgrades
    # when their respective heads are targeted
