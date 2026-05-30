import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_internal_token
from app.schemas.internal_persistent_runtime import (
    InternalPersistentRuntimeStartedRequest,
    InternalPersistentRuntimeStoppedRequest,
)
from app.schemas.persistent_runtime import (
    PersistentRuntimeControllerResponse,
    PersistentRuntimeKeepaliveRequest,
    PersistentRuntimeResponse,
)
from app.schemas.response import Response, ResponseSchema
from app.services.persistent_runtime_service import PersistentRuntimeService

router = APIRouter(
    prefix="/internal/persistent-runtimes",
    tags=["internal-persistent-runtimes"],
)

service = PersistentRuntimeService()


@router.get(
    "/controller",
    response_model=ResponseSchema[list[PersistentRuntimeControllerResponse]],
)
async def list_controller_persistent_runtimes(
    lifecycle_state: list[str] = Query(default_factory=list),
    limit: int | None = Query(default=None, ge=1, le=500),
    _: None = Depends(require_internal_token),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.list_controller_runtimes(
        db,
        lifecycle_states=lifecycle_state or None,
        limit=limit,
    )
    return Response.success(
        data=result,
        message="Persistent runtimes listed successfully",
    )


@router.get("/{runtime_key}", response_model=ResponseSchema[PersistentRuntimeResponse])
async def get_persistent_runtime(
    runtime_key: str,
    _: None = Depends(require_internal_token),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.get_runtime(db, runtime_key)
    return Response.success(
        data=result,
        message="Persistent runtime retrieved successfully",
    )


@router.post(
    "/{runtime_key}/keepalive",
    response_model=ResponseSchema[PersistentRuntimeResponse],
)
async def extend_persistent_runtime_keepalive(
    runtime_key: str,
    request: PersistentRuntimeKeepaliveRequest,
    _: None = Depends(require_internal_token),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.extend_keepalive(
        db,
        runtime_key=runtime_key,
        duration_seconds=request.duration_seconds,
    )
    return Response.success(
        data=PersistentRuntimeResponse.model_validate(result),
        message="Persistent runtime keepalive updated successfully",
    )


@router.post(
    "/{runtime_key}/started",
    response_model=ResponseSchema[PersistentRuntimeResponse],
)
async def mark_persistent_runtime_started(
    runtime_key: str,
    request: InternalPersistentRuntimeStartedRequest,
    _: None = Depends(require_internal_token),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.mark_running(
        db,
        runtime_key=runtime_key,
        session_id=request.session_id,
        container_id=request.container_id,
        worker_id=request.worker_id,
        browser_enabled=request.browser_enabled,
        filesystem_fingerprint=request.filesystem_fingerprint,
    )
    return Response.success(
        data=PersistentRuntimeResponse.model_validate(result),
        message="Persistent runtime marked running successfully",
    )


@router.post(
    "/{runtime_key}/sleep",
    response_model=ResponseSchema[PersistentRuntimeResponse],
)
async def mark_persistent_runtime_sleeping(
    runtime_key: str,
    request: InternalPersistentRuntimeStoppedRequest,
    _: None = Depends(require_internal_token),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.mark_sleeping(
        db,
        runtime_key=runtime_key,
        stop_reason=request.stop_reason,
        worker_id=request.worker_id,
    )
    return Response.success(
        data=PersistentRuntimeResponse.model_validate(result),
        message="Persistent runtime marked sleeping successfully",
    )


@router.post(
    "/{runtime_key}/stale",
    response_model=ResponseSchema[PersistentRuntimeResponse],
)
async def mark_persistent_runtime_stale(
    runtime_key: str,
    request: InternalPersistentRuntimeStoppedRequest,
    _: None = Depends(require_internal_token),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.mark_stale(
        db,
        runtime_key=runtime_key,
        stop_reason=request.stop_reason,
    )
    return Response.success(
        data=PersistentRuntimeResponse.model_validate(result),
        message="Persistent runtime marked stale successfully",
    )
