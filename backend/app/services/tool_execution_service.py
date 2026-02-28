import logging
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.tool_execution import ToolExecution
from app.repositories.tool_execution_repository import ToolExecutionRepository
from app.schemas.tool_execution import ToolExecutionDeltaResponse, ToolExecutionResponse

logger = logging.getLogger(__name__)


class ToolExecutionService:
    """Service layer for tool execution queries."""

    def get_tool_executions(
        self,
        db: Session,
        session_id: uuid.UUID,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[ToolExecution]:
        """Gets all tool executions for a session.

        Args:
            db: Database session
            session_id: Session ID

        Returns:
            List of tool executions ordered by creation time
        """
        executions = ToolExecutionRepository.list_by_session(
            db,
            session_id,
            limit=max(1, int(limit)),
            offset=max(0, int(offset)),
        )
        logger.debug(
            f"Retrieved {len(executions)} tool executions for session {session_id}"
        )
        return executions

    def get_tool_execution(self, db: Session, execution_id: uuid.UUID) -> ToolExecution:
        """Gets a tool execution by ID.

        Args:
            db: Database session
            execution_id: Tool execution ID

        Returns:
            The tool execution

        Raises:
            AppException: If tool execution not found
        """
        execution = ToolExecutionRepository.get_by_id(db, execution_id)
        if not execution:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Tool execution not found: {execution_id}",
            )
        return execution

    def get_tool_executions_delta(
        self,
        db: Session,
        session_id: uuid.UUID,
        *,
        after_created_at: datetime | None = None,
        after_id: uuid.UUID | None = None,
        limit: int = 200,
    ) -> ToolExecutionDeltaResponse:
        """Gets incremental tool executions for polling."""
        safe_limit = max(1, min(int(limit), 2000))
        fetched = ToolExecutionRepository.list_by_session_after_cursor(
            db,
            session_id,
            after_created_at=after_created_at,
            after_id=after_id,
            limit=safe_limit + 1,
        )

        has_more = len(fetched) > safe_limit
        items_db = fetched[:safe_limit]
        items = [ToolExecutionResponse.model_validate(e) for e in items_db]

        if items_db:
            next_after_created_at = items_db[-1].created_at
            next_after_id = items_db[-1].id
        else:
            next_after_created_at = after_created_at
            next_after_id = after_id

        return ToolExecutionDeltaResponse(
            items=items,
            next_after_created_at=next_after_created_at,
            next_after_id=next_after_id,
            has_more=has_more,
        )
