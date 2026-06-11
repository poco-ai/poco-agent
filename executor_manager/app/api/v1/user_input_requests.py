from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.core.deps import require_callback_token
from app.schemas.response import Response, ResponseSchema
from app.schemas.user_input_request import (
    UserInputRequestCreateRequest,
    UserInputRequestResponse,
)
from app.services.backend_client import BackendClient

router = APIRouter(
    prefix="/user-input-requests",
    tags=["user-input-requests"],
    dependencies=[Depends(require_callback_token)],
)

backend_client = BackendClient()


@router.post("", response_model=ResponseSchema[UserInputRequestResponse])
async def create_user_input_request(
    request: UserInputRequestCreateRequest,
) -> JSONResponse:
    result = await backend_client.create_user_input_request(request.model_dump())
    return Response.success(data=result, message="User input request created")


@router.get("/{request_id}", response_model=ResponseSchema[UserInputRequestResponse])
async def get_user_input_request(request_id: str) -> JSONResponse:
    result = await backend_client.get_user_input_request(request_id)
    return Response.success(data=result, message="User input request retrieved")
