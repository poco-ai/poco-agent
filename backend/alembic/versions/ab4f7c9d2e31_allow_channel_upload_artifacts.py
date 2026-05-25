"""allow channel upload artifacts

Revision ID: ab4f7c9d2e31
Revises: 9dfa9009ffbd
Create Date: 2026-05-24 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ab4f7c9d2e31"
down_revision: Union[str, Sequence[str], None] = "9dfa9009ffbd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "channel_artifacts",
        "source_session_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DELETE FROM channel_artifacts WHERE source_session_id IS NULL")
    op.alter_column(
        "channel_artifacts",
        "source_session_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
