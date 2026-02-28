import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.agent_message import AgentMessage


class MessageRepository:
    """Data access layer for messages."""

    @staticmethod
    def create(
        session_db: Session,
        session_id: uuid.UUID,
        role: str,
        content: dict[str, Any],
        text_preview: str | None = None,
    ) -> AgentMessage:
        """Creates a new message."""
        message = AgentMessage(
            session_id=session_id,
            role=role,
            content=content,
            text_preview=text_preview,
        )
        session_db.add(message)
        return message

    @staticmethod
    def get_by_id(session_db: Session, message_id: int) -> AgentMessage | None:
        """Gets a message by ID."""
        return (
            session_db.query(AgentMessage).filter(AgentMessage.id == message_id).first()
        )

    @staticmethod
    def list_by_session(
        session_db: Session, session_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> list[AgentMessage]:
        """Lists messages for a session."""
        return (
            session_db.query(AgentMessage)
            .filter(AgentMessage.session_id == session_id)
            .order_by(AgentMessage.created_at.asc(), AgentMessage.id.asc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    @staticmethod
    def count_by_session(session_db: Session, session_id: uuid.UUID) -> int:
        """Counts messages for a session."""
        return (
            session_db.query(AgentMessage)
            .filter(AgentMessage.session_id == session_id)
            .count()
        )
