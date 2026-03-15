"""merge pending skill creations and im event outbox

Revision ID: 9a4fff9b8b57
Revises: 496ff1c1ee70, 8a31d647f0ff
Create Date: 2026-03-15 20:38:34.661081

"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = '9a4fff9b8b57'
down_revision: Union[str, Sequence[str], None] = ('496ff1c1ee70', '8a31d647f0ff')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
