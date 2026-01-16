from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db
from app.schemas.response import Response, ResponseSchema
from app.schemas.user_mcp_config import (
    UserMcpConfigCreateRequest,
    UserMcpConfigResponse,
    UserMcpConfigUpdateRequest,
)
from app.services.user_mcp_config_service import UserMcpConfigService

router = APIRouter(prefix="/mcp-configs", tags=["mcp-configs"])

service = UserMcpConfigService()


@router.get("", response_model=ResponseSchema[list[UserMcpConfigResponse]])
async def list_user_mcp_configs(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.list_configs(db, user_id)
    return Response.success(data=result, message="MCP configs retrieved")


@router.post("", response_model=ResponseSchema[UserMcpConfigResponse])
async def create_user_mcp_config(
    request: UserMcpConfigCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.create_config(db, user_id, request)
    return Response.success(data=result, message="MCP config created")


@router.patch("/{config_id}", response_model=ResponseSchema[UserMcpConfigResponse])
async def update_user_mcp_config(
    config_id: int,
    request: UserMcpConfigUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.update_config(db, user_id, config_id, request)
    return Response.success(data=result, message="MCP config updated")


@router.delete("/{config_id}", response_model=ResponseSchema[dict])
async def delete_user_mcp_config(
    config_id: int,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    service.delete_config(db, user_id, config_id)
    return Response.success(data={"id": config_id}, message="MCP config deleted")
