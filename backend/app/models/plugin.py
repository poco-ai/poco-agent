from sqlalchemy import Boolean, JSON, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class Plugin(Base, TimestampMixin):
    __tablename__ = "plugins"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[str] = mapped_column(String(20), default="user", nullable=False)
    owner_user_id: Mapped[str] = mapped_column(String(255), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    manifest: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Location info for staging the plugin into workspace
    # (e.g. {"s3_key": ".../", "is_prefix": true}).
    entry: Mapped[dict] = mapped_column(JSON, nullable=False)
    source: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    default_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    force_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    __table_args__ = (
        UniqueConstraint("name", "owner_user_id", name="uq_plugin_name_owner"),
    )
