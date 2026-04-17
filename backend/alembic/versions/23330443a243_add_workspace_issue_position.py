"""add workspace issue position

Revision ID: 23330443a243
Revises: 3b7f9c2d4e11
Create Date: 2026-04-17 13:40:34.707950

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "23330443a243"
down_revision: Union[str, Sequence[str], None] = "3b7f9c2d4e11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "workspace_issues",
        sa.Column("position", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY board_id, status
                    ORDER BY created_at ASC, updated_at ASC, id ASC
                ) - 1 AS new_position
            FROM workspace_issues
        )
        UPDATE workspace_issues AS issues
        SET position = ranked.new_position
        FROM ranked
        WHERE issues.id = ranked.id
        """
    )
    op.create_index(
        "ix_workspace_issues_board_id_status_position",
        "workspace_issues",
        ["board_id", "status", "position"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_workspace_issues_board_id_status_position",
        table_name="workspace_issues",
    )
    op.drop_column("workspace_issues", "position")
