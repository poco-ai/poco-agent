"""add_session_queue_items_table

Revision ID: 98b9968cc9be
Revises: 74e90ae3d7a1
Create Date: 2026-03-10 18:05:35.711162

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "98b9968cc9be"
down_revision: Union[str, Sequence[str], None] = "74e90ae3d7a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "agent_session_queue_items",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_no", sa.BigInteger(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=50),
            server_default=sa.text("'queued'"),
            nullable=False,
        ),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column(
            "permission_mode",
            sa.String(length=50),
            server_default=sa.text("'default'"),
            nullable=False,
        ),
        sa.Column("run_config_snapshot", sa.JSON(), nullable=True),
        sa.Column("client_request_id", sa.String(length=255), nullable=True),
        sa.Column("linked_run_id", sa.Uuid(), nullable=True),
        sa.Column("linked_user_message_id", sa.BigInteger(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["linked_run_id"], ["agent_runs.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["linked_user_message_id"],
            ["agent_messages.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["agent_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id",
            "sequence_no",
            name="uq_agent_session_queue_items_session_id_sequence_no",
        ),
        sa.UniqueConstraint(
            "session_id",
            "client_request_id",
            name="uq_agent_session_queue_items_session_id_client_request_id",
        ),
    )
    op.create_index(
        op.f("ix_agent_session_queue_items_linked_run_id"),
        "agent_session_queue_items",
        ["linked_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_session_queue_items_linked_user_message_id"),
        "agent_session_queue_items",
        ["linked_user_message_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_session_queue_items_session_id"),
        "agent_session_queue_items",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_session_queue_items_status"),
        "agent_session_queue_items",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_agent_session_queue_items_session_id_status_sequence_no",
        "agent_session_queue_items",
        ["session_id", "status", "sequence_no"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_agent_session_queue_items_session_id_status_sequence_no",
        table_name="agent_session_queue_items",
    )
    op.drop_index(
        op.f("ix_agent_session_queue_items_status"),
        table_name="agent_session_queue_items",
    )
    op.drop_index(
        op.f("ix_agent_session_queue_items_session_id"),
        table_name="agent_session_queue_items",
    )
    op.drop_index(
        op.f("ix_agent_session_queue_items_linked_user_message_id"),
        table_name="agent_session_queue_items",
    )
    op.drop_index(
        op.f("ix_agent_session_queue_items_linked_run_id"),
        table_name="agent_session_queue_items",
    )
    op.drop_table("agent_session_queue_items")
