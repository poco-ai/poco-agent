from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.core.deps import require_internal_token
from app.schemas.response import Response, ResponseSchema
from app.schemas.task import (
    ContainerDeleteRequest,
    ContainerStatsResponse,
    TaskCancelRequest,
    TaskCancelResult,
)
from app.scheduler.task_dispatcher import TaskDispatcher

router = APIRouter(
    prefix="/executor",
    tags=["executor"],
    dependencies=[Depends(require_internal_token)],
)


@router.post("/cancel", response_model=ResponseSchema[TaskCancelResult])
async def cancel_task(request: TaskCancelRequest) -> JSONResponse:
    """Cancel running task and delete container.

    Args:
        request: Cancel task request

    Returns:
        Success response with session_id and status
    """
    container_pool = TaskDispatcher.get_container_pool()
    result = await container_pool.cancel_task(request.session_id)

    return Response.success(
        data=result,
        message="Task cancel request processed",
    )


@router.post("/delete", response_model=ResponseSchema[dict])
async def delete_container(request: ContainerDeleteRequest) -> JSONResponse:
    """Delete persistent container explicitly.

    Args:
        request: Delete container request

    Returns:
        Success response with container_id and status
    """
    container_pool = TaskDispatcher.get_container_pool()
    await container_pool.delete_container(request.container_id)

    return Response.success(
        data={"container_id": request.container_id, "status": "deleted"},
        message="Container deleted successfully",
    )


@router.get("/load", response_model=ResponseSchema[ContainerStatsResponse])
async def get_executor_load() -> JSONResponse:
    """Get executor container load statistics.

    Returns:
        Container statistics response
    """
    container_pool = TaskDispatcher.get_container_pool()
    stats = container_pool.get_container_stats()

    return Response.success(data=stats)
