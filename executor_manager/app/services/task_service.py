import logging
from datetime import datetime

import httpx

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.core.settings import get_settings
from app.scheduler.task_dispatcher import TaskDispatcher
from app.schemas.task import (
    SessionStatusResponse,
    TaskCreateResponse,
    TaskStatusResponse,
)

logger = logging.getLogger(__name__)


class TaskService:
    """Manager-facing task APIs backed by the backend run queue."""

    def __init__(self) -> None:
        self.settings = get_settings()

    async def create_task(
        self,
        user_id: str,
        prompt: str,
        config: dict,
        session_id: str | None = None,
        scheduled_at: datetime | None = None,
    ) -> TaskCreateResponse:
        """Create a task and enqueue it for queue-driven execution.

        Args:
            user_id: User ID who created the task
            prompt: Task prompt for the agent
            config: Task configuration dictionary
            session_id: Optional existing session ID to continue conversation

        Returns:
            TaskCreateResponse with backend task identifier, session_id, and container info

        Raises:
            AppException: If task enqueue fails
        """
        from app.services.backend_client import BackendClient

        try:
            backend_client = BackendClient()
            config_snapshot = dict(config or {})
            config_snapshot.pop("user_id", None)
            enqueue_result = await backend_client.enqueue_task_from_manager(
                user_id=user_id,
                prompt=prompt,
                config_snapshot=config_snapshot,
                session_id=session_id,
                scheduled_at=scheduled_at.isoformat() if scheduled_at else None,
            )
            logger.info(
                "task_enqueue_accepted",
                extra={
                    "user_id": user_id,
                    "session_id": enqueue_result.get("session_id") or session_id,
                    "accepted_type": enqueue_result.get("accepted_type"),
                    "run_id": enqueue_result.get("run_id"),
                    "queue_item_id": enqueue_result.get("queue_item_id"),
                    "status": enqueue_result.get("status"),
                },
            )
            logger.info(
                "task_enqueue_accepted",
                extra={
                    "user_id": user_id,
                    "session_id": enqueue_result.get("session_id") or session_id,
                    "accepted_type": enqueue_result.get("accepted_type"),
                    "run_id": enqueue_result.get("run_id"),
                    "queue_item_id": enqueue_result.get("queue_item_id"),
                    "status": enqueue_result.get("status"),
                    "has_requested_container": bool(
                        config.get("container_id")
                        or config.get("container_mode") == "persistent"
                    ),
                },
            )

            container_id = config.get("container_id")
            container_mode = config.get("container_mode", "ephemeral")
            resolved_session_id = str(
                enqueue_result.get("session_id") or session_id or ""
            )
            if not resolved_session_id:
                raise AppException(
                    error_code=ErrorCode.TASK_SCHEDULING_FAILED,
                    message="Backend enqueue response missing session_id",
                )

            if container_id or container_mode == "persistent":
                browser_enabled = bool(config.get("browser_enabled"))
                _, container_id = await TaskDispatcher.resolve_executor_target(
                    session_id=resolved_session_id,
                    user_id=user_id,
                    browser_enabled=browser_enabled,
                    container_mode=container_mode,
                    container_id=container_id,
                )
                logger.info(
                    "task_enqueue_container_prepared",
                    extra={
                        "user_id": user_id,
                        "session_id": resolved_session_id,
                        "container_id": container_id,
                        "container_mode": container_mode,
                        "browser_enabled": browser_enabled,
                    },
                )
                logger.info(
                    "task_enqueue_container_prepared",
                    extra={
                        "user_id": user_id,
                        "session_id": resolved_session_id,
                        "container_id": container_id,
                        "container_mode": container_mode,
                        "browser_enabled": browser_enabled,
                    },
                )

            task_id = str(
                enqueue_result.get("run_id")
                or enqueue_result.get("queue_item_id")
                or ""
            )
            if not task_id:
                raise AppException(
                    error_code=ErrorCode.TASK_SCHEDULING_FAILED,
                    message="Backend enqueue response missing task identifier",
                )

            return TaskCreateResponse(
                task_id=task_id,
                session_id=resolved_session_id,
                status=str(enqueue_result.get("status") or "queued"),
                container_id=container_id,
                task_type=enqueue_result.get("accepted_type"),
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to enqueue task: {e}")
            raise AppException(
                error_code=ErrorCode.TASK_SCHEDULING_FAILED,
                message=f"Failed to enqueue task: {e.response.text}",
            )
        except AppException:
            raise
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            raise AppException(
                error_code=ErrorCode.TASK_SCHEDULING_FAILED,
                message=str(e),
            )

    async def get_task_status(self, task_id: str) -> TaskStatusResponse:
        """Get task status from backend.

        Args:
            task_id: Task ID to query

        Returns:
            TaskStatusResponse with task status info

        Raises:
            AppException: If task not found in backend
        """
        from app.services.backend_client import BackendClient

        backend_client = BackendClient()

        try:
            status_data = await backend_client.get_internal_task_status(task_id)
            return TaskStatusResponse(
                task_id=task_id,
                status=str(status_data.get("status") or "unknown"),
                next_run_time=None,
                task_type=status_data.get("task_type"),
                session_id=status_data.get("session_id"),
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise AppException(
                    error_code=ErrorCode.TASK_NOT_FOUND,
                    message=f"Task not found: {task_id}",
                    details={"task_id": task_id},
                )
            raise AppException(
                error_code=ErrorCode.BACKEND_UNAVAILABLE,
                message=f"Backend request failed: {e.response.text}",
            )
        except AppException:
            raise
        except Exception as e:
            logger.error(f"Failed to get task status: {e}")
            raise AppException(
                error_code=ErrorCode.BACKEND_UNAVAILABLE,
                message=str(e),
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
