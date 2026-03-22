from fastapi import APIRouter

from app.api.v1 import (
    callback,
    computer,
    executor,
    memories,
    schedules,
    skills_upload,
    tasks,
    user_input_requests,
    workspace,
)
from app.core.settings import get_settings
from app.schemas.response import Response
from app.scheduler.scheduler_config import scheduler

api_v1_router = APIRouter()

api_v1_router.include_router(tasks.router)
api_v1_router.include_router(schedules.router)
api_v1_router.include_router(callback.router)
api_v1_router.include_router(computer.router)
api_v1_router.include_router(executor.router)
api_v1_router.include_router(skills_upload.router)
api_v1_router.include_router(workspace.router)
api_v1_router.include_router(user_input_requests.router)
api_v1_router.include_router(memories.router)


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
            "scheduler_running": scheduler.running,
        }
    )
