import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.tool_execution import ToolExecution


class ToolExecutionRepository:
    """Data access layer for tool executions."""

    @staticmethod
    def create(
        session_db: Session,
        session_id: uuid.UUID,
        message_id: int,
        tool_use_id: str | None,
        tool_name: str,
        tool_input: dict[str, Any] | None = None,
        tool_output: dict[str, Any] | None = None,
        result_message_id: int | None = None,
        is_error: bool = False,
        duration_ms: int | None = None,
    ) -> ToolExecution:
        """Creates a new tool execution record."""
        tool_execution = ToolExecution(
            session_id=session_id,
            message_id=message_id,
            tool_use_id=tool_use_id,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
            result_message_id=result_message_id,
            is_error=is_error,
            duration_ms=duration_ms,
        )
        session_db.add(tool_execution)
        return tool_execution

    @staticmethod
    def get_by_id(session_db: Session, execution_id: uuid.UUID) -> ToolExecution | None:
        """Gets a tool execution by ID."""
        return (
            session_db.query(ToolExecution)
            .filter(ToolExecution.id == execution_id)
            .first()
        )

    @staticmethod
    def get_by_session_and_tool_use_id(
        session_db: Session,
        session_id: uuid.UUID,
        tool_use_id: str,
    ) -> ToolExecution | None:
        """Gets a tool execution by (session_id, tool_use_id)."""
        return (
            session_db.query(ToolExecution)
            .filter(
                ToolExecution.session_id == session_id,
                ToolExecution.tool_use_id == tool_use_id,
            )
            .first()
        )

    @staticmethod
    def list_by_session(
        session_db: Session, session_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> list[ToolExecution]:
        """Lists tool executions for a session."""
        return (
            session_db.query(ToolExecution)
            .filter(ToolExecution.session_id == session_id)
            .order_by(ToolExecution.created_at.asc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    @staticmethod
    def list_by_session_after_cursor(
        session_db: Session,
        session_id: uuid.UUID,
        *,
        after_created_at: datetime | None = None,
        after_id: uuid.UUID | None = None,
        limit: int = 100,
    ) -> list[ToolExecution]:
        """Lists tool executions for a session using a composite cursor."""
        query = session_db.query(ToolExecution).filter(
            ToolExecution.session_id == session_id
        )

        if after_created_at is not None:
            if after_id is not None:
                query = query.filter(
                    or_(
                        ToolExecution.created_at > after_created_at,
                        and_(
                            ToolExecution.created_at == after_created_at,
                            ToolExecution.id > after_id,
                        ),
                    )
                )
            else:
                query = query.filter(ToolExecution.created_at > after_created_at)

        return (
            query.order_by(ToolExecution.created_at.asc(), ToolExecution.id.asc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def list_unfinished_by_session(
        session_db: Session, session_id: uuid.UUID
    ) -> list[ToolExecution]:
        """Lists tool executions that have not produced a ToolResultBlock yet."""
        return (
            session_db.query(ToolExecution)
            .filter(ToolExecution.session_id == session_id)
            .filter(ToolExecution.tool_output.is_(None))
            .order_by(ToolExecution.created_at.asc())
            .all()
        )

    @staticmethod
    def list_by_message(session_db: Session, message_id: int) -> list[ToolExecution]:
        """Lists tool executions for a message."""
        return (
            session_db.query(ToolExecution)
            .filter(ToolExecution.message_id == message_id)
            .order_by(ToolExecution.created_at.asc())
            .all()
        )

    @staticmethod
    def count_by_session(session_db: Session, session_id: uuid.UUID) -> int:
        """Counts tool executions for a session."""
        return (
            session_db.query(ToolExecution)
            .filter(ToolExecution.session_id == session_id)
            .count()
        )
