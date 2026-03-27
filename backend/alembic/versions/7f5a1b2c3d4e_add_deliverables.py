"""add deliverables

Revision ID: 7f5a1b2c3d4e
Revises: d4019c5265dc
Create Date: 2026-03-23 22:55:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "7f5a1b2c3d4e"
down_revision: Union[str, Sequence[str], None] = "d4019c5265dc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "deliverables",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("logical_name", sa.String(length=255), nullable=False),
        sa.Column("latest_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
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
            ["session_id"],
            ["agent_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id",
            "kind",
            "logical_name",
            name="uq_deliverables_session_kind_name",
        ),
    )
    op.create_index(
        op.f("ix_deliverables_session_id"),
        "deliverables",
        ["session_id"],
        unique=False,
    )

    op.create_table(
        "deliverable_versions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "deliverable_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("source_message_id", sa.BigInteger(), nullable=True),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("input_refs_json", sa.JSON(), nullable=True),
        sa.Column("related_tool_execution_ids_json", sa.JSON(), nullable=True),
        sa.Column("detection_metadata_json", sa.JSON(), nullable=True),
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
            ["deliverable_id"],
            ["deliverables.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["agent_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["agent_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_message_id"],
            ["agent_messages.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id",
            "run_id",
            "file_path",
            name="uq_deliverable_versions_session_run_path",
        ),
    )
    op.create_index(
        op.f("ix_deliverable_versions_deliverable_id"),
        "deliverable_versions",
        ["deliverable_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_deliverable_versions_run_id"),
        "deliverable_versions",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_deliverable_versions_session_id"),
        "deliverable_versions",
        ["session_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_deliverables_latest_version_id",
        "deliverables",
        "deliverable_versions",
        ["latest_version_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_deliverables_latest_version_id",
        "deliverables",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_deliverable_versions_session_id"),
        table_name="deliverable_versions",
    )
    op.drop_index(
        op.f("ix_deliverable_versions_run_id"),
        table_name="deliverable_versions",
    )
    op.drop_index(
        op.f("ix_deliverable_versions_deliverable_id"),
        table_name="deliverable_versions",
    )
    op.drop_table("deliverable_versions")
    op.drop_index(op.f("ix_deliverables_session_id"), table_name="deliverables")
    op.drop_table("deliverables")
