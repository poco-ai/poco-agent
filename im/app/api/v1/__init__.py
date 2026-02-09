from fastapi import APIRouter

from app.api.v1 import dingtalk, feishu, health, telegram
from app.core.settings import get_settings
from app.schemas.response import Response

api_v1_router = APIRouter()

api_v1_router.include_router(health.router)
api_v1_router.include_router(telegram.router)
api_v1_router.include_router(feishu.router)
api_v1_router.include_router(dingtalk.router)


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
