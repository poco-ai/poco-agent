from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db
from app.schemas.response import Response, ResponseSchema
from app.schemas.skill import SkillCreateRequest, SkillResponse, SkillUpdateRequest
from app.services.skill_service import SkillService

router = APIRouter(prefix="/skills", tags=["skills"])

service = SkillService()


@router.get("", response_model=ResponseSchema[list[SkillResponse]])
async def list_skills(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.list_skills(db, user_id=user_id)
    return Response.success(data=result, message="Skills retrieved")


@router.get("/{skill_id}", response_model=ResponseSchema[SkillResponse])
async def get_skill(
    skill_id: int,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.get_skill(db, user_id, skill_id)
    return Response.success(data=result, message="Skill retrieved")


@router.post("", response_model=ResponseSchema[SkillResponse])
async def create_skill(
    request: SkillCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.create_skill(db, user_id, request)
    return Response.success(data=result, message="Skill created")


@router.patch("/{skill_id}", response_model=ResponseSchema[SkillResponse])
async def update_skill(
    skill_id: int,
    request: SkillUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.update_skill(db, user_id, skill_id, request)
    return Response.success(data=result, message="Skill updated")


@router.delete("/{skill_id}", response_model=ResponseSchema[dict])
async def delete_skill(
    skill_id: int,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    service.delete_skill(db, user_id, skill_id)
    return Response.success(data={"id": skill_id}, message="Skill deleted")
