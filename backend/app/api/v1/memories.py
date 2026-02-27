from typing import Any

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse

from app.core.deps import get_current_user_id
from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.core.settings import get_settings
from app.schemas.memory import (
    MemoryConfigureRequest,
    MemoryCreateRequest,
    MemorySearchRequest,
    MemoryUpdateRequest,
)
from app.schemas.response import Response, ResponseSchema
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/memories", tags=["memories"])

memory_service = MemoryService()


def require_internal_token(
    x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
) -> None:
    settings = get_settings()
    if not settings.internal_api_token:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Internal API token is not configured",
        )
    if not x_internal_token or x_internal_token != settings.internal_api_token:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Invalid internal token",
        )


@router.post("/configure", response_model=ResponseSchema[dict[str, bool]])
async def configure_memory(
    request: MemoryConfigureRequest,
    _: None = Depends(require_internal_token),
) -> JSONResponse:
    memory_service.configure(enabled=request.enabled, config=request.config)
    return Response.success(
        data={"configured": True, "enabled": memory_service.is_enabled()},
        message="Memory configuration updated",
    )


@router.post("", response_model=ResponseSchema[Any])
async def create_memories(
    request: MemoryCreateRequest,
    user_id: str = Depends(get_current_user_id),
) -> JSONResponse:
    result = memory_service.create_memories(user_id=user_id, request=request)
    return Response.success(data=result, message="Memory stored successfully")


@router.get("", response_model=ResponseSchema[Any])
async def list_memories(
    agent_id: str | None = None,
    run_id: str | None = None,
    user_id: str = Depends(get_current_user_id),
) -> JSONResponse:
    result = memory_service.list_memories(
        user_id=user_id,
        agent_id=agent_id,
        run_id=run_id,
    )
    return Response.success(data=result, message="Memories retrieved successfully")


@router.post("/search", response_model=ResponseSchema[Any])
async def search_memories(
    request: MemorySearchRequest,
    user_id: str = Depends(get_current_user_id),
) -> JSONResponse:
    result = memory_service.search_memories(user_id=user_id, request=request)
    return Response.success(data=result, message="Memories searched successfully")


@router.get("/{memory_id}", response_model=ResponseSchema[Any])
async def get_memory(memory_id: str) -> JSONResponse:
    result = memory_service.get_memory(memory_id)
    return Response.success(data=result, message="Memory retrieved successfully")


@router.put("/{memory_id}", response_model=ResponseSchema[Any])
async def update_memory(
    memory_id: str,
    request: MemoryUpdateRequest,
) -> JSONResponse:
    result = memory_service.update_memory(memory_id=memory_id, data=request.data)
    return Response.success(data=result, message="Memory updated successfully")


@router.get("/{memory_id}/history", response_model=ResponseSchema[Any])
async def get_memory_history(memory_id: str) -> JSONResponse:
    result = memory_service.get_memory_history(memory_id=memory_id)
    return Response.success(
        data=result, message="Memory history retrieved successfully"
    )


@router.delete("/{memory_id}", response_model=ResponseSchema[dict[str, str]])
async def delete_memory(memory_id: str) -> JSONResponse:
    memory_service.delete_memory(memory_id=memory_id)
    return Response.success(
        data={"id": memory_id}, message="Memory deleted successfully"
    )


@router.delete("", response_model=ResponseSchema[dict[str, bool]])
async def delete_all_memories(
    agent_id: str | None = None,
    run_id: str | None = None,
    user_id: str = Depends(get_current_user_id),
) -> JSONResponse:
    memory_service.delete_all_memories(
        user_id=user_id,
        agent_id=agent_id,
        run_id=run_id,
    )
    return Response.success(
        data={"deleted": True},
        message="All relevant memories deleted successfully",
    )


@router.post("/reset", response_model=ResponseSchema[dict[str, bool]])
async def reset_memories(
    _: None = Depends(require_internal_token),
) -> JSONResponse:
    memory_service.reset()
    return Response.success(
        data={"reset": True}, message="All memories reset successfully"
    )
