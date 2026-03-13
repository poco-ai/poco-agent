import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.session_queue_item import AgentSessionQueueItem


class SessionQueueItemRepository:
    """Data access layer for persisted queued queries."""

    ACTIVE_STATUSES = ("queued", "paused")
    PROMOTABLE_STATUS = "queued"

    @staticmethod
    def create(
        session_db: Session,
        *,
        session_id: uuid.UUID,
        sequence_no: int,
        prompt: str,
        permission_mode: str,
        run_config_snapshot: dict | None,
        client_request_id: str | None = None,
    ) -> AgentSessionQueueItem:
        item = AgentSessionQueueItem(
            session_id=session_id,
            sequence_no=sequence_no,
            status="queued",
            prompt=prompt,
            permission_mode=permission_mode,
            run_config_snapshot=run_config_snapshot,
            client_request_id=client_request_id,
        )
        session_db.add(item)
        return item

    @staticmethod
    def get_by_id(
        session_db: Session,
        item_id: uuid.UUID,
    ) -> AgentSessionQueueItem | None:
        return (
            session_db.query(AgentSessionQueueItem)
            .filter(AgentSessionQueueItem.id == item_id)
            .first()
        )

    @staticmethod
    def get_by_id_for_update(
        session_db: Session,
        item_id: uuid.UUID,
    ) -> AgentSessionQueueItem | None:
        return (
            session_db.query(AgentSessionQueueItem)
            .filter(AgentSessionQueueItem.id == item_id)
            .with_for_update()
            .first()
        )

    @staticmethod
    def get_by_client_request_id(
        session_db: Session,
        *,
        session_id: uuid.UUID,
        client_request_id: str,
    ) -> AgentSessionQueueItem | None:
        return (
            session_db.query(AgentSessionQueueItem)
            .filter(AgentSessionQueueItem.session_id == session_id)
            .filter(AgentSessionQueueItem.client_request_id == client_request_id)
            .first()
        )

    @staticmethod
    def list_active_by_session(
        session_db: Session,
        session_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> list[AgentSessionQueueItem]:
        query = (
            session_db.query(AgentSessionQueueItem)
            .filter(AgentSessionQueueItem.session_id == session_id)
            .filter(
                AgentSessionQueueItem.status.in_(
                    SessionQueueItemRepository.ACTIVE_STATUSES
                )
            )
            .order_by(
                AgentSessionQueueItem.sequence_no.asc(),
                AgentSessionQueueItem.created_at.asc(),
            )
        )
        if for_update:
            query = query.with_for_update()
        return query.all()

    @staticmethod
    def count_active_by_session(session_db: Session, session_id: uuid.UUID) -> int:
        return (
            session_db.query(AgentSessionQueueItem)
            .filter(AgentSessionQueueItem.session_id == session_id)
            .filter(
                AgentSessionQueueItem.status.in_(
                    SessionQueueItemRepository.ACTIVE_STATUSES
                )
            )
            .count()
        )

    @staticmethod
    def has_active_items(session_db: Session, session_id: uuid.UUID) -> bool:
        return (
            session_db.query(AgentSessionQueueItem.id)
            .filter(AgentSessionQueueItem.session_id == session_id)
            .filter(
                AgentSessionQueueItem.status.in_(
                    SessionQueueItemRepository.ACTIVE_STATUSES
                )
            )
            .first()
            is not None
        )

    @staticmethod
    def get_head_for_update(
        session_db: Session,
        session_id: uuid.UUID,
    ) -> AgentSessionQueueItem | None:
        return (
            session_db.query(AgentSessionQueueItem)
            .filter(AgentSessionQueueItem.session_id == session_id)
            .filter(
                AgentSessionQueueItem.status
                == SessionQueueItemRepository.PROMOTABLE_STATUS
            )
            .order_by(
                AgentSessionQueueItem.sequence_no.asc(),
                AgentSessionQueueItem.created_at.asc(),
            )
            .with_for_update()
            .first()
        )

    @staticmethod
    def get_last_active_item(
        session_db: Session,
        session_id: uuid.UUID,
    ) -> AgentSessionQueueItem | None:
        return (
            session_db.query(AgentSessionQueueItem)
            .filter(AgentSessionQueueItem.session_id == session_id)
            .filter(
                AgentSessionQueueItem.status.in_(
                    SessionQueueItemRepository.ACTIVE_STATUSES
                )
            )
            .order_by(
                AgentSessionQueueItem.sequence_no.desc(),
                AgentSessionQueueItem.created_at.desc(),
            )
            .first()
        )

    @staticmethod
    def get_max_sequence_no(session_db: Session, session_id: uuid.UUID) -> int:
        value = (
            session_db.query(func.max(AgentSessionQueueItem.sequence_no))
            .filter(AgentSessionQueueItem.session_id == session_id)
            .scalar()
        )
        return int(value or 0)

    @staticmethod
    def get_min_active_sequence_no(
        session_db: Session,
        session_id: uuid.UUID,
    ) -> int | None:
        value = (
            session_db.query(func.min(AgentSessionQueueItem.sequence_no))
            .filter(AgentSessionQueueItem.session_id == session_id)
            .filter(
                AgentSessionQueueItem.status.in_(
                    SessionQueueItemRepository.ACTIVE_STATUSES
                )
            )
            .scalar()
        )
        return int(value) if value is not None else None

    @staticmethod
    def get_min_sequence_no(
        session_db: Session,
        session_id: uuid.UUID,
    ) -> int | None:
        value = (
            session_db.query(func.min(AgentSessionQueueItem.sequence_no))
            .filter(AgentSessionQueueItem.session_id == session_id)
            .scalar()
        )
        return int(value) if value is not None else None

    @staticmethod
    def mark_canceled(
        session_db: Session,
        *,
        session_id: uuid.UUID,
    ) -> int:
        items = SessionQueueItemRepository.list_active_by_session(
            session_db,
            session_id,
            for_update=True,
        )
        for item in items:
            item.status = "canceled"
        return len(items)

    @staticmethod
    def mark_paused(
        session_db: Session,
        *,
        session_id: uuid.UUID,
    ) -> int:
        items = SessionQueueItemRepository.list_active_by_session(
            session_db,
            session_id,
            for_update=True,
        )
        updated = 0
        for item in items:
            if item.status == "queued":
                item.status = "paused"
                updated += 1
        return updated
