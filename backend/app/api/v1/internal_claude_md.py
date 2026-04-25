from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db, require_internal_token
from app.schemas.claude_md import ClaudeMdResponse
from app.schemas.response import Response, ResponseSchema
from app.services.claude_md_service import ClaudeMdService

router = APIRouter(prefix="/internal", tags=["internal"])

service = ClaudeMdService()


@router.get("/claude-md", response_model=ResponseSchema[ClaudeMdResponse])
async def get_claude_md_internal(
    _: None = Depends(require_internal_token),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.get_effective_settings(db, user_id=user_id)
    return Response.success(data=result, message="CLAUDE.md retrieved")
