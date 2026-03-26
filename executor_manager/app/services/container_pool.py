import logging
import time
from typing import TYPE_CHECKING

import docker
import docker.errors
import httpx

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.core.settings import get_settings
from app.schemas.filesystem import MountResolutionResult
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
        filesystem_mode = (
            "local_mount" if mount_resolution.resolved_mounts else "sandbox"
        )
        mount_fingerprint = mount_resolution.mount_fingerprint
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
                host_port = self._wait_for_port_mapping(container)
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
                    f"http://{published_host}:{host_port}",
                    container_id,
                    mount_resolution,
                )

        container_id = f"exec-{session_id[:8]}"
        container_name = f"executor-{session_id[:8]}"

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
            ),
            ports=ports,
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
                "image": image,
                "browser_enabled": bool(browser_enabled),
                "filesystem_mode": filesystem_mode,
                "mount_count": len(mount_resolution.resolved_mounts),
            },
        )

        self.containers[container_id] = container
        self.session_to_container[session_id] = container_id

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
    ) -> dict[str, dict[str, str]]:
        volumes: dict[str, dict[str, str]] = {
            workspace_volume: {"bind": "/workspace", "mode": "rw"}
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
        and attempts to remove it from Docker. (In most cases the container is started
        with auto_remove=True, so removal may already be handled by Docker.)
        """
        cid = (container_id or "").strip()
        if not cid:
            return

        # Detach all sessions that still point to this container.
        sessions = [sid for sid, c in self.session_to_container.items() if c == cid]
        for sid in sessions:
            self.session_to_container.pop(sid, None)

        container = self.containers.pop(cid, None)
        if not container:
            return

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

    async def cancel_task(self, session_id: str) -> None:
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
            return

        for container in containers_to_stop:
            labels = getattr(container, "labels", None) or {}
            logical_id = labels.get("container_id")
            try:
                self._log_mount_release(
                    container,
                    reason="cancel_task",
                    session_id=session_id,
                )
                container.stop(timeout=10)
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
                # Best-effort: the container may have already been removed (auto_remove=True).
                pass
            except Exception as e:
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
