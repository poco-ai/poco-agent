import uuid

from sqlalchemy.orm import Session

from app.models.agent_run_mcp_connection import AgentRunMcpConnection


class AgentRunMcpConnectionRepository:
    @staticmethod
    def get_by_run_and_server_name(
        session_db: Session, run_id: uuid.UUID, server_name: str
    ) -> AgentRunMcpConnection | None:
        return (
            session_db.query(AgentRunMcpConnection)
            .filter(
                AgentRunMcpConnection.run_id == run_id,
                AgentRunMcpConnection.server_name == server_name,
            )
            .first()
        )

    @staticmethod
    def list_by_run(
        session_db: Session, run_id: uuid.UUID
    ) -> list[AgentRunMcpConnection]:
        return (
            session_db.query(AgentRunMcpConnection)
            .filter(AgentRunMcpConnection.run_id == run_id)
            .order_by(AgentRunMcpConnection.created_at.asc())
            .all()
        )

    @staticmethod
    def create(
        session_db: Session, item: AgentRunMcpConnection
    ) -> AgentRunMcpConnection:
        session_db.add(item)
        return item
