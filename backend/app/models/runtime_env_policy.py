from sqlalchemy import JSON, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class RuntimeEnvPolicy(Base, TimestampMixin):
    __tablename__ = "runtime_env_policies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    mode: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="opt_in",
        server_default=text("'opt_in'"),
    )
    allowlist_patterns: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default=text("'[]'::json"),
    )
    denylist_patterns: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default=text("'[]'::json"),
    )
