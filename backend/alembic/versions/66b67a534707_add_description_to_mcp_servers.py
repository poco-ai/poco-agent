"""add description to mcp servers

Revision ID: 66b67a534707
Revises: ac35ccd45c9d
Create Date: 2026-03-12 14:11:07.459844

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "66b67a534707"
down_revision: Union[str, Sequence[str], None] = "ac35ccd45c9d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "mcp_servers", sa.Column("description", sa.String(length=1000), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("mcp_servers", "description")
