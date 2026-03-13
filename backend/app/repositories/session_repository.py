import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.agent_session import AgentSession


class SessionRepository:
    """Data access layer for sessions."""

    @staticmethod
    def create(
        session_db: Session,
        user_id: str,
        config: dict[str, Any] | None = None,
        project_id: uuid.UUID | None = None,
        *,
        kind: str = "chat",
    ) -> AgentSession:
        db_session = AgentSession(
            user_id=user_id,
            config_snapshot=config,
            project_id=project_id,
            kind=kind,
            status="pending",
        )
        session_db.add(db_session)
        return db_session

    @staticmethod
    def get_by_id(session_db: Session, session_id: uuid.UUID) -> AgentSession | None:
        return (
            session_db.query(AgentSession)
            .filter(
                AgentSession.id == session_id,
                AgentSession.is_deleted.is_(False),
            )
            .first()
        )

    @staticmethod
    def get_by_id_for_update(
        session_db: Session, session_id: uuid.UUID
    ) -> AgentSession | None:
        return (
            session_db.query(AgentSession)
            .filter(
                AgentSession.id == session_id,
                AgentSession.is_deleted.is_(False),
            )
            .with_for_update()
            .first()
        )

    @staticmethod
    def get_by_sdk_session_id(
        session_db: Session, sdk_session_id: str
    ) -> AgentSession | None:
        return (
            session_db.query(AgentSession)
            .filter(
                AgentSession.sdk_session_id == sdk_session_id,
                AgentSession.is_deleted.is_(False),
            )
            .first()
        )

    @staticmethod
    def list_by_user(
        session_db: Session,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        project_id: uuid.UUID | None = None,
        kind: str | None = None,
    ) -> list[AgentSession]:
        query = session_db.query(AgentSession).filter(
            AgentSession.user_id == user_id,
            AgentSession.is_deleted.is_(False),
        )
        if kind:
            query = query.filter(AgentSession.kind == kind)
        if project_id is not None:
            query = query.filter(AgentSession.project_id == project_id)
        return (
            query.order_by(AgentSession.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    @staticmethod
    def list_all(
        session_db: Session,
        limit: int = 100,
        offset: int = 0,
        project_id: uuid.UUID | None = None,
        kind: str | None = None,
    ) -> list[AgentSession]:
        query = session_db.query(AgentSession).filter(
            AgentSession.is_deleted.is_(False)
        )
        if kind:
            query = query.filter(AgentSession.kind == kind)
        if project_id is not None:
            query = query.filter(AgentSession.project_id == project_id)
        return (
            query.order_by(AgentSession.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    @staticmethod
    def count_by_user(session_db: Session, user_id: str) -> int:
        return (
            session_db.query(AgentSession)
            .filter(
                AgentSession.user_id == user_id,
                AgentSession.is_deleted.is_(False),
            )
            .count()
        )

    @staticmethod
    def clear_project_id(session_db: Session, project_id: uuid.UUID) -> None:
        session_db.query(AgentSession).filter(
            AgentSession.project_id == project_id
        ).update({AgentSession.project_id: None}, synchronize_session=False)
