import logging
import time
from typing import TYPE_CHECKING

import docker

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
        if container_id and container_id in self.containers:
            logger.info(
                f"Reusing existing container {container_id} for session {session_id}"
            )
            container = self.containers[container_id]
            self.session_to_container[session_id] = container_id

            port_info = container.ports["8000/tcp"][0]
            return f"http://localhost:{port_info['HostPort']}", container_id

        container_id = f"exec-{session_id[:8]}"
        container_name = f"executor-{session_id[:8]}"

        logger.info(f"Creating new container {container_id} (mode: {container_mode})")

        workspace_volume = self.workspace_manager.get_workspace_volume(
            user_id=user_id,
            session_id=session_id,
        )

        labels = {
            "owner": "executor_manager",
            "session_id": session_id,
            "container_id": container_id,
            "user": user_id,
            "container_mode": container_mode,
        }

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
            ports={"8000/tcp": None},  # Docker 随机分配宿主机端口
            detach=True,
            auto_remove=True,
            labels=labels,
        )

        self.containers[container_id] = container
        self.session_to_container[session_id] = container_id

        self._wait_for_container_ready(container)

        # 获取 Docker 分配的实际端口
        container.reload()
        port_info = container.ports.get("8000/tcp")
        if not port_info:
            raise AppException(
                error_code=ErrorCode.CONTAINER_START_FAILED,
                message=f"Container {container_name} has no port mapping",
            )
        host_port = port_info[0]["HostPort"]

        logger.info(
            f"Container {container_id} started for session {session_id} on port {host_port}"
        )
        return f"http://localhost:{host_port}", container_id

    def _wait_for_container_ready(
        self,
        container: "Container",
        timeout: int = 30,
    ) -> None:
        """Wait for container to start.

        Args:
            container: Container object
            timeout: Timeout in seconds
        """
        start = time.time()

        while time.time() - start < timeout:
            container.reload()
            if container.status == "running":
                return
            time.sleep(1)

        raise AppException(
            error_code=ErrorCode.CONTAINER_START_FAILED,
            message=f"Container {container.name} failed to start within {timeout}s",
        )

    async def on_task_complete(self, session_id: str) -> None:
        """Handle task completion.

        Args:
            session_id: Session ID

        ephemeral mode: delete container
        persistent mode: keep container
        """
        if session_id not in self.session_to_container:
            logger.warning(f"Session {session_id} has no container mapping")
            return

        container_id = self.session_to_container.pop(session_id)

        sessions_using_container = [
            sid for sid, cid in self.session_to_container.items() if cid == container_id
        ]

        if sessions_using_container:
            logger.info(
                f"Container {container_id} still in use by {len(sessions_using_container)} sessions"
            )
            return

        if container_id in self.containers:
            container = self.containers[container_id]
            container_mode = container.labels.get("container_mode", "ephemeral")

            if container_mode == "ephemeral":
                logger.info(f"Container {container_id} is ephemeral, stopping")
                await self._delete_container(container_id)
            else:
                logger.info(f"Container {container_id} is persistent, keeping alive")

    async def delete_container(self, container_id: str) -> None:
        """Delete container explicitly.

        Args:
            container_id: Container ID
        """
        await self._delete_container(container_id)

    async def _delete_container(self, container_id: str) -> None:
        """Delete container.

        Args:
            container_id: Container ID
        """
        sessions_to_remove = [
            sid for sid, cid in self.session_to_container.items() if cid == container_id
        ]
        for sid in sessions_to_remove:
            self.session_to_container.pop(sid)

        if container_id in self.containers:
            container = self.containers.pop(container_id)
            try:
                container.stop(timeout=10)
                logger.info(f"Container {container_id} stopped")
            except Exception as e:
                logger.error(f"Failed to stop container {container_id}: {e}")

    async def cancel_task(self, session_id: str) -> None:
        """Cancel task and delete container.

        Args:
            session_id: Session ID
        """
        logger.info(f"Cancelling task for session {session_id}")

        if session_id not in self.session_to_container:
            logger.warning(f"Session {session_id} has no container")
            return

        container_id = self.session_to_container[session_id]
        await self._delete_container(container_id)

    def get_container_stats(self) -> dict[str, int | list[dict]]:
        """Get container statistics.

        Returns:
            Dict with total_active, persistent_containers, ephemeral_containers, containers list
        """
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
                    "labels": c.labels,
                }
                for c in self.containers.values()
            ],
        }
