from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db
from app.schemas.env_var import (
    EnvVarCreateRequest,
    EnvVarResponse,
    EnvVarUpdateRequest,
)
from app.schemas.response import Response, ResponseSchema
from app.services.env_var_service import EnvVarService

router = APIRouter(prefix="/env-vars", tags=["env-vars"])

env_var_service = EnvVarService()


@router.get("", response_model=ResponseSchema[list[EnvVarResponse]])
async def list_env_vars(
    include_secrets: bool = Query(default=False),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = env_var_service.list_env_vars(
        db, user_id=user_id, include_secrets=include_secrets
    )
    return Response.success(data=result, message="Env vars retrieved")


@router.post("", response_model=ResponseSchema[EnvVarResponse])
async def create_env_var(
    request: EnvVarCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = env_var_service.create_env_var(db, user_id, request)
    return Response.success(data=result, message="Env var created")


@router.patch("/{env_var_id}", response_model=ResponseSchema[EnvVarResponse])
async def update_env_var(
    env_var_id: int,
    request: EnvVarUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = env_var_service.update_env_var(db, user_id, env_var_id, request)
    return Response.success(data=result, message="Env var updated")


@router.delete("/{env_var_id}", response_model=ResponseSchema[dict])
async def delete_env_var(
    env_var_id: int,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    env_var_service.delete_env_var(db, user_id, env_var_id)
    return Response.success(data={"id": env_var_id}, message="Env var deleted")
