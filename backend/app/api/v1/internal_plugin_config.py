from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db, require_internal_token
from app.schemas.plugin_config import PluginConfigResolveRequest
from app.schemas.response import Response, ResponseSchema
from app.services.plugin_config_service import PluginConfigService

router = APIRouter(prefix="/internal", tags=["internal"])

service = PluginConfigService()


@router.post(
    "/plugin-config/resolve",
    response_model=ResponseSchema[dict],
)
async def resolve_plugin_config(
    request: PluginConfigResolveRequest,
    _: None = Depends(require_internal_token),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    resolved = service.resolve_user_plugin_files(
        db=db,
        user_id=user_id,
        plugin_ids=request.plugin_ids,
        plugin_overrides=request.plugin_overrides,
    )
    return Response.success(data=resolved, message="Plugin config resolved")
