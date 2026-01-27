import logging
import time
from typing import TYPE_CHECKING

import docker
import docker.errors
import httpx

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.core.settings import get_settings
from app.services.workspace_manager import WorkspaceManager

if TYPE_CHECKING:
    from docker.models.containers import Container

logger = logging.getLogger(__name__)


class ContainerPool:
    """Executor container pool with ephemeral and persistent modes."""

    def __init__(self):
        self.docker_client = docker.from_env()
        self.settings = get_settings()
        self.workspace_manager = WorkspaceManager()

        self.containers: dict[str, "Container"] = {}
        self.session_to_container: dict[str, str] = {}

    async def get_or_create_container(
        self,
        session_id: str,
        user_id: str,
        container_mode: str = "ephemeral",
        container_id: str | None = None,
    ) -> tuple[str, str]:
        """Get or create container.

        Args:
            session_id: Session ID
            user_id: User ID
            container_mode: ephemeral | persistent
            container_id: Existing container ID to reuse

        Returns:
            (executor_url, container_id)
        """
        overall_started = time.perf_counter()
        published_host = (
            self.settings.executor_published_host or ""
        ).strip() or "localhost"
        if container_id and container_id in self.containers:
            logger.info(
                f"Reusing existing container {container_id} for session {session_id}"
            )
            container = self.containers[container_id]
            self.session_to_container[session_id] = container_id

            port_info = container.ports["8000/tcp"][0]
            logger.info(
                "timing",
                extra={
                    "step": "container_reuse_total",
                    "duration_ms": int((time.perf_counter() - overall_started) * 1000),
                    "session_id": session_id,
                    "user_id": user_id,
                    "container_id": container_id,
                    "container_mode": container_mode,
                },
            )
            return f"http://{published_host}:{port_info['HostPort']}", container_id

        container_id = f"exec-{session_id[:8]}"
        container_name = f"executor-{session_id[:8]}"

        # 清理可能存在的同名容器
        step_started = time.perf_counter()
        removed_stale = False
        try:
            old_container = self.docker_client.containers.get(container_name)
            logger.warning(f"Removing stale container {container_name}")
            old_container.remove(force=True)
            removed_stale = True
        except docker.errors.NotFound:
            pass
        logger.info(
            "timing",
            extra={
                "step": "container_cleanup_stale",
                "duration_ms": int((time.perf_counter() - step_started) * 1000),
                "session_id": session_id,
                "user_id": user_id,
                "container_id": container_id,
                "container_name": container_name,
                "removed": removed_stale,
            },
        )

        logger.info(f"Creating new container {container_id} (mode: {container_mode})")

        step_started = time.perf_counter()
        workspace_volume = self.workspace_manager.get_workspace_volume(
            user_id=user_id,
            session_id=session_id,
        )
        logger.info(
            "timing",
            extra={
                "step": "container_prepare_workspace_volume",
                "duration_ms": int((time.perf_counter() - step_started) * 1000),
                "session_id": session_id,
                "user_id": user_id,
                "container_id": container_id,
            },
        )

        labels = {
            "owner": "executor_manager",
            "session_id": session_id,
            "container_id": container_id,
            "user": user_id,
            "container_mode": container_mode,
        }

        step_started = time.perf_counter()
        container = self.docker_client.containers.run(
            image=self.settings.executor_image,
            name=container_name,
            environment={
                "ANTHROPIC_AUTH_TOKEN": self.settings.anthropic_token,
                "ANTHROPIC_BASE_URL": self.settings.anthropic_base_url,
                "DEFAULT_MODEL": self.settings.default_model,
                "WORKSPACE_PATH": "/workspace",
                "USER_ID": user_id,
                "SESSION_ID": session_id,
            },
            volumes={workspace_volume: {"bind": "/workspace", "mode": "rw"}},
            ports={"8000/tcp": None},
            detach=True,
            auto_remove=True,
            labels=labels,
            extra_hosts={"host.docker.internal": "host-gateway"},
        )
        logger.info(
            "timing",
            extra={
                "step": "container_docker_run",
                "duration_ms": int((time.perf_counter() - step_started) * 1000),
                "session_id": session_id,
                "user_id": user_id,
                "container_id": container_id,
                "container_name": container_name,
                "image": self.settings.executor_image,
            },
        )

        self.containers[container_id] = container
        self.session_to_container[session_id] = container_id

        self._wait_for_container_ready(container)

        step_started = time.perf_counter()
        container.reload()
        port_info = container.ports.get("8000/tcp")
        if not port_info:
            raise AppException(
                error_code=ErrorCode.CONTAINER_START_FAILED,
                message=f"Container {container_name} has no port mapping",
            )
        logger.info(
            "timing",
            extra={
                "step": "container_get_port_mapping",
                "duration_ms": int((time.perf_counter() - step_started) * 1000),
                "session_id": session_id,
                "user_id": user_id,
                "container_id": container_id,
                "container_name": container_name,
            },
        )
        host_port = port_info[0]["HostPort"]
        executor_url = f"http://{published_host}:{host_port}"

        self._wait_for_service_ready(executor_url)

        logger.info(
            f"Container {container_id} started for session {session_id} on port {host_port}"
        )
        logger.info(
            "timing",
            extra={
                "step": "container_create_total",
                "duration_ms": int((time.perf_counter() - overall_started) * 1000),
                "session_id": session_id,
                "user_id": user_id,
                "container_id": container_id,
                "container_name": container_name,
                "container_mode": container_mode,
                "host_port": host_port,
            },
        )
        return executor_url, container_id

    def _wait_for_container_ready(
        self,
        container: "Container",
        timeout: int = 30,
    ) -> None:
        """Wait for container to start."""
        started = time.perf_counter()
        attempts = 0

        while time.perf_counter() - started < timeout:
            attempts += 1
            container.reload()
            if container.status == "running":
                logger.info(
                    "timing",
                    extra={
                        "step": "container_wait_running",
                        "duration_ms": int((time.perf_counter() - started) * 1000),
                        "attempts": attempts,
                        "container_name": container.name,
                        "status": container.status,
                    },
                )
                return
            time.sleep(1)

        logger.warning(
            "timing",
            extra={
                "step": "container_wait_running_timeout",
                "duration_ms": int((time.perf_counter() - started) * 1000),
                "attempts": attempts,
                "container_name": container.name,
                "status": container.status,
            },
        )
        raise AppException(
            error_code=ErrorCode.CONTAINER_START_FAILED,
            message=f"Container {container.name} failed to start within {timeout}s",
        )

    def _wait_for_service_ready(
        self,
        executor_url: str,
        timeout: int = 60,
    ) -> None:
        """Wait for executor HTTP service to be ready."""
        started = time.perf_counter()
        attempts = 0
        health_url = f"{executor_url}/health"

        while time.perf_counter() - started < timeout:
            attempts += 1
            try:
                with httpx.Client(timeout=2.0) as client:
                    response = client.get(health_url)
                    if response.status_code == 200:
                        logger.info(
                            "timing",
                            extra={
                                "step": "container_wait_service_ready",
                                "duration_ms": int(
                                    (time.perf_counter() - started) * 1000
                                ),
                                "attempts": attempts,
                                "executor_url": executor_url,
                            },
                        )
                        logger.info(f"Executor service ready at {executor_url}")
                        return
            except httpx.RequestError:
                pass
            time.sleep(1)

        logger.warning(
            "timing",
            extra={
                "step": "container_wait_service_ready_timeout",
                "duration_ms": int((time.perf_counter() - started) * 1000),
                "attempts": attempts,
                "executor_url": executor_url,
            },
        )
        raise AppException(
            error_code=ErrorCode.CONTAINER_START_FAILED,
            message=f"Executor service at {executor_url} not ready within {timeout}s",
        )

    async def on_task_complete(self, session_id: str) -> None:
        """Handle task completion. Ephemeral containers are stopped."""
        container_id = self.session_to_container.pop(session_id, None)

        if not container_id:
            return

        sessions_using_container = [
            sid for sid, cid in self.session_to_container.items() if cid == container_id
        ]

        if sessions_using_container:
            logger.info(
                f"Container {container_id} still in use by {len(sessions_using_container)} sessions"
            )
            return

        if container_id in self.containers:
            container = self.containers.pop(container_id)
            container_mode = container.labels.get("container_mode", "ephemeral")

            if container_mode == "ephemeral":
                logger.info(f"Container {container_id} is ephemeral, stopping")
                try:
                    container.stop(timeout=10)
                except Exception as e:
                    logger.error(f"Failed to stop container {container_id}: {e}")

    async def cancel_task(self, session_id: str) -> None:
        """Cancel task and stop container."""
        logger.info(f"Cancelling task for session {session_id}")

        container_id = self.session_to_container.pop(session_id, None)
        if not container_id:
            return

        if container_id in self.containers:
            container = self.containers.pop(container_id)
            try:
                container.stop(timeout=10)
                logger.info(f"Container {container_id} stopped")
            except Exception as e:
                logger.error(f"Failed to stop container {container_id}: {e}")

    def get_container_stats(self) -> dict[str, int | list[dict]]:
        """Get container statistics."""
        persistent = 0
        ephemeral = 0

        for container in self.containers.values():
            mode = container.labels.get("container_mode", "ephemeral")
            if mode == "persistent":
                persistent += 1
            else:
                ephemeral += 1

        return {
            "total_active": len(self.containers),
            "persistent_containers": persistent,
            "ephemeral_containers": ephemeral,
            "containers": [
                {
                    "container_id": c.labels.get("container_id", c.name),
                    "name": c.name,
                    "status": c.status,
                    "mode": c.labels.get("container_mode", "ephemeral"),
                }
                for c in self.containers.values()
            ],
        }
