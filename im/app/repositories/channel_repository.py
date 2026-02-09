from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.channel import Channel


class ChannelRepository:
    @staticmethod
    def get_by_provider_destination(
        db: Session, *, provider: str, destination: str
    ) -> Channel | None:
        stmt = (
            select(Channel)
            .where(Channel.provider == provider)
            .where(Channel.destination == destination)
        )
        return db.execute(stmt).scalars().first()

    @staticmethod
    def get_or_create(db: Session, *, provider: str, destination: str) -> Channel:
        existing = ChannelRepository.get_by_provider_destination(
            db, provider=provider, destination=destination
        )
        if existing:
            return existing

        channel = Channel(provider=provider, destination=destination)
        db.add(channel)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            # Concurrent create; load again.
            existing = ChannelRepository.get_by_provider_destination(
                db, provider=provider, destination=destination
            )
            if existing:
                return existing
            raise
        db.refresh(channel)
        return channel

    @staticmethod
    def list_enabled(db: Session) -> list[Channel]:
        stmt = select(Channel).where(Channel.enabled.is_(True))
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def set_subscribe_all(db: Session, *, channel_id: int, enabled: bool) -> Channel:
        channel = db.get(Channel, channel_id)
        if not channel:
            raise ValueError(f"Channel not found: {channel_id}")
        channel.subscribe_all = bool(enabled)
        db.commit()
        db.refresh(channel)
        return channel
