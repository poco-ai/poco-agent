import logging
import uuid
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.agent_run_mcp_connection import AgentRunMcpConnection
from app.models.agent_run_mcp_connection_event import AgentRunMcpConnectionEvent
from app.repositories.agent_run_mcp_connection_repository import (
    AgentRunMcpConnectionRepository,
)
from app.schemas.mcp_connection import McpConnectionResponse

logger = logging.getLogger(__name__)

VALID_TRANSITIONS: dict[str | None, set[str]] = {
    None: {"requested", "staged"},
    "requested": {"staged", "failed"},
    "staged": {"launching", "failed"},
    "launching": {"connected", "failed"},
    "connected": {"terminated", "failed"},
    "failed": {"launching", "terminated"},
    "terminated": set(),
}


class McpConnectionService:
    def sync_run_connections(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
        run_id: uuid.UUID,
        mcp_statuses: list[dict[str, Any]],
    ) -> None:
        for status in mcp_statuses:
            if not isinstance(status, dict):
                continue
            server_name = status.get("server_name")
            if not isinstance(server_name, str) or not server_name.strip():
                continue
            server_name = server_name.strip()
            existing = AgentRunMcpConnectionRepository.get_by_run_and_server_name(
                db, run_id, server_name
            )
            if existing is None:
                existing = AgentRunMcpConnection(
                    run_id=run_id,
                    session_id=session_id,
                    server_name=server_name,
                    state=str(status.get("status") or "unknown"),
                    last_error=status.get("message")
                    if isinstance(status.get("message"), str)
                    else None,
                    connection_metadata={
                        "message": status.get("message"),
                    },
                )
                AgentRunMcpConnectionRepository.create(db, existing)
                continue

            existing.state = str(status.get("status") or existing.state or "unknown")
            message = status.get("message")
            if isinstance(message, str):
                existing.last_error = message
            existing.connection_metadata = {
                **(
                    existing.connection_metadata
                    if isinstance(existing.connection_metadata, dict)
                    else {}
                ),
                "message": message,
            }
            existing.attempt_count = max(1, int(existing.attempt_count or 0))

    def record_transition(
        self,
        db: Session,
        *,
        run_id: uuid.UUID,
        session_id: uuid.UUID,
        server_name: str,
        to_state: str,
        event_source: str,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        existing = AgentRunMcpConnectionRepository.get_by_run_and_server_name(
            db, run_id, server_name
        )
        from_state = existing.state if existing else None

        if existing and existing.state == to_state:
            return

        allowed = VALID_TRANSITIONS.get(from_state, set())
        if to_state not in allowed:
            logger.warning(
                "invalid_mcp_transition",
                extra={
                    "run_id": str(run_id),
                    "server_name": server_name,
                    "from_state": from_state,
                    "to_state": to_state,
                },
            )
            return

        if existing is None:
            existing = AgentRunMcpConnection(
                run_id=run_id,
                session_id=session_id,
                server_name=server_name,
                state=to_state,
            )
            try:
                with db.begin_nested():
                    AgentRunMcpConnectionRepository.create(db, existing)
                    db.flush()
            except IntegrityError:
                existing = AgentRunMcpConnectionRepository.get_by_run_and_server_name(
                    db, run_id, server_name
                )
                if existing is None:
                    raise

                from_state = existing.state
                if existing.state == to_state:
                    return

                allowed = VALID_TRANSITIONS.get(from_state, set())
                if to_state not in allowed:
                    logger.warning(
                        "invalid_mcp_transition",
                        extra={
                            "run_id": str(run_id),
                            "server_name": server_name,
                            "from_state": from_state,
                            "to_state": to_state,
                        },
                    )
                    return

                existing.state = to_state
        else:
            existing.state = to_state

        if to_state == "failed":
            existing.last_error = error_message
            existing.attempt_count = (existing.attempt_count or 0) + 1
        if to_state == "connected":
            existing.health = "healthy"

        event = AgentRunMcpConnectionEvent(
            connection_id=existing.id,
            run_id=run_id,
            from_state=from_state,
            to_state=to_state,
            event_source=event_source,
            error_message=error_message,
            metadata_=metadata,
        )
        db.add(event)
        db.flush()

    def list_run_connections(
        self, db: Session, run_id: uuid.UUID
    ) -> list[McpConnectionResponse]:
        return [
            McpConnectionResponse.model_validate(item)
            for item in AgentRunMcpConnectionRepository.list_by_run(db, run_id)
        ]
