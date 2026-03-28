import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.core.deps import require_callback_token
from app.schemas.callback import AgentCallbackRequest, CallbackReceiveResponse
from app.schemas.response import Response, ResponseSchema
from app.services.callback_service import CallbackService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/callback", tags=["callback"])
callback_service = CallbackService()


@router.post("", response_model=ResponseSchema[CallbackReceiveResponse])
async def receive_callback(
    callback: AgentCallbackRequest,
    _: None = Depends(require_callback_token),
) -> JSONResponse:
    """Receive callback from Executor and forward to Backend."""
    result = await callback_service.process_callback(callback)
    return Response.success(data=result.model_dump(), message="Callback received")
