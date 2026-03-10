from sqlalchemy import JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class UserModelProviderSetting(Base, TimestampMixin):
    __tablename__ = "user_model_provider_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    provider_id: Mapped[str] = mapped_column(String(64), nullable=False)
    model_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "provider_id",
            name="uq_user_model_provider_settings_user_provider",
        ),
    )
