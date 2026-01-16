from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db
from app.schemas.response import Response, ResponseSchema
from app.schemas.skill_preset import (
    SkillPresetCreateRequest,
    SkillPresetResponse,
    SkillPresetUpdateRequest,
)
from app.services.skill_preset_service import SkillPresetService

router = APIRouter(prefix="/skill-presets", tags=["skill-presets"])

service = SkillPresetService()


@router.get("", response_model=ResponseSchema[list[SkillPresetResponse]])
async def list_skill_presets(
    include_inactive: bool = Query(default=False),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.list_presets(
        db, user_id=user_id, include_inactive=include_inactive
    )
    return Response.success(data=result, message="Skill presets retrieved")


@router.get("/{preset_id}", response_model=ResponseSchema[SkillPresetResponse])
async def get_skill_preset(
    preset_id: int,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.get_preset(db, user_id, preset_id)
    return Response.success(data=result, message="Skill preset retrieved")


@router.post("", response_model=ResponseSchema[SkillPresetResponse])
async def create_skill_preset(
    request: SkillPresetCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.create_preset(db, user_id, request)
    return Response.success(data=result, message="Skill preset created")


@router.patch("/{preset_id}", response_model=ResponseSchema[SkillPresetResponse])
async def update_skill_preset(
    preset_id: int,
    request: SkillPresetUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.update_preset(db, user_id, preset_id, request)
    return Response.success(data=result, message="Skill preset updated")


@router.delete("/{preset_id}", response_model=ResponseSchema[dict])
async def delete_skill_preset(
    preset_id: int,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    service.delete_preset(db, user_id, preset_id)
    return Response.success(data={"id": preset_id}, message="Skill preset deleted")
