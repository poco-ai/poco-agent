from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.im import (
    ActiveSession,
    Channel,
    ChannelDelivery,
    DedupEvent,
    ImEventOutbox,
    WatchedSession,
)


class ActiveSessionRepository:
    @staticmethod
    def get_by_channel(db: Session, *, channel_id: int) -> ActiveSession | None:
        stmt = select(ActiveSession).where(ActiveSession.channel_id == channel_id)
        return db.execute(stmt).scalars().first()

    @staticmethod
    def create(db: Session, *, channel_id: int, session_id: str) -> ActiveSession:
        entry = ActiveSession(channel_id=channel_id, session_id=session_id)
        db.add(entry)
        return entry

    @staticmethod
    def delete_by_channel(db: Session, *, channel_id: int) -> int:
        stmt = delete(ActiveSession).where(ActiveSession.channel_id == channel_id)
        result = db.execute(stmt)
        return int(result.rowcount or 0)

    @staticmethod
    def list_by_session(db: Session, *, session_id: str) -> list[ActiveSession]:
        stmt = select(ActiveSession).where(ActiveSession.session_id == session_id)
        return list(db.execute(stmt).scalars().all())


class ChannelRepository:
    @staticmethod
    def get_by_provider_destination(
        db: Session,
        *,
        provider: str,
        destination: str,
    ) -> Channel | None:
        stmt = (
            select(Channel)
            .where(Channel.provider == provider)
            .where(Channel.destination == destination)
        )
        return db.execute(stmt).scalars().first()

    @staticmethod
    def get_by_id(db: Session, *, channel_id: int) -> Channel | None:
        return db.get(Channel, channel_id)

    @staticmethod
    def create(db: Session, *, provider: str, destination: str) -> Channel:
        channel = Channel(provider=provider, destination=destination)
        db.add(channel)
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
        return channel


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
    def create(
        db: Session,
        *,
        channel_id: int,
        send_address: str,
    ) -> ChannelDelivery:
        row = ChannelDelivery(channel_id=channel_id, send_address=send_address)
        db.add(row)
        return row


class DedupRepository:
    @staticmethod
    def exists(db: Session, *, key: str) -> bool:
        stmt = select(DedupEvent.key).where(DedupEvent.key == key)
        return db.execute(stmt).first() is not None

    @staticmethod
    def create(db: Session, *, key: str) -> DedupEvent:
        row = DedupEvent(key=key)
        db.add(row)
        return row


class WatchRepository:
    @staticmethod
    def create(db: Session, *, channel_id: int, session_id: str) -> WatchedSession:
        entry = WatchedSession(channel_id=channel_id, session_id=session_id)
        db.add(entry)
        return entry

    @staticmethod
    def delete_by_channel_session(
        db: Session,
        *,
        channel_id: int,
        session_id: str,
    ) -> int:
        stmt = (
            delete(WatchedSession)
            .where(WatchedSession.channel_id == channel_id)
            .where(WatchedSession.session_id == session_id)
        )
        result = db.execute(stmt)
        return int(result.rowcount or 0)

    @staticmethod
    def get_watch(
        db: Session,
        *,
        channel_id: int,
        session_id: str,
    ) -> WatchedSession | None:
        stmt = (
            select(WatchedSession)
            .where(WatchedSession.channel_id == channel_id)
            .where(WatchedSession.session_id == session_id)
        )
        return db.execute(stmt).scalars().first()

    @staticmethod
    def list_by_session(db: Session, *, session_id: str) -> list[WatchedSession]:
        stmt = select(WatchedSession).where(WatchedSession.session_id == session_id)
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def list_by_channel(db: Session, *, channel_id: int) -> list[WatchedSession]:
        stmt = (
            select(WatchedSession)
            .where(WatchedSession.channel_id == channel_id)
            .order_by(WatchedSession.created_at.desc(), WatchedSession.id.desc())
        )
        return list(db.execute(stmt).scalars().all())


class ImEventOutboxRepository:
    @staticmethod
    def _normalize_id(event_id: uuid.UUID | str) -> uuid.UUID:
        if isinstance(event_id, uuid.UUID):
            return event_id
        return uuid.UUID(str(event_id))

    @staticmethod
    def create_if_absent(
        db: Session,
        *,
        event_key: str,
        event_type: str,
        event_version: int,
        user_id: str,
        session_id: uuid.UUID | None,
        run_id: uuid.UUID | None,
        message_id: int | None,
        user_input_request_id: uuid.UUID | None,
        payload: dict[str, Any],
    ) -> ImEventOutbox:
        existing = ImEventOutboxRepository.get_by_event_key(db, event_key=event_key)
        if existing:
            return existing

        row = ImEventOutbox(
            event_key=event_key,
            event_type=event_type,
            event_version=event_version,
            user_id=user_id,
            session_id=session_id,
            run_id=run_id,
            message_id=message_id,
            user_input_request_id=user_input_request_id,
            payload=payload,
        )
        db.add(row)
        try:
            with db.begin_nested():
                db.flush([row])
        except IntegrityError:
            existing = ImEventOutboxRepository.get_by_event_key(db, event_key=event_key)
            if existing:
                return existing
            raise
        return row

    @staticmethod
    def get_by_event_key(db: Session, *, event_key: str) -> ImEventOutbox | None:
        stmt = select(ImEventOutbox).where(ImEventOutbox.event_key == event_key)
        return db.execute(stmt).scalars().first()

    @staticmethod
    def claim_due_batch(
        db: Session,
        *,
        limit: int,
        lease_seconds: int,
    ) -> list[ImEventOutbox]:
        now = datetime.now(timezone.utc)
        lease_until = now + timedelta(seconds=max(5, lease_seconds))
        stmt = (
            select(ImEventOutbox)
            .where(ImEventOutbox.status != "delivered")
            .where(ImEventOutbox.next_attempt_at <= now)
            .where(
                or_(
                    ImEventOutbox.lease_expires_at.is_(None),
                    ImEventOutbox.lease_expires_at < now,
                )
            )
            .order_by(ImEventOutbox.created_at.asc(), ImEventOutbox.id.asc())
            .with_for_update(skip_locked=True)
            .limit(limit)
        )
        rows = list(db.execute(stmt).scalars().all())
        if not rows:
            return []

        for row in rows:
            row.status = "sending"
            row.attempt_count = int(row.attempt_count or 0) + 1
            row.lease_expires_at = lease_until
        return rows

    @staticmethod
    def mark_delivered(db: Session, *, event_id: uuid.UUID | str) -> None:
        row = db.get(ImEventOutbox, ImEventOutboxRepository._normalize_id(event_id))
        if row is None:
            return
        row.status = "delivered"
        row.delivered_at = datetime.now(timezone.utc)
        row.lease_expires_at = None
        row.last_error = None

    @staticmethod
    def mark_retry(
        db: Session,
        *,
        event_id: uuid.UUID | str,
        error_message: str,
        delay_seconds: float,
    ) -> None:
        row = db.get(ImEventOutbox, ImEventOutboxRepository._normalize_id(event_id))
        if row is None:
            return
        row.status = "pending"
        row.lease_expires_at = None
        row.last_error = error_message[:4000]
        row.next_attempt_at = datetime.now(timezone.utc) + timedelta(
            seconds=max(0.5, delay_seconds)
        )
