from sqlalchemy import Boolean, ForeignKey, JSON, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class UserMcpConfig(Base, TimestampMixin):
    __tablename__ = "user_mcp_configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    preset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("mcp_presets.id", ondelete="CASCADE"), nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    overrides: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "preset_id", name="uq_user_mcp_user_preset"),
    )
