from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class ChannelDelivery(Base, TimestampMixin):
    __tablename__ = "channel_deliveries"
    __table_args__ = (
        UniqueConstraint("channel_id", name="uq_channel_delivery_channel_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    send_address: Mapped[str] = mapped_column(String(2048), nullable=False)
