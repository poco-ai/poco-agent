from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db
from app.schemas.execution_settings import (
    ExecutionSettings,
    ExecutionSettingsUpdateRequest,
)
from app.schemas.response import Response, ResponseSchema
from app.services.execution_settings_service import ExecutionSettingsService

router = APIRouter(prefix="/execution-settings", tags=["execution-settings"])

service = ExecutionSettingsService()


@router.get("", response_model=ResponseSchema[ExecutionSettings])
async def get_execution_settings(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.get_or_create(db, user_id)
    return Response.success(data=result, message="Execution settings retrieved")


@router.patch("", response_model=ResponseSchema[ExecutionSettings])
async def update_execution_settings(
    request: ExecutionSettingsUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.update(db, user_id, request.settings)
    return Response.success(data=result, message="Execution settings updated")


@router.get("/catalog", response_model=ResponseSchema[dict])
async def get_execution_settings_catalog() -> JSONResponse:
    return Response.success(
        data={
            "hook_keys": [
                "workspace",
                "todo",
                "callback",
                "run_snapshot",
                "browser_screenshot",
            ],
            "hook_phases": ["setup", "pre_query", "message", "error", "teardown"],
            "workspace_strategies": [
                "clone",
                "worktree",
                "sparse-clone",
                "sparse-worktree",
            ],
        },
        message="Execution settings catalog retrieved",
    )
