import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.core.deps import get_current_user_id, get_db
from app.schemas.mcp_connection import McpConnectionResponse
from app.schemas.permission_policy import PermissionAuditEventResponse
from app.schemas.response import Response
from app.services.mcp_connection_service import McpConnectionService
from app.services.run_service import RunService
from app.services.session_service import SessionService

router = APIRouter(prefix="/runs", tags=["runs-mcp"])

run_service = RunService()
session_service = SessionService()


def _ensure_run_belongs_to_user(db: Session, run_id: uuid.UUID, user_id: str) -> None:
    result = run_service.get_run(db, run_id)
    db_session = session_service.get_session(db, result.session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Run does not belong to the user",
        )


@router.get("/{run_id}/mcp-connections")
def list_mcp_connections(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> Response:
    _ensure_run_belongs_to_user(db, run_id, user_id)
    service = McpConnectionService()
    connections = service.list_run_connections(db, run_id)
    return Response.success(data=[c.model_dump(mode="json") for c in connections])


@router.get("/{run_id}/permission-audit")
def list_permission_audit(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> Response:
    _ensure_run_belongs_to_user(db, run_id, user_id)
    from app.models.permission_audit_event import PermissionAuditEvent

    events = (
        db.query(PermissionAuditEvent)
        .filter(PermissionAuditEvent.run_id == run_id)
        .order_by(PermissionAuditEvent.created_at.asc())
        .all()
    )
    return Response.success(
        data=[
            {
                "id": str(e.id),
                "run_id": str(e.run_id),
                "session_id": str(e.session_id),
                "tool_name": e.tool_name,
                "tool_input": e.tool_input,
                "policy_action": e.policy_action,
                "policy_rule_id": e.policy_rule_id,
                "policy_reason": e.policy_reason,
                "audit_mode": e.audit_mode,
                "context": e.context,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ]
    )
