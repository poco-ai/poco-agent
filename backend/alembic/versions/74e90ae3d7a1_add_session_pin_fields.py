"""add session pin fields

Revision ID: 74e90ae3d7a1
Revises: 1b3d96b80d10
Create Date: 2026-03-09 07:35:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "74e90ae3d7a1"
down_revision: Union[str, Sequence[str], None] = "1b3d96b80d10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "agent_sessions",
        sa.Column(
            "is_pinned",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "agent_sessions",
        sa.Column("pinned_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("agent_sessions", "pinned_at")
    op.drop_column("agent_sessions", "is_pinned")
