from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.im_event_outbox import ImEventOutbox


class ImEventOutboxRepository:
    @staticmethod
    def _normalize_id(event_id: uuid.UUID | str) -> uuid.UUID:
        if isinstance(event_id, uuid.UUID):
            return event_id
        return uuid.UUID(str(event_id))

    @staticmethod
    def create_if_absent(
        session_db: Session,
        *,
        event_key: str,
        event_type: str,
        event_version: int,
        user_id: str,
        session_id: uuid.UUID | None,
        run_id: uuid.UUID | None,
        message_id: int | None,
        user_input_request_id: uuid.UUID | None,
        payload: dict,
    ) -> ImEventOutbox:
        existing = ImEventOutboxRepository.get_by_event_key(
            session_db, event_key=event_key
        )
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
        session_db.add(row)
        try:
            with session_db.begin_nested():
                session_db.flush()
        except IntegrityError:
            existing = ImEventOutboxRepository.get_by_event_key(
                session_db, event_key=event_key
            )
            if existing:
                return existing
            raise
        return row

    @staticmethod
    def get_by_event_key(
        session_db: Session, *, event_key: str
    ) -> ImEventOutbox | None:
        stmt = select(ImEventOutbox).where(ImEventOutbox.event_key == event_key)
        return session_db.execute(stmt).scalars().first()

    @staticmethod
    def claim_due_batch(
        session_db: Session,
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
        rows = list(session_db.execute(stmt).scalars().all())
        if not rows:
            return []

        for row in rows:
            row.status = "sending"
            row.attempt_count = int(row.attempt_count or 0) + 1
            row.lease_expires_at = lease_until
        session_db.commit()

        for row in rows:
            session_db.refresh(row)
        return rows

    @staticmethod
    def mark_delivered(session_db: Session, *, event_id: uuid.UUID | str) -> None:
        row = session_db.get(
            ImEventOutbox,
            ImEventOutboxRepository._normalize_id(event_id),
        )
        if row is None:
            return
        row.status = "delivered"
        row.delivered_at = datetime.now(timezone.utc)
        row.lease_expires_at = None
        row.last_error = None
        session_db.commit()

    @staticmethod
    def mark_retry(
        session_db: Session,
        *,
        event_id: uuid.UUID | str,
        error_message: str,
        delay_seconds: float,
    ) -> None:
        row = session_db.get(
            ImEventOutbox,
            ImEventOutboxRepository._normalize_id(event_id),
        )
        if row is None:
            return
        row.status = "pending"
        row.lease_expires_at = None
        row.last_error = error_message[:4000]
        row.next_attempt_at = datetime.now(timezone.utc) + timedelta(
            seconds=max(0.5, delay_seconds)
        )
        session_db.commit()
