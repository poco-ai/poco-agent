import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_internal_token
from app.models.permission_audit_event import PermissionAuditEvent

router = APIRouter(prefix="/internal/permission-audit", tags=["internal-audit"])


class PermissionAuditRequest(BaseModel):
    run_id: uuid.UUID
    session_id: uuid.UUID
    tool_name: str
    tool_input: dict[str, Any] | None = None
    policy_action: str
    policy_rule_id: str | None = None
    policy_reason: str | None = None
    audit_mode: bool = True
    context: dict[str, Any] | None = None


@router.post("")
def record_permission_audit(
    req: PermissionAuditRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_internal_token),
) -> dict[str, str]:
    event = PermissionAuditEvent(
        run_id=req.run_id,
        session_id=req.session_id,
        tool_name=req.tool_name,
        tool_input=req.tool_input,
        policy_action=req.policy_action,
        policy_rule_id=req.policy_rule_id,
        policy_reason=req.policy_reason,
        audit_mode=req.audit_mode,
        context=req.context,
    )
    db.add(event)
    db.commit()
    return {"status": "ok"}
