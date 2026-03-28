from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.schemas.response import Response, ResponseSchema
from app.schemas.task import (
    SessionStatusResponse,
    TaskCreateRequest,
    TaskCreateResponse,
    TaskStatusResponse,
)
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])
task_service = TaskService()


@router.post("", response_model=ResponseSchema[TaskCreateResponse])
async def create_task(request: TaskCreateRequest) -> JSONResponse:
    """Create a task and enqueue it into the backend run queue.

    If session_id is provided, the request continues the existing conversation.
    Runtime dispatch is handled later by RunPullService rather than directly by
    this endpoint.
    """
    result = await task_service.create_task(
        user_id=request.user_id,
        prompt=request.prompt,
        config=request.config.model_dump(exclude_unset=True),
        session_id=request.session_id,
        scheduled_at=request.scheduled_at,
    )
    return Response.success(data=result.model_dump(), message="Task created")


@router.get("/{task_id}", response_model=ResponseSchema[TaskStatusResponse])
async def get_task_status(task_id: str) -> JSONResponse:
    """Get task status from backend's unified run/queue state."""
    result = await task_service.get_task_status(task_id)
    return Response.success(data=result.model_dump())


@router.get(
    "/session/{session_id}", response_model=ResponseSchema[SessionStatusResponse]
)
async def get_task_status_by_session(session_id: str) -> JSONResponse:
    """Get task status by session ID."""
    result = await task_service.get_session_status(session_id)
    return Response.success(data=result.model_dump())
