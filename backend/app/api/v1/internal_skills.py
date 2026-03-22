import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_user_id_by_session_id, require_internal_token
from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.repositories.session_repository import SessionRepository
from app.schemas.response import Response, ResponseSchema
from app.schemas.workspace import SubmitSkillRequest, SubmitSkillResponse
from app.services.pending_skill_creation_service import PendingSkillCreationService

router = APIRouter(prefix="/internal", tags=["internal"])
pending_skill_creation_service = PendingSkillCreationService()


@router.post(
    "/skills/submit-from-workspace",
    response_model=ResponseSchema[SubmitSkillResponse],
)
async def submit_skill_from_workspace(
    request: SubmitSkillRequest,
    session_id: uuid.UUID,
    _: None = Depends(require_internal_token),
    user_id: str = Depends(get_user_id_by_session_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    session = SessionRepository.get_by_id(db, session_id)
    if session is None:
        raise AppException(
            error_code=ErrorCode.NOT_FOUND,
            message=f"Session not found: {session_id}",
        )

    pending = pending_skill_creation_service.submit_from_workspace(
        db,
        user_id=user_id,
        session=session,
        folder_path=request.folder_path,
        skill_name=request.skill_name,
        workspace_files_prefix=request.workspace_files_prefix,
    )
    db.commit()
    db.refresh(pending)
    return Response.success(
        data=SubmitSkillResponse(
            pending_id=str(pending.id),
            status=pending.status,
        ),
        message="Skill submission queued successfully",
    )
