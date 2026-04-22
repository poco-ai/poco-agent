from sqlalchemy import Boolean, JSON, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class McpServer(Base, TimestampMixin):
    __tablename__ = "mcp_servers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    scope: Mapped[str] = mapped_column(String(20), default="user", nullable=False)
    owner_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    server_config: Mapped[dict] = mapped_column(JSON, nullable=False)
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
        UniqueConstraint("name", "owner_user_id", name="uq_mcp_server_name_owner"),
    )
