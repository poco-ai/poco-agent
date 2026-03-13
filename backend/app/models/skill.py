from sqlalchemy import JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class Skill(Base, TimestampMixin):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Name is used as the directory name under ~/.claude/skills/<name>/ (staged into workspace).
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    scope: Mapped[str] = mapped_column(String(20), default="user", nullable=False)
    owner_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    # Location info for staging the skill into workspace (e.g. {"s3_key": "...", "is_prefix": true}).
    entry: Mapped[dict] = mapped_column(JSON, nullable=False)
    source: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("name", "owner_user_id", name="uq_skill_name_owner"),
    )
