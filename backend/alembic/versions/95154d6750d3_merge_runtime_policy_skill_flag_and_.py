"""merge runtime policy skill flag and channel heads

Revision ID: 95154d6750d3
Revises: 20260510_merge_heads, 536bf6b4ee0c
Create Date: 2026-05-11 02:03:33.211001

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "95154d6750d3"
down_revision: Union[str, Sequence[str], None] = (
    "20260510_merge_heads",
    "536bf6b4ee0c",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
