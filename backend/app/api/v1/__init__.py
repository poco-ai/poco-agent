from fastapi import APIRouter

from app.api.v1 import (
    callback,
    env_vars,
    mcp_presets,
    messages,
    runs,
    schedules,
    sessions,
    skill_installs,
    skill_presets,
    tasks,
    tool_executions,
    user_mcp_configs,
)
from app.core.settings import get_settings
from app.schemas.response import Response

api_v1_router = APIRouter()

api_v1_router.include_router(sessions.router)
api_v1_router.include_router(tasks.router)
api_v1_router.include_router(runs.router)
api_v1_router.include_router(schedules.router)
api_v1_router.include_router(callback.router)
api_v1_router.include_router(messages.router)
api_v1_router.include_router(tool_executions.router)
api_v1_router.include_router(env_vars.router)
api_v1_router.include_router(mcp_presets.router)
api_v1_router.include_router(user_mcp_configs.router)
api_v1_router.include_router(skill_presets.router)
api_v1_router.include_router(skill_installs.router)


@api_v1_router.get("/")
async def root():
    """Health check."""
    settings = get_settings()
    return Response.success(
        data={
            "service": settings.app_name,
            "status": "running",
            "version": settings.app_version,
        }
    )


@api_v1_router.get("/health")
async def health():
    """Health check."""
    settings = get_settings()
    return Response.success(
        data={
            "service": settings.app_name,
            "status": "healthy",
        }
    )
