from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class UserExecutionSetting(Base, TimestampMixin):
    __tablename__ = "user_execution_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    schema_version: Mapped[str] = mapped_column(
        String(32), default="v1", nullable=False
    )
    settings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
