import uuid

from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog


class ActivityLogRepository:
    @staticmethod
    def create(session_db: Session, activity_log: ActivityLog) -> ActivityLog:
        session_db.add(activity_log)
        return activity_log

    @staticmethod
    def list_by_workspace(
        session_db: Session,
        workspace_id: uuid.UUID,
        *,
        limit: int = 50,
    ) -> list[ActivityLog]:
        return (
            session_db.query(ActivityLog)
            .filter(ActivityLog.workspace_id == workspace_id)
            .order_by(ActivityLog.created_at.desc())
            .limit(limit)
            .all()
        )
