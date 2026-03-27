import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db
from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.schemas.deliverable import DeliverableResponse, DeliverableVersionResponse
from app.schemas.response import Response, ResponseSchema
from app.schemas.tool_execution import ToolExecutionResponse
from app.services.deliverable_service import DeliverableService
from app.services.session_service import SessionService

router = APIRouter(prefix="/sessions", tags=["deliverables"])

deliverable_service = DeliverableService()
session_service = SessionService()


def _ensure_session_owner(db: Session, session_id: uuid.UUID, user_id: str) -> None:
    db_session = session_service.get_session(db, session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Session does not belong to the user",
        )


@router.get(
    "/{session_id}/deliverables",
    response_model=ResponseSchema[list[DeliverableResponse]],
)
async def list_session_deliverables(
    session_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    _ensure_session_owner(db, session_id, user_id)
    payload = deliverable_service.list_by_session(db, session_id=session_id)
    return Response.success(data=payload, message="Deliverables retrieved")


@router.get(
    "/{session_id}/deliverables/{deliverable_id}",
    response_model=ResponseSchema[DeliverableResponse],
)
async def get_session_deliverable(
    session_id: uuid.UUID,
    deliverable_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    _ensure_session_owner(db, session_id, user_id)
    payload = deliverable_service.get_deliverable(
        db,
        session_id=session_id,
        deliverable_id=deliverable_id,
    )
    return Response.success(data=payload, message="Deliverable retrieved")


@router.get(
    "/{session_id}/deliverables/{deliverable_id}/versions",
    response_model=ResponseSchema[list[DeliverableVersionResponse]],
)
async def list_session_deliverable_versions(
    session_id: uuid.UUID,
    deliverable_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    _ensure_session_owner(db, session_id, user_id)
    payload = deliverable_service.list_versions_by_deliverable(
        db,
        session_id=session_id,
        deliverable_id=deliverable_id,
    )
    return Response.success(data=payload, message="Deliverable versions retrieved")


@router.get(
    "/{session_id}/deliverable-versions/{version_id}",
    response_model=ResponseSchema[DeliverableVersionResponse],
)
async def get_session_deliverable_version(
    session_id: uuid.UUID,
    version_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    _ensure_session_owner(db, session_id, user_id)
    payload = deliverable_service.get_version(
        db,
        session_id=session_id,
        version_id=version_id,
    )
    return Response.success(data=payload, message="Deliverable version retrieved")


@router.get(
    "/{session_id}/deliverable-versions/{version_id}/tool-executions",
    response_model=ResponseSchema[list[ToolExecutionResponse]],
)
async def get_session_deliverable_version_tool_executions(
    session_id: uuid.UUID,
    version_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    _ensure_session_owner(db, session_id, user_id)
    payload = deliverable_service.get_version_tool_executions(
        db,
        session_id=session_id,
        version_id=version_id,
    )
    return Response.success(
        data=payload,
        message="Deliverable version tool executions retrieved",
    )
