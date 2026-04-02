from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db
from app.schemas.preset import (
    PresetCreateRequest,
    PresetResponse,
    PresetUpdateRequest,
)
from app.schemas.response import Response, ResponseSchema
from app.services.preset_service import PresetService

router = APIRouter(prefix="/presets", tags=["presets"])

service = PresetService()


@router.get("", response_model=ResponseSchema[list[PresetResponse]])
async def list_presets(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.list_presets(db, user_id)
    return Response.success(data=result, message="Presets retrieved successfully")


@router.get("/{preset_id}", response_model=ResponseSchema[PresetResponse])
async def get_preset(
    preset_id: int,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.get_preset(db, user_id, preset_id)
    return Response.success(data=result, message="Preset retrieved successfully")


@router.post("", response_model=ResponseSchema[PresetResponse])
async def create_preset(
    request: PresetCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.create_preset(db, user_id, request)
    return Response.success(data=result, message="Preset created successfully")


@router.put("/{preset_id}", response_model=ResponseSchema[PresetResponse])
async def update_preset(
    preset_id: int,
    request: PresetUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.update_preset(db, user_id, preset_id, request)
    return Response.success(data=result, message="Preset updated successfully")


@router.delete("/{preset_id}", response_model=ResponseSchema[dict])
async def delete_preset(
    preset_id: int,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    service.delete_preset(db, user_id, preset_id)
    return Response.success(
        data={"id": preset_id}, message="Preset deleted successfully"
    )
