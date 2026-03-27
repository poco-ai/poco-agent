import uuid

from sqlalchemy.orm import Session

from app.models.deliverable import Deliverable


class DeliverableRepository:
    """Data access layer for deliverables."""

    @staticmethod
    def create(
        session_db: Session,
        session_id: uuid.UUID,
        kind: str,
        logical_name: str,
        latest_version_id: uuid.UUID | None = None,
    ) -> Deliverable:
        """Creates a new deliverable record."""
        deliverable = Deliverable(
            session_id=session_id,
            kind=kind,
            logical_name=logical_name,
            status="active",
            latest_version_id=latest_version_id,
        )
        session_db.add(deliverable)
        return deliverable

    @staticmethod
    def get_by_id(session_db: Session, deliverable_id: uuid.UUID) -> Deliverable | None:
        """Gets a deliverable by ID."""
        return (
            session_db.query(Deliverable)
            .filter(Deliverable.id == deliverable_id)
            .first()
        )

    @staticmethod
    def get_by_session_kind_logical_name(
        session_db: Session,
        session_id: uuid.UUID,
        kind: str,
        logical_name: str,
    ) -> Deliverable | None:
        """Gets a deliverable by natural key (session_id, kind, logical_name)."""
        return (
            session_db.query(Deliverable)
            .filter(
                Deliverable.session_id == session_id,
                Deliverable.kind == kind,
                Deliverable.logical_name == logical_name,
            )
            .first()
        )

    @staticmethod
    def list_by_session(
        session_db: Session, session_id: uuid.UUID
    ) -> list[Deliverable]:
        """Lists all deliverables for a session."""
        return (
            session_db.query(Deliverable)
            .filter(Deliverable.session_id == session_id)
            .order_by(Deliverable.created_at.asc())
            .all()
        )

    @staticmethod
    def get_or_create(
        session_db: Session,
        session_id: uuid.UUID,
        kind: str,
        logical_name: str,
    ) -> tuple[Deliverable, bool]:
        """Gets an existing deliverable or creates a new one.

        Returns:
            A tuple of (deliverable, created) where created is True if a new
            deliverable was created.
        """
        deliverable = DeliverableRepository.get_by_session_kind_logical_name(
            session_db, session_id, kind, logical_name
        )
        if deliverable is not None:
            return deliverable, False

        deliverable = DeliverableRepository.create(
            session_db, session_id, kind, logical_name
        )
        return deliverable, True
