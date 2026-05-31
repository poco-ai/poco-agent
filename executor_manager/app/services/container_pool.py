from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

import docker
import docker.errors
import httpx

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.core.settings import get_settings
from app.schemas.filesystem import MountResolutionResult
from app.schemas.task import TaskCancelResult
from app.services.local_mount_service import LocalMountService
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
        self.local_mount_service = LocalMountService(self.settings)

        self.containers: dict[str, "Container"] = {}
        self.session_to_container: dict[str, str] = {}
        self.runtime_to_container: dict[str, str] = {}

    async def get_or_create_container(
        self,
        session_id: str,
        user_id: str,
        *,
        task_config: dict | None = None,
        browser_enabled: bool = False,
        container_mode: str = "ephemeral",
        container_id: str | None = None,
    ) -> tuple[str, str, MountResolutionResult]:
        """Get or create container.

        Args:
            session_id: Session ID
            user_id: User ID
            browser_enabled: Whether this container needs the desktop/browser stack (noVNC/Chrome).
            container_mode: ephemeral | persistent
            container_id: Existing container ID to reuse

        Returns:
            (executor_url, container_id)
        """
        overall_started = time.perf_counter()
        _, mount_resolution = self.local_mount_service.build_runtime_config(
            task_config,
            session_id=session_id,
        )
        agent_state_mount = self._resolve_agent_state_mount(
            task_config=task_config,
            session_id=session_id,
        )
        filesystem_mode = (
            "local_mount" if mount_resolution.resolved_mounts else "sandbox"
        )
        mount_fingerprint = mount_resolution.mount_fingerprint
        persistent_runtime_key = self._extract_persistent_runtime_key(
            task_config=task_config,
            container_mode=container_mode,
        )
        resolved_runtime_container_id = self._resolve_persistent_runtime_container_id(
            task_config
        )
        resolved_container_id = self._resolve_agent_container_id(
            task_config=task_config,
            container_mode=container_mode,
        )
        if resolved_runtime_container_id:
            resolved_container_id = resolved_runtime_container_id
        if resolved_container_id:
            container_id = resolved_container_id
        if (
            persistent_runtime_key
            and not container_id
            and persistent_runtime_key in self.runtime_to_container
        ):
            container_id = self.runtime_to_container[persistent_runtime_key]
        if persistent_runtime_key and not container_id:
            existing_container = self.find_container_by_runtime_key(
                persistent_runtime_key
            )
            if existing_container is not None:
                labels = getattr(existing_container, "labels", None) or {}
                label_container_id = str(labels.get("container_id") or "").strip()
                if label_container_id:
                    container_id = label_container_id
        published_host = (
            self.settings.executor_published_host or ""
        ).strip() or "localhost"
        if container_id and container_id in self.containers:
            logger.info(
                f"Reusing existing container {container_id} for session {session_id}"
            )
            container = self.containers[container_id]
            self.session_to_container[session_id] = container_id

            # Best-effort refresh port mappings.
            try:
                container.reload()
            except Exception:
                pass

            # If the caller now requires browser support but the existing container was created
            # without it, recreate the container (most common when upgrading a persistent container).
            mismatch_reasons = self._get_reuse_mismatch_reasons(
                container=container,
                browser_enabled=browser_enabled,
                filesystem_mode=filesystem_mode,
                mount_fingerprint=mount_fingerprint,
            )
            if mismatch_reasons:
                logger.info(
                    "mount_reuse_mismatch",
                    extra={
                        "session_id": session_id,
                        "user_id": user_id,
                        "container_id": container_id,
                        "container_mode": container_mode,
                        "browser_enabled": bool(browser_enabled),
                        "filesystem_mode": filesystem_mode,
                        "mount_fingerprint": mount_fingerprint,
                        "reasons": mismatch_reasons,
                    },
                )
                await self.delete_container(container_id)
            else:
                restarted = self._ensure_container_running(container)
                host_port = self._wait_for_port_mapping(container)
                executor_url = f"http://{published_host}:{host_port}"
                if restarted:
                    self._wait_for_service_ready(executor_url)
                logger.info(
                    "timing",
                    extra={
                        "step": "container_reuse_total",
                        "duration_ms": int(
                            (time.perf_counter() - overall_started) * 1000
                        ),
                        "session_id": session_id,
                        "user_id": user_id,
                        "container_id": container_id,
                        "container_mode": container_mode,
                        "browser_enabled": bool(browser_enabled),
                        "filesystem_mode": filesystem_mode,
                        "mount_fingerprint": mount_fingerprint,
                        "host_port": host_port,
                    },
                )
                return (
                    executor_url,
                    container_id,
                    mount_resolution,
                )

        if not container_id:
            container_id = f"exec-{session_id[:8]}"
        container_name = f"executor-{container_id}"

        # Remove stale container with the same name (best-effort).
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
            "browser_enabled": "true" if browser_enabled else "false",
            "filesystem_mode": filesystem_mode,
            "mount_fingerprint": mount_fingerprint,
            "agent_identity_id": (
                str(task_config.get("agent_identity_id")) if task_config else ""
            ),
            "agent_runtime_mode": (
                str(task_config.get("agent_runtime_mode")) if task_config else ""
            ),
            "persistent_runtime_key": persistent_runtime_key or "",
        }

        step_started = time.perf_counter()
        image = self._resolve_executor_image(browser_enabled=browser_enabled)
        ports = {"8000/tcp": None}
        environment = {
            "ANTHROPIC_BASE_URL": self.settings.anthropic_base_url,
            "DEFAULT_MODEL": self.settings.default_model,
            "WORKSPACE_PATH": "/workspace",
            "USER_ID": user_id,
            "SESSION_ID": session_id,
            "CALLBACK_BASE_URL": self.settings.callback_base_url.rstrip("/"),
            "CALLBACK_TOKEN": self.settings.callback_token,
            "POCO_SESSION_ID": session_id,
            "POCO_CALLBACK_BASE_URL": self.settings.callback_base_url.rstrip("/"),
            "POCO_CALLBACK_TOKEN": self.settings.callback_token,
            "EXECUTOR_TIMEZONE": self.settings.executor_timezone,
        }
        anthropic_api_key = (self.settings.anthropic_api_key or "").strip()
        if anthropic_api_key:
            environment["ANTHROPIC_API_KEY"] = anthropic_api_key
        if browser_enabled:
            environment["POCO_BROWSER_VIEWPORT_SIZE"] = (
                self.settings.poco_browser_viewport_size
            )
            environment["PLAYWRIGHT_MCP_OUTPUT_MODE"] = (
                self.settings.playwright_mcp_output_mode
            )
            environment["PLAYWRIGHT_MCP_IMAGE_RESPONSES"] = (
                self.settings.playwright_mcp_image_responses
            )
        container = self.docker_client.containers.run(
            image=image,
            name=container_name,
            environment=environment,
            volumes=self._build_volume_map(
                workspace_volume=workspace_volume,
                mount_resolution=mount_resolution,
                agent_state_mount=agent_state_mount,
            ),
            ports=ports,
            detach=True,
            auto_remove=container_mode != "persistent",
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
                "image": image,
                "browser_enabled": bool(browser_enabled),
                "filesystem_mode": filesystem_mode,
                "mount_count": len(mount_resolution.resolved_mounts),
            },
        )

        self.containers[container_id] = container
        self.session_to_container[session_id] = container_id
        if persistent_runtime_key:
            self.runtime_to_container[persistent_runtime_key] = container_id

        self._wait_for_container_ready(container)

        step_started = time.perf_counter()
        host_port = self._wait_for_port_mapping(container)
        logger.info(
            "timing",
            extra={
                "step": "container_get_port_mapping",
                "duration_ms": int((time.perf_counter() - step_started) * 1000),
                "session_id": session_id,
                "user_id": user_id,
                "container_id": container_id,
                "container_name": container_name,
                "host_port": host_port,
            },
        )
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
                "filesystem_mode": filesystem_mode,
                "mount_fingerprint": mount_fingerprint,
            },
        )
        return executor_url, container_id, mount_resolution

    @staticmethod
    def _build_volume_map(
        *,
        workspace_volume: str,
        mount_resolution: MountResolutionResult,
        agent_state_mount: dict[str, str] | None = None,
    ) -> dict[str, dict[str, str]]:
        volumes: dict[str, dict[str, str]] = {
            workspace_volume: {"bind": "/workspace", "mode": "rw"}
        }
        if agent_state_mount is not None:
            volumes[agent_state_mount["source"]] = {
                "bind": agent_state_mount["target"],
                "mode": agent_state_mount["mode"],
            }
        for mount in mount_resolution.resolved_mounts:
            logger.info(
                "mount_attach",
                extra={
                    "source_path": mount.source_path,
                    "container_path": mount.container_path,
                    "access_mode": mount.access_mode,
                    "provider_type": mount.provider_type,
                },
            )
            volumes[mount.source_path] = {
                "bind": mount.container_path,
                "mode": mount.access_mode,
            }
        return volumes

    def _resolve_agent_container_id(
        self,
        *,
        task_config: dict | None,
        container_mode: str,
    ) -> str | None:
        if not isinstance(task_config, dict):
            return None
        agent_identity_id = str(task_config.get("agent_identity_id") or "").strip()
        agent_runtime_mode = str(task_config.get("agent_runtime_mode") or "").strip()
        if (
            container_mode == "persistent"
            and agent_identity_id
            and agent_runtime_mode == "persistent"
        ):
            return f"agent-{agent_identity_id[:8]}"
        return None

    @staticmethod
    def _extract_persistent_runtime_key(
        *,
        task_config: dict | None,
        container_mode: str,
    ) -> str | None:
        if container_mode != "persistent" or not isinstance(task_config, dict):
            return None
        runtime_key = str(task_config.get("persistent_runtime_key") or "").strip()
        return runtime_key or None

    def _resolve_persistent_runtime_container_id(
        self,
        task_config: dict | None,
    ) -> str | None:
        if not isinstance(task_config, dict):
            return None
        runtime_key = str(task_config.get("persistent_runtime_key") or "").strip()
        if not runtime_key:
            return None
        owner_type, _, owner_id = runtime_key.partition(":")
        owner_id = owner_id.strip()
        if not owner_id:
            return None
        if owner_type == "server_agent":
            return f"agent-{owner_id[:8]}"
        if owner_type == "agent_assignment":
            return f"assignment-{owner_id[:8]}"
        return f"runtime-{owner_id[:8]}"

    def find_container_by_runtime_key(
        self,
        runtime_key: str,
    ) -> "Container" | None:
        tracked_container_id = self.runtime_to_container.get(runtime_key)
        if tracked_container_id and tracked_container_id in self.containers:
            return self.containers[tracked_container_id]

        for container_id, container in self.containers.items():
            labels = getattr(container, "labels", None) or {}
            if str(labels.get("persistent_runtime_key") or "").strip() == runtime_key:
                self.runtime_to_container[runtime_key] = container_id
                return container

        try:
            found = self.docker_client.containers.list(
                all=True,
                filters={"label": f"persistent_runtime_key={runtime_key}"},
            )
        except Exception:
            return None
        if not found:
            return None

        container = found[0]
        labels = getattr(container, "labels", None) or {}
        container_id = str(labels.get("container_id") or "").strip()
        if container_id:
            self.containers[container_id] = container
            self.runtime_to_container[runtime_key] = container_id
        return container

    def _resolve_agent_state_mount(
        self,
        *,
        task_config: dict | None,
        session_id: str,
    ) -> dict[str, str] | None:
        if not isinstance(task_config, dict):
            return None
        agent_identity_id = str(task_config.get("agent_identity_id") or "").strip()
        agent_runtime_mode = str(task_config.get("agent_runtime_mode") or "").strip()
        if not agent_identity_id or agent_runtime_mode not in {
            "persistent",
            "temporary",
        }:
            return None
        if agent_runtime_mode == "persistent":
            source = self.workspace_manager.get_agent_state_dir(
                agent_identity_id, create=True
            )
            mode = "rw"
        else:
            source = self.workspace_manager.create_agent_state_snapshot(
                agent_identity_id,
                session_id,
            )
            mode = "ro"
        return {
            "source": str(Path(source)),
            "target": "/agent_state",
            "mode": mode,
        }

    def _get_reuse_mismatch_reasons(
        self,
        *,
        container: "Container",
        browser_enabled: bool,
        filesystem_mode: str,
        mount_fingerprint: str,
    ) -> list[str]:
        reasons: list[str] = []
        if browser_enabled and not self._is_browser_enabled_container(container):
            reasons.append("browser_enabled")

        labels = getattr(container, "labels", None) or {}
        current_filesystem_mode = str(labels.get("filesystem_mode", "sandbox")).strip()
        if current_filesystem_mode != filesystem_mode:
            reasons.append("filesystem_mode")

        current_mount_fingerprint = str(labels.get("mount_fingerprint", "")).strip()
        if current_mount_fingerprint != mount_fingerprint:
            reasons.append("mount_fingerprint")

        current_container_mode = str(labels.get("container_mode", "")).strip()
        if current_container_mode == "persistent" and self._is_auto_remove_container(
            container
        ):
            reasons.append("auto_remove")

        return reasons

    def _resolve_executor_image(self, *, browser_enabled: bool) -> str:
        """Pick executor image based on browser requirement."""
        fallback_image = self._resolve_fallback_executor_image(
            browser_enabled=browser_enabled
        )
        if not self.settings.executor_prefer_local_image:
            return fallback_image

        local_candidate = self._resolve_local_executor_image(
            browser_enabled=browser_enabled
        )
        if not local_candidate:
            return fallback_image

        if self._local_image_exists(local_candidate):
            logger.info(
                "executor_local_image_selected",
                extra={
                    "browser_enabled": bool(browser_enabled),
                    "image": local_candidate,
                    "fallback_image": fallback_image,
                },
            )
            return local_candidate

        logger.info(
            "executor_local_image_missing_falling_back",
            extra={
                "browser_enabled": bool(browser_enabled),
                "local_image": local_candidate,
                "fallback_image": fallback_image,
            },
        )
        return fallback_image

    def _resolve_fallback_executor_image(self, *, browser_enabled: bool) -> str:
        if not browser_enabled:
            return self.settings.executor_image

        candidate = (self.settings.executor_browser_image or "").strip()
        if candidate:
            return candidate

        # Backward-compatible fallback: may not have a desktop stack, but keeps the system running.
        logger.warning(
            "executor_browser_image_not_configured_falling_back",
            extra={"executor_image": self.settings.executor_image},
        )
        return self.settings.executor_image

    def _resolve_local_executor_image(self, *, browser_enabled: bool) -> str:
        if browser_enabled:
            return (self.settings.executor_local_browser_image or "").strip()
        return (self.settings.executor_local_image or "").strip()

    def _local_image_exists(self, image: str) -> bool:
        try:
            self.docker_client.images.get(image)
            return True
        except docker.errors.ImageNotFound:
            return False
        except docker.errors.DockerException as exc:
            logger.warning(
                "executor_local_image_check_failed",
                extra={"image": image, "error": str(exc)},
            )
            return False

    @staticmethod
    def _extract_host_port(container: "Container") -> str | None:
        port_info = getattr(container, "ports", None) or {}
        bindings = port_info.get("8000/tcp") if isinstance(port_info, dict) else None
        if isinstance(bindings, list) and bindings:
            host_port = bindings[0].get("HostPort")
            if isinstance(host_port, str) and host_port.strip():
                return host_port.strip()

        attrs = getattr(container, "attrs", None) or {}
        network = attrs.get("NetworkSettings") if isinstance(attrs, dict) else None
        ports = network.get("Ports") if isinstance(network, dict) else None
        bindings = ports.get("8000/tcp") if isinstance(ports, dict) else None
        if isinstance(bindings, list) and bindings:
            host_port = bindings[0].get("HostPort")
            if isinstance(host_port, str) and host_port.strip():
                return host_port.strip()

        return None

    def _wait_for_port_mapping(
        self,
        container: "Container",
        timeout: int = 30,
    ) -> str:
        started = time.perf_counter()
        attempts = 0

        while time.perf_counter() - started < timeout:
            attempts += 1
            try:
                container.reload()
            except docker.errors.NotFound as exc:
                raise AppException(
                    error_code=ErrorCode.CONTAINER_START_FAILED,
                    message=f"Container {container.name} disappeared before port mapping became available",
                ) from exc

            host_port = self._extract_host_port(container)
            if host_port:
                logger.info(
                    "timing",
                    extra={
                        "step": "container_wait_port_mapping",
                        "duration_ms": int((time.perf_counter() - started) * 1000),
                        "attempts": attempts,
                        "container_name": container.name,
                        "host_port": host_port,
                    },
                )
                return host_port

            time.sleep(0.5)

        logger.warning(
            "timing",
            extra={
                "step": "container_wait_port_mapping_timeout",
                "duration_ms": int((time.perf_counter() - started) * 1000),
                "attempts": attempts,
                "container_name": container.name,
                "status": getattr(container, "status", None),
                "ports": getattr(container, "ports", None),
            },
        )
        raise AppException(
            error_code=ErrorCode.CONTAINER_START_FAILED,
            message=f"Container {container.name} has no port mapping",
        )

    @staticmethod
    def _is_browser_enabled_container(container: "Container") -> bool:
        labels = getattr(container, "labels", None) or {}
        raw = str(labels.get("browser_enabled", "")).strip().lower()
        return raw in {"true", "1", "yes"}

    @staticmethod
    def _is_auto_remove_container(container: "Container") -> bool:
        attrs = getattr(container, "attrs", None)
        if not isinstance(attrs, dict):
            return False
        host_config = attrs.get("HostConfig")
        if not isinstance(host_config, dict):
            return False
        return bool(host_config.get("AutoRemove"))

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

    def _ensure_container_running(self, container: "Container") -> bool:
        """Start a stopped persistent container before reusing its executor service."""
        try:
            container.reload()
        except docker.errors.NotFound as exc:
            raise AppException(
                error_code=ErrorCode.CONTAINER_START_FAILED,
                message=f"Container {container.name} disappeared before reuse",
            ) from exc

        status = str(getattr(container, "status", "") or "").strip().lower()
        if status == "running":
            return False

        logger.info(
            "container_resume_start",
            extra={
                "container_name": container.name,
                "container_id": (getattr(container, "labels", None) or {}).get(
                    "container_id"
                ),
                "status": status,
            },
        )
        container.start()
        self._wait_for_container_ready(container)
        return True

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
                    self._log_mount_release(
                        container,
                        reason="task_complete",
                        session_id=session_id,
                    )
                    container.stop(timeout=10)
                except Exception as e:
                    logger.error(f"Failed to stop container {container_id}: {e}")

    async def delete_container(self, container_id: str) -> None:
        """Delete a container explicitly (mainly for persistent mode).

        This removes any session bindings, stops the container if it is still running,
        and attempts to remove it from Docker. Persistent runtime sleep uses stop only;
        this method is for explicit deletion/recreation.
        """
        cid = (container_id or "").strip()
        if not cid:
            return

        # Detach all sessions that still point to this container.
        sessions = [sid for sid, c in self.session_to_container.items() if c == cid]
        for sid in sessions:
            self.session_to_container.pop(sid, None)

        container = self.containers.pop(cid, None)
        if container is None:
            try:
                found = self.docker_client.containers.list(
                    all=True,
                    filters={"label": f"container_id={cid}"},
                )
                container = found[0] if found else None
            except Exception:
                container = None
        if not container:
            return

        labels = getattr(container, "labels", None) or {}
        runtime_key = str(labels.get("persistent_runtime_key") or "").strip()
        if runtime_key:
            self.runtime_to_container.pop(runtime_key, None)

        try:
            self._log_mount_release(container, reason="delete_container")
            container.stop(timeout=10)
        except Exception as e:
            logger.error(f"Failed to stop container {cid}: {e}")

        try:
            container.remove(force=True)
        except Exception:
            # Best-effort: the container might have already been removed.
            pass

    async def cancel_task(self, session_id: str) -> TaskCancelResult:
        """Cancel task and stop the executor container.

        Note: container bookkeeping is in-memory. When the service restarts or runs with
        multiple workers, the session->container mapping may be missing. In that case,
        fall back to resolving the container by Docker labels/name.
        """
        logger.info(f"Cancelling task for session {session_id}")

        container_id = self.session_to_container.pop(session_id, None)
        containers_to_stop: list["Container"] = []
        seen: set[str] = set()

        tracked = self.containers.pop(container_id, None) if container_id else None
        if tracked is not None:
            containers_to_stop.append(tracked)
            cid = getattr(tracked, "id", None)
            if isinstance(cid, str) and cid:
                seen.add(cid)

        def _extend_unique(found: list["Container"]) -> None:
            for c in found:
                cid = getattr(c, "id", None)
                if not isinstance(cid, str) or not cid:
                    continue
                if cid in seen:
                    continue
                seen.add(cid)
                containers_to_stop.append(c)

        # Prefer exact match by full session_id label.
        try:
            found = self.docker_client.containers.list(
                all=True, filters={"label": f"session_id={session_id}"}
            )
            _extend_unique(found)
        except Exception:
            pass

        # Best-effort: if we know the logical container_id label, try to locate by that label too.
        if container_id:
            try:
                found = self.docker_client.containers.list(
                    all=True, filters={"label": f"container_id={container_id}"}
                )
                _extend_unique(found)
            except Exception:
                pass

        # Fallback to deterministic name (used by get_or_create_container).
        try:
            name = f"executor-{session_id[:8]}"
            found = self.docker_client.containers.get(name)
            _extend_unique([found])
        except docker.errors.NotFound:
            pass
        except Exception:
            pass

        if not containers_to_stop:
            logger.info(
                "cancel_task_no_container_found",
                extra={"session_id": session_id, "container_id": container_id},
            )
            return TaskCancelResult(
                session_id=session_id,
                stop_status="not_found",
                matched_container_count=0,
                stopped_container_count=0,
                message="No running executor container was found for this session",
            )

        stop_errors: list[str] = []
        stopped_count = 0
        for container in containers_to_stop:
            labels = getattr(container, "labels", None) or {}
            logical_id = labels.get("container_id")
            runtime_key = str(labels.get("persistent_runtime_key") or "").strip()
            try:
                self._log_mount_release(
                    container,
                    reason="cancel_task",
                    session_id=session_id,
                )
                container.stop(timeout=10)
                stopped_count += 1
                logger.info(
                    "container_stopped",
                    extra={
                        "session_id": session_id,
                        "container_id": logical_id or container_id,
                        "docker_id": container.id,
                        "container_name": container.name,
                    },
                )
            except docker.errors.NotFound:
                # Best-effort: ephemeral containers may have already been auto-removed.
                stopped_count += 1
            except Exception as e:
                stop_errors.append(str(e))
                logger.error(
                    "container_stop_failed",
                    extra={
                        "session_id": session_id,
                        "container_id": logical_id or container_id,
                        "docker_id": getattr(container, "id", None),
                        "container_name": getattr(container, "name", None),
                        "error": str(e),
                    },
                )

            # Clean up any stale bookkeeping for this logical container_id.
            if isinstance(logical_id, str) and logical_id:
                self.containers.pop(logical_id, None)
                bound_sessions = [
                    sid
                    for sid, cid in self.session_to_container.items()
                    if cid == logical_id
                ]
                for sid in bound_sessions:
                    self.session_to_container.pop(sid, None)
            if runtime_key:
                self.runtime_to_container.pop(runtime_key, None)

        if stop_errors:
            return TaskCancelResult(
                session_id=session_id,
                stop_status="failed",
                matched_container_count=len(containers_to_stop),
                stopped_container_count=stopped_count,
                message="; ".join(stop_errors),
            )

        return TaskCancelResult(
            session_id=session_id,
            stop_status="stopped",
            matched_container_count=len(containers_to_stop),
            stopped_container_count=stopped_count,
        )

    async def sleep_runtime(self, runtime_key: str) -> tuple[str, str | None]:
        container = self.find_container_by_runtime_key(runtime_key)
        if container is None:
            return "not_found", None

        labels = getattr(container, "labels", None) or {}
        logical_id = str(labels.get("container_id") or "").strip() or None
        try:
            self._log_mount_release(container, reason="sleep_runtime")
            container.stop(timeout=10)
        except docker.errors.NotFound:
            pass
        except Exception:
            return "failed", logical_id

        if logical_id:
            self.containers.pop(logical_id, None)
            bound_sessions = [
                session_id
                for session_id, cid in self.session_to_container.items()
                if cid == logical_id
            ]
            for session_id in bound_sessions:
                self.session_to_container.pop(session_id, None)
        self.runtime_to_container.pop(runtime_key, None)
        return "stopped", logical_id

    @staticmethod
    def _log_mount_release(
        container: "Container",
        *,
        reason: str,
        session_id: str | None = None,
    ) -> None:
        labels = getattr(container, "labels", None) or {}
        logger.info(
            "mount_release",
            extra={
                "reason": reason,
                "session_id": session_id or labels.get("session_id"),
                "container_id": labels.get("container_id"),
                "mount_fingerprint": labels.get("mount_fingerprint"),
            },
        )

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
