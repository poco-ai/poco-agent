from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.channel_delivery import ChannelDelivery


class ChannelDeliveryRepository:
    @staticmethod
    def get_by_channel(db: Session, *, channel_id: int) -> ChannelDelivery | None:
        stmt = select(ChannelDelivery).where(ChannelDelivery.channel_id == channel_id)
        return db.execute(stmt).scalars().first()

    @staticmethod
    def get_send_address(db: Session, *, channel_id: int) -> str | None:
        row = ChannelDeliveryRepository.get_by_channel(db, channel_id=channel_id)
        if not row:
            return None
        return row.send_address

    @staticmethod
    def upsert_send_address(
        db: Session, *, channel_id: int, send_address: str
    ) -> ChannelDelivery:
        current = ChannelDeliveryRepository.get_by_channel(db, channel_id=channel_id)
        if current:
            current.send_address = send_address
            db.commit()
            db.refresh(current)
            return current

        row = ChannelDelivery(channel_id=channel_id, send_address=send_address)
        db.add(row)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            current = ChannelDeliveryRepository.get_by_channel(
                db, channel_id=channel_id
            )
            if current:
                current.send_address = send_address
                db.commit()
                db.refresh(current)
                return current
            raise
        db.refresh(row)
        return row
