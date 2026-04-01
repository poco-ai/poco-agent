from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db, require_internal_token
from app.schemas.response import Response, ResponseSchema
from app.services.execution_settings_service import ExecutionSettingsService

router = APIRouter(prefix="/internal", tags=["internal"])

service = ExecutionSettingsService()


@router.get(
    "/execution-settings/resolve",
    response_model=ResponseSchema[dict],
)
async def resolve_execution_settings(
    _: None = Depends(require_internal_token),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.resolve_for_execution(db, user_id)
    return Response.success(data=result, message="Execution settings resolved")
