import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_internal_token
from app.services.mcp_connection_service import McpConnectionService

router = APIRouter(prefix="/internal/mcp-transitions", tags=["internal-mcp"])


class McpTransitionRequest(BaseModel):
    run_id: uuid.UUID
    session_id: uuid.UUID
    server_name: str
    to_state: str
    event_source: str
    error_message: str | None = None
    metadata: dict[str, Any] | None = None


@router.post("")
def record_mcp_transition(
    req: McpTransitionRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_internal_token),
) -> dict[str, str]:
    service = McpConnectionService()
    service.record_transition(
        db,
        run_id=req.run_id,
        session_id=req.session_id,
        server_name=req.server_name,
        to_state=req.to_state,
        event_source=req.event_source,
        error_message=req.error_message,
        metadata=req.metadata,
    )
    db.commit()
    return {"status": "ok"}
