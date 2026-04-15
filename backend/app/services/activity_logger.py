import logging
import uuid

from sqlalchemy.orm import Session

from app.core.audit import AuditConfig, AuditEvent
from app.models.activity_log import ActivityLog
from app.repositories.activity_log_repository import ActivityLogRepository
from app.schemas.activity_log import ActivityLogResponse

logger = logging.getLogger(__name__)


class ActivityLogger:
    def __init__(self, audit_config: AuditConfig | None = None) -> None:
        self._audit_config = audit_config or AuditConfig()

    def log_activity(self, db: Session, event: AuditEvent) -> ActivityLogResponse | None:
        if not self._audit_config.is_enabled(event.action):
            return None

        try:
            activity_log = ActivityLogRepository.create(
                db,
                ActivityLog(
                    workspace_id=uuid.UUID(str(event.workspace_id)),
                    actor_user_id=event.actor_user_id,
                    action=event.action,
                    target_type=event.target_type,
                    target_id=event.target_id,
                    metadata_json=event.metadata,
                ),
            )
            db.commit()
            db.refresh(activity_log)
            return ActivityLogResponse.model_validate(activity_log)
        except Exception:
            db.rollback()
            logger.exception(
                "activity_log_write_failed",
                extra={
                    "action": event.action,
                    "workspace_id": str(event.workspace_id),
                    "target_type": event.target_type,
                    "target_id": event.target_id,
                },
            )
            return None

    def list_workspace_activity(
        self,
        db: Session,
        workspace_id: uuid.UUID,
        *,
        limit: int = 50,
    ) -> list[ActivityLogResponse]:
        logs = ActivityLogRepository.list_by_workspace(db, workspace_id, limit=limit)
        return [ActivityLogResponse.model_validate(item) for item in logs]
