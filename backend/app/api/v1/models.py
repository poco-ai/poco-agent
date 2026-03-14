from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db
from app.schemas.model_config import (
    ModelConfigResponse,
    ModelProviderResponse,
    ProviderModelSettingsUpsertRequest,
)
from app.schemas.response import Response, ResponseSchema
from app.services.model_config_service import ModelConfigService

router = APIRouter(prefix="/models", tags=["models"])
model_config_service = ModelConfigService()


@router.get("", response_model=ResponseSchema[ModelConfigResponse])
async def get_model_config(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Get model configuration for UI selection."""
    payload = model_config_service.get_model_config(db, user_id=user_id)
    return Response.success(data=payload, message="Models retrieved successfully")


@router.put(
    "/providers/{provider_id}",
    response_model=ResponseSchema[ModelProviderResponse],
)
async def upsert_provider_models(
    provider_id: str,
    request: ProviderModelSettingsUpsertRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Persist the selected model list for a provider."""
    payload = model_config_service.upsert_provider_models(
        db,
        user_id=user_id,
        provider_id=provider_id,
        request=request,
    )
    return Response.success(data=payload, message="Provider models updated")
