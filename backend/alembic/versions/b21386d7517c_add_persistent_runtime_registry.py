"""add persistent runtime registry

Revision ID: b21386d7517c
Revises: ab4f7c9d2e31
Create Date: 2026-05-31 00:31:36.708032

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b21386d7517c"
down_revision: Union[str, Sequence[str], None] = "ab4f7c9d2e31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "persistent_runtimes",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("runtime_key", sa.String(length=255), nullable=False),
        sa.Column("owner_type", sa.String(length=50), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("agent_identity_id", sa.Uuid(), nullable=True),
        sa.Column("assignment_id", sa.Uuid(), nullable=True),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("container_id", sa.String(length=255), nullable=True),
        sa.Column(
            "lifecycle_state",
            sa.String(length=50),
            server_default=sa.text("'sleeping'"),
            nullable=False,
        ),
        sa.Column(
            "auto_resume", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "idle_timeout_seconds",
            sa.Integer(),
            server_default=sa.text("900"),
            nullable=False,
        ),
        sa.Column(
            "warm_retention_seconds",
            sa.Integer(),
            server_default=sa.text("120"),
            nullable=False,
        ),
        sa.Column("keepalive_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_stop_reason", sa.String(length=255), nullable=True),
        sa.Column("worker_id", sa.String(length=255), nullable=True),
        sa.Column(
            "browser_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("filesystem_fingerprint", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
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
            ["agent_identity_id"], ["agent_identities.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["assignment_id"], ["agent_assignments.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["agent_sessions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_persistent_runtimes_agent_identity_id"),
        "persistent_runtimes",
        ["agent_identity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_persistent_runtimes_assignment_id"),
        "persistent_runtimes",
        ["assignment_id"],
        unique=False,
    )
    op.create_index(
        "ix_persistent_runtimes_container_id",
        "persistent_runtimes",
        ["container_id"],
        unique=False,
    )
    op.create_index(
        "ix_persistent_runtimes_lifecycle_state",
        "persistent_runtimes",
        ["lifecycle_state"],
        unique=False,
    )
    op.create_index(
        "ix_persistent_runtimes_owner",
        "persistent_runtimes",
        ["owner_type", "owner_id"],
        unique=False,
    )
    op.create_index(
        "ix_persistent_runtimes_runtime_key",
        "persistent_runtimes",
        ["runtime_key"],
        unique=True,
    )
    op.create_index(
        op.f("ix_persistent_runtimes_session_id"),
        "persistent_runtimes",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_persistent_runtimes_session_id"), table_name="persistent_runtimes"
    )
    op.drop_index(
        "ix_persistent_runtimes_runtime_key", table_name="persistent_runtimes"
    )
    op.drop_index("ix_persistent_runtimes_owner", table_name="persistent_runtimes")
    op.drop_index(
        "ix_persistent_runtimes_lifecycle_state", table_name="persistent_runtimes"
    )
    op.drop_index(
        "ix_persistent_runtimes_container_id", table_name="persistent_runtimes"
    )
    op.drop_index(
        op.f("ix_persistent_runtimes_assignment_id"), table_name="persistent_runtimes"
    )
    op.drop_index(
        op.f("ix_persistent_runtimes_agent_identity_id"),
        table_name="persistent_runtimes",
    )
    op.drop_table("persistent_runtimes")
