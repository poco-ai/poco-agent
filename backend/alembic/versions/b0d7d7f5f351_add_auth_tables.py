"""add auth tables

Revision ID: b0d7d7f5f351
Revises: a053345a5972
Create Date: 2026-04-07 22:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b0d7d7f5f351"
down_revision: Union[str, Sequence[str], None] = "a053345a5972"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("primary_email", sa.String(length=320), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=50),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_users_primary_email",
        "users",
        ["primary_email"],
        unique=True,
    )

    op.create_table(
        "auth_identities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_user_id", sa.String(length=255), nullable=False),
        sa.Column("provider_email", sa.String(length=320), nullable=True),
        sa.Column(
            "email_verified",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("profile_json", sa.JSON(), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auth_identities_user_id", "auth_identities", ["user_id"])
    op.create_index(
        "ix_auth_identities_provider_provider_user_id",
        "auth_identities",
        ["provider", "provider_user_id"],
        unique=True,
    )
    op.create_index(
        "ix_auth_identities_user_id_provider",
        "auth_identities",
        ["user_id", "provider"],
        unique=False,
    )

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("session_token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index(
        "ix_user_sessions_session_token_hash",
        "user_sessions",
        ["session_token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_user_sessions_user_id_revoked_at_expires_at",
        "user_sessions",
        ["user_id", "revoked_at", "expires_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_user_sessions_user_id_revoked_at_expires_at",
        table_name="user_sessions",
    )
    op.drop_index("ix_user_sessions_session_token_hash", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")

    op.drop_index("ix_auth_identities_user_id_provider", table_name="auth_identities")
    op.drop_index(
        "ix_auth_identities_provider_provider_user_id",
        table_name="auth_identities",
    )
    op.drop_index("ix_auth_identities_user_id", table_name="auth_identities")
    op.drop_table("auth_identities")

    op.drop_index("ix_users_primary_email", table_name="users")
    op.drop_table("users")
