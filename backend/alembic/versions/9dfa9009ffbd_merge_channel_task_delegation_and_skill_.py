"""merge channel task delegation and skill flag heads

Revision ID: 9dfa9009ffbd
Revises: 907f563b7532, 95154d6750d3
Create Date: 2026-05-11 21:15:24.976376

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "9dfa9009ffbd"
down_revision: Union[str, Sequence[str], None] = ("907f563b7532", "95154d6750d3")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
