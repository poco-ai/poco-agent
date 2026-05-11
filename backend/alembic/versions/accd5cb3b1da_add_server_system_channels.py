"""add server system channels

Revision ID: accd5cb3b1da
Revises: 20260510_merge_heads
Create Date: 2026-05-11 15:16:42.852210

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "accd5cb3b1da"
down_revision: Union[str, Sequence[str], None] = "20260510_merge_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "server_channels",
        sa.Column("system_channel_type", sa.String(length=50), nullable=True),
    )

    op.execute(
        """
        UPDATE server_channels AS c
        SET system_channel_type = 'personal',
            name = 'Personal'
        FROM servers AS s
        WHERE c.server_id = s.id
          AND s.kind = 'personal'
          AND c.slug = 'personal'
          AND c.archived_at IS NULL
          AND c.system_channel_type IS NULL
        """
    )
    op.execute(
        """
        INSERT INTO server_channels (
            id,
            server_id,
            name,
            slug,
            description,
            conversation_type,
            visibility,
            system_channel_type,
            created_by,
            created_at,
            updated_at
        )
        SELECT
            gen_random_uuid(),
            s.id,
            'Personal',
            CASE
                WHEN EXISTS (
                    SELECT 1 FROM server_channels existing
                    WHERE existing.server_id = s.id AND existing.slug = 'personal'
                )
                THEN 'personal-' || left(md5(s.id::text), 8)
                ELSE 'personal'
            END,
            NULL,
            'channel',
            'private',
            'personal',
            s.owner_user_id,
            now(),
            now()
        FROM servers AS s
        WHERE s.kind = 'personal'
          AND NOT EXISTS (
              SELECT 1 FROM server_channels c
              WHERE c.server_id = s.id
                AND c.system_channel_type = 'personal'
          )
        """
    )
    op.execute(
        """
        INSERT INTO server_channel_members (
            channel_id,
            user_id,
            role,
            joined_at,
            status,
            created_at,
            updated_at
        )
        SELECT
            c.id,
            s.owner_user_id,
            'owner',
            now(),
            'active',
            now(),
            now()
        FROM server_channels AS c
        JOIN servers AS s ON s.id = c.server_id
        WHERE c.system_channel_type = 'personal'
          AND NOT EXISTS (
              SELECT 1 FROM server_channel_members existing
              WHERE existing.channel_id = c.id
                AND existing.user_id = s.owner_user_id
          )
        """
    )

    op.execute(
        """
        WITH ranked AS (
            SELECT
                c.id,
                row_number() OVER (
                    PARTITION BY c.server_id
                    ORDER BY
                        CASE
                            WHEN c.slug = 'public' THEN 0
                            WHEN c.slug = 'general' THEN 1
                            ELSE 2
                        END,
                        c.created_at ASC,
                        c.id ASC
                ) AS rn
            FROM server_channels c
            JOIN servers s ON s.id = c.server_id
            WHERE s.kind = 'shared'
              AND c.conversation_type = 'channel'
              AND c.visibility = 'public'
              AND c.archived_at IS NULL
        )
        UPDATE server_channels AS c
        SET system_channel_type = 'public',
            name = 'Public',
            slug = CASE
                WHEN c.slug = 'public'
                  OR NOT EXISTS (
                      SELECT 1 FROM server_channels sibling
                      WHERE sibling.server_id = c.server_id
                        AND sibling.slug = 'public'
                        AND sibling.id <> c.id
                  )
                THEN 'public'
                ELSE c.slug
            END
        FROM ranked
        WHERE ranked.id = c.id
          AND ranked.rn = 1
        """
    )
    op.execute(
        """
        INSERT INTO server_channels (
            id,
            server_id,
            name,
            slug,
            description,
            conversation_type,
            visibility,
            system_channel_type,
            created_by,
            created_at,
            updated_at
        )
        SELECT
            gen_random_uuid(),
            s.id,
            'Public',
            CASE
                WHEN EXISTS (
                    SELECT 1 FROM server_channels existing
                    WHERE existing.server_id = s.id AND existing.slug = 'public'
                )
                THEN 'public-' || left(md5(s.id::text), 8)
                ELSE 'public'
            END,
            NULL,
            'channel',
            'public',
            'public',
            s.owner_user_id,
            now(),
            now()
        FROM servers AS s
        WHERE s.kind = 'shared'
          AND NOT EXISTS (
              SELECT 1 FROM server_channels c
              WHERE c.server_id = s.id
                AND c.system_channel_type = 'public'
          )
        """
    )
    op.execute(
        """
        UPDATE server_channel_members AS scm
        SET status = 'active',
            updated_at = now()
        FROM server_channels AS c
        JOIN server_members AS sm
          ON sm.server_id = c.server_id
         AND sm.status = 'active'
        WHERE c.system_channel_type = 'public'
          AND scm.channel_id = c.id
          AND scm.user_id = sm.user_id
          AND scm.status <> 'active'
        """
    )
    op.execute(
        """
        INSERT INTO server_channel_members (
            channel_id,
            user_id,
            role,
            joined_at,
            status,
            created_at,
            updated_at
        )
        SELECT
            c.id,
            sm.user_id,
            CASE WHEN sm.role = 'owner' THEN 'owner' ELSE 'member' END,
            now(),
            'active',
            now(),
            now()
        FROM server_channels AS c
        JOIN server_members AS sm
          ON sm.server_id = c.server_id
         AND sm.status = 'active'
        WHERE c.system_channel_type = 'public'
          AND NOT EXISTS (
              SELECT 1 FROM server_channel_members existing
              WHERE existing.channel_id = c.id
                AND existing.user_id = sm.user_id
          )
        """
    )

    op.create_index(
        op.f("ix_server_channels_system_channel_type"),
        "server_channels",
        ["system_channel_type"],
        unique=False,
    )
    op.create_index(
        "uq_server_channels_server_system_channel_type",
        "server_channels",
        ["server_id", "system_channel_type"],
        unique=True,
        postgresql_where=sa.text("system_channel_type IS NOT NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "uq_server_channels_server_system_channel_type",
        table_name="server_channels",
        postgresql_where=sa.text("system_channel_type IS NOT NULL"),
    )
    op.drop_index(
        op.f("ix_server_channels_system_channel_type"),
        table_name="server_channels",
    )
    op.drop_column("server_channels", "system_channel_type")
