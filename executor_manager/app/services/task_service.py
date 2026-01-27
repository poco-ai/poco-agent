import logging
import time
import uuid

import httpx

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.core.observability.request_context import get_request_id, get_trace_id
from app.core.settings import get_settings
from app.scheduler.scheduler_config import scheduler
from app.scheduler.task_dispatcher import TaskDispatcher
from app.schemas.task import (
    SessionStatusResponse,
    TaskCreateResponse,
    TaskStatusResponse,
)

logger = logging.getLogger(__name__)


class TaskService:
    """Service layer for task operations."""

    def __init__(self) -> None:
        self.settings = get_settings()

    async def create_task(
        self,
        user_id: str,
        prompt: str,
        config: dict,
        session_id: str | None = None,
    ) -> TaskCreateResponse:
        """Create a task and schedule it for execution.

        Args:
            user_id: User ID who created the task
            prompt: Task prompt for the agent
            config: Task configuration dictionary
            session_id: Optional existing session ID to continue conversation

        Returns:
            TaskCreateResponse with task_id, session_id, and container info

        Raises:
            AppException: If session creation or task scheduling fails
        """
        from app.services.backend_client import BackendClient

        task_id = str(uuid.uuid4())
        started = time.perf_counter()
        request_id = get_request_id()
        trace_id = get_trace_id()

        try:
            backend_client = BackendClient()

            # Continue existing session or create new one
            if session_id:
                # Get existing session info
                step_started = time.perf_counter()
                session_data = await self.get_session_status(session_id)
                logger.info(
                    "timing",
                    extra={
                        "step": "task_create_get_session_status",
                        "duration_ms": int((time.perf_counter() - step_started) * 1000),
                        "task_id": task_id,
                        "session_id": session_id,
                        "user_id": user_id,
                    },
                )
                sdk_session_id = session_data.sdk_session_id
                logger.info(f"Reusing existing session {session_id} for task {task_id}")
            else:
                # Create new session
                step_started = time.perf_counter()
                session_info = await backend_client.create_session(
                    user_id=user_id, config=config
                )
                logger.info(
                    "timing",
                    extra={
                        "step": "task_create_backend_create_session",
                        "duration_ms": int((time.perf_counter() - step_started) * 1000),
                        "task_id": task_id,
                        "session_id": session_info.get("session_id"),
                        "user_id": user_id,
                    },
                )
                session_id = session_info["session_id"]
                sdk_session_id = session_info.get("sdk_session_id")
                logger.info(f"Created session {session_id} for task {task_id}")

            container_url = None
            container_id = config.get("container_id")
            container_mode = config.get("container_mode", "ephemeral")

            if container_id or container_mode == "persistent":
                container_pool = TaskDispatcher.get_container_pool()
                step_started = time.perf_counter()
                (
                    container_url,
                    container_id,
                ) = await container_pool.get_or_create_container(
                    session_id=session_id,
                    user_id=user_id,
                    container_mode=container_mode,
                    container_id=container_id,
                )
                logger.info(
                    "timing",
                    extra={
                        "step": "task_create_get_or_create_container",
                        "duration_ms": int((time.perf_counter() - step_started) * 1000),
                        "task_id": task_id,
                        "session_id": session_id,
                        "user_id": user_id,
                        "container_id": container_id,
                        "container_mode": container_mode,
                    },
                )

            enqueued_at = time.perf_counter()
            step_started = time.perf_counter()
            scheduler.add_job(
                TaskDispatcher.dispatch,
                args=[
                    task_id,
                    session_id,
                    prompt,
                    config,
                    sdk_session_id,
                    request_id,
                    trace_id,
                    enqueued_at,
                ],
                id=task_id,
                replace_existing=True,
            )
            logger.info(
                "timing",
                extra={
                    "step": "task_create_scheduler_add_job",
                    "duration_ms": int((time.perf_counter() - step_started) * 1000),
                    "task_id": task_id,
                    "session_id": session_id,
                    "user_id": user_id,
                },
            )

            logger.info(f"Task {task_id} scheduled for execution")
            logger.info(
                "timing",
                extra={
                    "step": "task_create_total",
                    "duration_ms": int((time.perf_counter() - started) * 1000),
                    "task_id": task_id,
                    "session_id": session_id,
                    "user_id": user_id,
                },
            )

            return TaskCreateResponse(
                task_id=task_id,
                session_id=session_id,
                status="scheduled",
                executor_url=container_url,
                container_id=container_id,
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create session: {e}")
            raise AppException(
                error_code=ErrorCode.SESSION_CREATE_FAILED,
                message=f"Failed to create session: {e.response.text}",
            )
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            raise AppException(
                error_code=ErrorCode.TASK_SCHEDULING_FAILED,
                message=str(e),
            )

    def get_task_status(self, task_id: str) -> TaskStatusResponse:
        """Get task status from scheduler.

        Args:
            task_id: Task ID to query

        Returns:
            TaskStatusResponse with task status info

        Raises:
            AppException: If task not found in scheduler
        """
        job = scheduler.get_job(task_id)

        if job:
            return TaskStatusResponse(
                task_id=task_id,
                status="scheduled",
                next_run_time=str(job.next_run_time) if job.next_run_time else None,
            )

        # Task not found in scheduler - may have already executed
        raise AppException(
            error_code=ErrorCode.TASK_NOT_FOUND,
            message="Task not found in scheduler. It may have already been executed.",
            details={"task_id": task_id},
        )

    async def get_session_status(self, session_id: str) -> SessionStatusResponse:
        """Get session status from backend.

        Args:
            session_id: Session ID to query

        Returns:
            SessionStatusResponse from backend

        Raises:
            AppException: If session not found or backend request fails
        """
        from app.services.backend_client import BackendClient

        backend_client = BackendClient()

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{backend_client.settings.backend_url}/api/v1/sessions/{session_id}",
                    headers=backend_client._trace_headers(),
                )
                response.raise_for_status()
                data = response.json()

            # Parse backend response (backend returns wrapped ResponseSchema)
            session_data = data.get("data", data)
            return SessionStatusResponse(**session_data)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise AppException(
                    error_code=ErrorCode.SESSION_NOT_FOUND,
                    message=f"Session not found: {session_id}",
                )
            raise AppException(
                error_code=ErrorCode.BACKEND_UNAVAILABLE,
                message=f"Backend request failed: {e.response.text}",
            )
        except Exception as e:
            logger.error(f"Failed to get session status: {e}")
            raise AppException(
                error_code=ErrorCode.BACKEND_UNAVAILABLE,
                message=str(e),
            )
