import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.deliverable_version import DeliverableVersion


class DeliverableVersionRepository:
    """Data access layer for deliverable versions."""

    @staticmethod
    def create(
        session_db: Session,
        session_id: uuid.UUID,
        run_id: uuid.UUID,
        deliverable_id: uuid.UUID,
        file_path: str,
        source_message_id: int | None = None,
        version_no: int = 1,
        file_name: str | None = None,
        mime_type: str | None = None,
        input_refs_json: dict[str, Any] | None = None,
        related_tool_execution_ids_json: dict[str, Any] | None = None,
        detection_metadata_json: dict[str, Any] | None = None,
    ) -> DeliverableVersion:
        """Creates a new deliverable version record."""
        version = DeliverableVersion(
            session_id=session_id,
            run_id=run_id,
            deliverable_id=deliverable_id,
            source_message_id=source_message_id,
            version_no=version_no,
            file_path=file_path,
            file_name=file_name,
            mime_type=mime_type,
            input_refs_json=input_refs_json,
            related_tool_execution_ids_json=related_tool_execution_ids_json,
            detection_metadata_json=detection_metadata_json,
        )
        session_db.add(version)
        return version

    @staticmethod
    def get_by_id(
        session_db: Session, version_id: uuid.UUID
    ) -> DeliverableVersion | None:
        """Gets a deliverable version by ID."""
        return (
            session_db.query(DeliverableVersion)
            .filter(DeliverableVersion.id == version_id)
            .first()
        )

    @staticmethod
    def get_by_session_run_path(
        session_db: Session,
        session_id: uuid.UUID,
        run_id: uuid.UUID,
        file_path: str,
    ) -> DeliverableVersion | None:
        """Gets a deliverable version by natural key (session_id, run_id, file_path)."""
        return (
            session_db.query(DeliverableVersion)
            .filter(
                DeliverableVersion.session_id == session_id,
                DeliverableVersion.run_id == run_id,
                DeliverableVersion.file_path == file_path,
            )
            .first()
        )

    @staticmethod
    def list_by_session(
        session_db: Session, session_id: uuid.UUID
    ) -> list[DeliverableVersion]:
        """Lists all deliverable versions for a session."""
        return (
            session_db.query(DeliverableVersion)
            .filter(DeliverableVersion.session_id == session_id)
            .order_by(DeliverableVersion.created_at.asc())
            .all()
        )

    @staticmethod
    def list_by_run(session_db: Session, run_id: uuid.UUID) -> list[DeliverableVersion]:
        """Lists all deliverable versions for a run."""
        return (
            session_db.query(DeliverableVersion)
            .filter(DeliverableVersion.run_id == run_id)
            .order_by(DeliverableVersion.created_at.asc())
            .all()
        )

    @staticmethod
    def list_by_deliverable(
        session_db: Session, deliverable_id: uuid.UUID
    ) -> list[DeliverableVersion]:
        """Lists all versions for a deliverable."""
        return (
            session_db.query(DeliverableVersion)
            .filter(DeliverableVersion.deliverable_id == deliverable_id)
            .order_by(DeliverableVersion.version_no.asc())
            .all()
        )

    @staticmethod
    def get_latest_by_deliverable(
        session_db: Session, deliverable_id: uuid.UUID
    ) -> DeliverableVersion | None:
        """Gets the latest version for a deliverable by version number."""
        return (
            session_db.query(DeliverableVersion)
            .filter(DeliverableVersion.deliverable_id == deliverable_id)
            .order_by(DeliverableVersion.version_no.desc())
            .first()
        )
