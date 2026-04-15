import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.agent_assignment import AgentAssignment


class AgentAssignmentRepository:
    @staticmethod
    def create(session_db: Session, assignment: AgentAssignment) -> AgentAssignment:
        session_db.add(assignment)
        return assignment

    @staticmethod
    def get_by_id(
        session_db: Session,
        assignment_id: uuid.UUID,
    ) -> AgentAssignment | None:
        return (
            session_db.query(AgentAssignment)
            .filter(AgentAssignment.id == assignment_id)
            .first()
        )

    @staticmethod
    def get_by_issue_id(
        session_db: Session,
        issue_id: uuid.UUID,
    ) -> AgentAssignment | None:
        return (
            session_db.query(AgentAssignment)
            .filter(AgentAssignment.issue_id == issue_id)
            .first()
        )

    @staticmethod
    def get_by_session_id(
        session_db: Session,
        session_id: uuid.UUID,
    ) -> AgentAssignment | None:
        return (
            session_db.query(AgentAssignment)
            .filter(AgentAssignment.session_id == session_id)
            .first()
        )

    @staticmethod
    def list_schedulable(
        session_db: Session,
        *,
        limit: int,
    ) -> list[AgentAssignment]:
        return (
            session_db.query(AgentAssignment)
            .filter(AgentAssignment.trigger_mode == "scheduled_task")
            .filter(AgentAssignment.status.in_(["pending", "completed"]))
            .filter(AgentAssignment.schedule_cron.is_not(None))
            .order_by(AgentAssignment.updated_at.asc())
            .with_for_update(skip_locked=True)
            .limit(limit)
            .all()
        )

    @staticmethod
    def mark_released(session_db: Session, assignment: AgentAssignment) -> None:
        assignment.container_id = None
        assignment.updated_at = datetime.now(timezone.utc)
