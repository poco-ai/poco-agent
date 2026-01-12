from fastapi import APIRouter

from app.api.v1 import callback, sessions
from app.core.settings import get_settings
from app.schemas.response import Response

api_v1_router = APIRouter()

api_v1_router.include_router(sessions.router)
api_v1_router.include_router(callback.router)


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
