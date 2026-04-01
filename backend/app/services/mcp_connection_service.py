import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.agent_run_mcp_connection import AgentRunMcpConnection
from app.repositories.agent_run_mcp_connection_repository import (
    AgentRunMcpConnectionRepository,
)
from app.schemas.mcp_connection import McpConnectionResponse


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

    def list_run_connections(
        self, db: Session, run_id: uuid.UUID
    ) -> list[McpConnectionResponse]:
        return [
            McpConnectionResponse.model_validate(item)
            for item in AgentRunMcpConnectionRepository.list_by_run(db, run_id)
        ]
