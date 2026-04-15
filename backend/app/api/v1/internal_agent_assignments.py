from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_internal_token
from app.schemas.agent_assignment import (
    AgentAssignmentDispatchRequest,
    AgentAssignmentDispatchResponse,
)
from app.schemas.response import Response, ResponseSchema
from app.services.agent_assignment_service import AgentAssignmentService

router = APIRouter(prefix="/internal/agent-assignments", tags=["internal-agent-assignments"])

service = AgentAssignmentService()


@router.post(
    "/dispatch-due",
    response_model=ResponseSchema[AgentAssignmentDispatchResponse],
)
async def dispatch_due_agent_assignments(
    request: AgentAssignmentDispatchRequest,
    _: None = Depends(require_internal_token),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.dispatch_due(db, limit=request.limit)
    return Response.success(
        data=result,
        message="Agent assignments dispatched",
    )
