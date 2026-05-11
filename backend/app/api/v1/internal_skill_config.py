from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db, require_internal_token
from app.schemas.response import Response, ResponseSchema
from app.schemas.skill_config import SkillConfigResolveRequest
from app.services.skill_config_service import SkillConfigService

router = APIRouter(prefix="/internal", tags=["internal"])

service = SkillConfigService()


@router.post(
    "/skill-config/resolve",
    response_model=ResponseSchema[dict],
)
async def resolve_skill_config(
    request: SkillConfigResolveRequest,
    _: None = Depends(require_internal_token),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    resolved = service.resolve_user_skill_files(
        db=db,
        user_id=user_id,
        skill_ids=request.skill_ids,
        skill_overrides=request.skill_overrides,
    )
    return Response.success(data=resolved, message="Skill config resolved")
