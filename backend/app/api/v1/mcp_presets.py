from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db
from app.schemas.mcp_preset import (
    McpPresetCreateRequest,
    McpPresetResponse,
    McpPresetUpdateRequest,
)
from app.schemas.response import Response, ResponseSchema
from app.services.mcp_preset_service import McpPresetService

router = APIRouter(prefix="/mcp-presets", tags=["mcp-presets"])

mcp_preset_service = McpPresetService()


@router.get("", response_model=ResponseSchema[list[McpPresetResponse]])
async def list_mcp_presets(
    include_inactive: bool = Query(default=False),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = mcp_preset_service.list_presets(
        db, user_id=user_id, include_inactive=include_inactive
    )
    return Response.success(data=result, message="MCP presets retrieved")


@router.get("/{preset_id}", response_model=ResponseSchema[McpPresetResponse])
async def get_mcp_preset(
    preset_id: int,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = mcp_preset_service.get_preset(db, user_id, preset_id)
    return Response.success(data=result, message="MCP preset retrieved")


@router.post("", response_model=ResponseSchema[McpPresetResponse])
async def create_mcp_preset(
    request: McpPresetCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = mcp_preset_service.create_preset(db, user_id, request)
    return Response.success(data=result, message="MCP preset created")


@router.patch("/{preset_id}", response_model=ResponseSchema[McpPresetResponse])
async def update_mcp_preset(
    preset_id: int,
    request: McpPresetUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = mcp_preset_service.update_preset(db, user_id, preset_id, request)
    return Response.success(data=result, message="MCP preset updated")


@router.delete("/{preset_id}", response_model=ResponseSchema[dict])
async def delete_mcp_preset(
    preset_id: int,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    mcp_preset_service.delete_preset(db, user_id, preset_id)
    return Response.success(data={"id": preset_id}, message="MCP preset deleted")
