from fastapi import APIRouter

from app.core.settings import Settings, get_settings
from app.schemas.filesystem import (
    LocalFilesystemHelperStatus,
    LocalFilesystemSupport,
)
from app.schemas.response import Response

router = APIRouter(prefix="/filesystem", tags=["filesystem"])


@router.get("/support")
async def get_local_filesystem_support():
    """Return frontend-facing local filesystem availability metadata."""
    settings = get_settings()
    helper_status = _resolve_helper_status(settings)
    payload = LocalFilesystemSupport(
        deployment_mode=settings.deployment_mode,
        helper_status=helper_status,
        helper_message=settings.local_filesystem_helper_message,
        local_mount_available=helper_status == "available",
    )
    return Response.success(data=payload.model_dump(mode="json"))


def _resolve_helper_status(settings: Settings) -> LocalFilesystemHelperStatus:
    configured_status = settings.local_filesystem_helper_status
    if configured_status is not None:
        return configured_status

    if settings.deployment_mode == "cloud":
        return "bridge_unreachable"

    return "available"
