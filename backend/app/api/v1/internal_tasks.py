from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db, require_internal_token
from app.schemas.response import Response, ResponseSchema
from app.schemas.task import (
    InternalTaskEnqueueRequest,
    InternalTaskStatusResponse,
    TaskEnqueueResponse,
)
from app.services.task_service import TaskService

router = APIRouter(prefix="/internal", tags=["internal"])

task_service = TaskService()


@router.post("/tasks", response_model=ResponseSchema[TaskEnqueueResponse])
async def enqueue_internal_task(
    request: InternalTaskEnqueueRequest,
    _: None = Depends(require_internal_token),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = task_service.enqueue_task_from_manager(db, user_id, request)
    return Response.success(data=result.model_dump(), message="Task enqueued")


@router.get(
    "/tasks/{task_id}", response_model=ResponseSchema[InternalTaskStatusResponse]
)
async def get_internal_task_status(
    task_id: UUID,
    _: None = Depends(require_internal_token),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = task_service.get_internal_task_status(db, task_id)
    return Response.success(data=result.model_dump(mode="json"), message="Task status")
