"""add im event outbox

Revision ID: 8a31d647f0ff
Revises: 66b67a534707, 98b9968cc9be
Create Date: 2026-03-15 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8a31d647f0ff"
down_revision: Union[str, Sequence[str], None] = (
    "66b67a534707",
    "98b9968cc9be",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "im_event_outbox",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("event_key", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column(
            "event_version", sa.Integer(), server_default=sa.text("1"), nullable=False
        ),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("user_input_request_id", sa.Uuid(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=50),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column(
            "attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_key", name="uq_im_event_outbox_event_key"),
    )
    op.create_index(
        "ix_im_event_outbox_status_next_attempt_at_created_at",
        "im_event_outbox",
        ["status", "next_attempt_at", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_im_event_outbox_user_id"),
        "im_event_outbox",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_im_event_outbox_session_id",
        "im_event_outbox",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "ix_im_event_outbox_run_id",
        "im_event_outbox",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        "ix_im_event_outbox_user_input_request_id",
        "im_event_outbox",
        ["user_input_request_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_im_event_outbox_status"),
        "im_event_outbox",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_im_event_outbox_status"), table_name="im_event_outbox")
    op.drop_index(
        "ix_im_event_outbox_user_input_request_id", table_name="im_event_outbox"
    )
    op.drop_index("ix_im_event_outbox_run_id", table_name="im_event_outbox")
    op.drop_index("ix_im_event_outbox_session_id", table_name="im_event_outbox")
    op.drop_index(op.f("ix_im_event_outbox_user_id"), table_name="im_event_outbox")
    op.drop_index(
        "ix_im_event_outbox_status_next_attempt_at_created_at",
        table_name="im_event_outbox",
    )
    op.drop_table("im_event_outbox")
