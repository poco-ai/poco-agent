from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db, require_internal_token
from app.schemas.mcp_config import McpConfigResolveRequest
from app.schemas.response import Response, ResponseSchema
from app.services.mcp_config_service import McpConfigService

router = APIRouter(prefix="/internal", tags=["internal"])

service = McpConfigService()


@router.post(
    "/mcp-config/resolve",
    response_model=ResponseSchema[dict],
)
async def resolve_mcp_config(
    request: McpConfigResolveRequest,
    _: None = Depends(require_internal_token),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Resolve effective MCP config for execution based on selected server ids."""
    resolved = service.resolve_user_mcp_config(
        db=db,
        user_id=user_id,
        server_ids=request.server_ids,
        server_overrides=request.server_overrides,
    )
    return Response.success(data=resolved, message="MCP config resolved")
