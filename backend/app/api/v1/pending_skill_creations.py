import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db
from app.schemas.pending_skill_creation import (
    PendingSkillCreationCancelRequest,
    PendingSkillCreationConfirmRequest,
    PendingSkillCreationResponse,
)
from app.schemas.response import Response, ResponseSchema
from app.services.pending_skill_creation_service import PendingSkillCreationService

router = APIRouter(prefix="/pending-skill-creations", tags=["skills"])

service = PendingSkillCreationService()


@router.get(
    "",
    response_model=ResponseSchema[list[PendingSkillCreationResponse]],
)
def list_pending_skill_creations(
    session_id: uuid.UUID | None = Query(default=None),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.list_pending_for_user(
        db,
        user_id=user_id,
        session_id=session_id,
    )
    return Response.success(data=result, message="Pending skill creations retrieved")


@router.get(
    "/{creation_id}",
    response_model=ResponseSchema[PendingSkillCreationResponse],
)
def get_pending_skill_creation(
    creation_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.get_creation(db, user_id=user_id, creation_id=creation_id)
    return Response.success(data=result, message="Pending skill creation retrieved")


@router.post(
    "/{creation_id}/confirm",
    response_model=ResponseSchema[PendingSkillCreationResponse],
)
def confirm_pending_skill_creation(
    creation_id: uuid.UUID,
    request: PendingSkillCreationConfirmRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.confirm(
        db,
        user_id=user_id,
        creation_id=creation_id,
        request=request,
    )
    return Response.success(data=result, message="Pending skill creation confirmed")


@router.post(
    "/{creation_id}/cancel",
    response_model=ResponseSchema[PendingSkillCreationResponse],
)
def cancel_pending_skill_creation(
    creation_id: uuid.UUID,
    request: PendingSkillCreationCancelRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.cancel(
        db,
        user_id=user_id,
        creation_id=creation_id,
        reason=request.reason,
    )
    return Response.success(data=result, message="Pending skill creation canceled")
