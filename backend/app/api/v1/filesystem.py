from fastapi import APIRouter

from app.core.settings import Settings, get_settings
from app.schemas.filesystem import LocalFilesystemSupport
from app.schemas.response import Response

router = APIRouter(prefix="/filesystem", tags=["filesystem"])


@router.get("/support")
async def get_local_filesystem_support():
    """Return frontend-facing local filesystem availability metadata."""
    settings = get_settings()
    payload = LocalFilesystemSupport(
        deployment_mode=settings.deployment_mode,
        local_mount_available=settings.deployment_mode == "local",
    )
    return Response.success(data=payload.model_dump(mode="json"))
