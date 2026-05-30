from datetime import datetime, timezone
import logging
from typing import Protocol

from app.core.settings import get_settings
from app.services.backend_client import BackendClient
from app.services.container_pool import ContainerPool

logger = logging.getLogger(__name__)


class RuntimeIdleSettings(Protocol):
    persistent_runtime_idle_controller_enabled: bool
    persistent_runtime_idle_scan_batch_size: int
    worker_id: str


def _parse_datetime(raw_value: object) -> datetime | None:
    if not isinstance(raw_value, str) or not raw_value.strip():
        return None
    value = raw_value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class RuntimeIdleService:
    def __init__(
        self,
        *,
        settings: RuntimeIdleSettings | None = None,
        backend_client: BackendClient | None = None,
        container_pool: ContainerPool | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.backend_client = backend_client or BackendClient()
        self.container_pool = container_pool or ContainerPool()

    async def scan_once(self) -> None:
        if not self.settings.persistent_runtime_idle_controller_enabled:
            return

        runtimes = await self.backend_client.list_controller_persistent_runtimes(
            lifecycle_states=["running", "warm_idle", "stale"],
            limit=getattr(
                self.settings, "persistent_runtime_idle_scan_batch_size", 200
            ),
        )
        now = datetime.now(timezone.utc)

        for runtime in runtimes:
            runtime_key = str(runtime.get("runtime_key") or "").strip()
            if not runtime_key:
                continue

            lifecycle_state = str(runtime.get("lifecycle_state") or "").strip()
            has_live_work = bool(runtime.get("has_live_work"))
            keepalive_active = bool(runtime.get("keepalive_active"))
            container = self.container_pool.find_container_by_runtime_key(runtime_key)

            if lifecycle_state in {"running", "warm_idle"} and container is None:
                await self.backend_client.mark_persistent_runtime_stale(
                    runtime_key,
                    stop_reason="container_missing",
                )
                continue

            if container is None:
                continue

            if has_live_work or keepalive_active:
                continue

            last_activity_at = _parse_datetime(runtime.get("last_activity_at"))
            if last_activity_at is None:
                last_activity_at = _parse_datetime(runtime.get("last_started_at"))
            if last_activity_at is None:
                last_activity_at = now

            idle_timeout_seconds = int(runtime.get("idle_timeout_seconds") or 0)
            idle_seconds = max(0.0, (now - last_activity_at).total_seconds())
            if idle_timeout_seconds <= 0 or idle_seconds < idle_timeout_seconds:
                continue

            stop_status, _ = await self.container_pool.sleep_runtime(runtime_key)
            if stop_status == "stopped":
                await self.backend_client.mark_persistent_runtime_sleeping(
                    runtime_key,
                    stop_reason="idle_timeout",
                    worker_id=self.settings.worker_id,
                )
                continue

            if stop_status == "not_found":
                await self.backend_client.mark_persistent_runtime_stale(
                    runtime_key,
                    stop_reason="container_missing",
                )
                continue

            logger.warning(
                "persistent_runtime_idle_stop_failed",
                extra={"runtime_key": runtime_key, "stop_status": stop_status},
            )
