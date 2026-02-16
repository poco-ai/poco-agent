from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.settings import get_settings
from app.schemas.model_config import ModelConfigResponse
from app.schemas.response import Response, ResponseSchema

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=ResponseSchema[ModelConfigResponse])
async def get_model_config() -> JSONResponse:
    """Get model configuration for UI selection."""
    settings = get_settings()
    payload = ModelConfigResponse(
        default_model=settings.default_model,
        model_list=settings.model_list,
    )
    return Response.success(data=payload, message="Models retrieved successfully")
