import asyncio
import unittest
import uuid
from unittest.mock import AsyncMock, MagicMock

from app.services.runtime_idle_service import RuntimeIdleService


class StubSettings:
    persistent_runtime_idle_controller_enabled = True
    persistent_runtime_idle_scan_batch_size = 200
    worker_id = "worker-1"


class RuntimeIdleServiceTests(unittest.TestCase):
    def test_scan_once_sleeps_expired_idle_runtime(self) -> None:
        runtime_key = f"agent_assignment:{uuid.uuid4()}"
        backend_client = MagicMock()
        backend_client.list_controller_persistent_runtimes = AsyncMock(
            return_value=[
                {
                    "runtime_key": runtime_key,
                    "lifecycle_state": "warm_idle",
                    "has_live_work": False,
                    "keepalive_active": False,
                    "idle_timeout_seconds": 900,
                    "last_activity_at": "2026-05-30T00:00:00+00:00",
                }
            ]
        )
        backend_client.mark_persistent_runtime_sleeping = AsyncMock()
        backend_client.mark_persistent_runtime_stale = AsyncMock()

        container_pool = MagicMock()
        container_pool.find_container_by_runtime_key.return_value = MagicMock()
        container_pool.sleep_runtime = AsyncMock(
            return_value=("stopped", "assignment-12345678")
        )

        service = RuntimeIdleService(
            settings=StubSettings(),
            backend_client=backend_client,
            container_pool=container_pool,
        )

        asyncio.run(service.scan_once())

        container_pool.sleep_runtime.assert_awaited_once_with(runtime_key)
        backend_client.mark_persistent_runtime_sleeping.assert_awaited_once()

    def test_scan_once_marks_runtime_stale_when_container_is_missing(self) -> None:
        runtime_key = f"server_agent:{uuid.uuid4()}"
        backend_client = MagicMock()
        backend_client.list_controller_persistent_runtimes = AsyncMock(
            return_value=[
                {
                    "runtime_key": runtime_key,
                    "lifecycle_state": "running",
                    "has_live_work": False,
                    "keepalive_active": False,
                    "idle_timeout_seconds": 900,
                    "last_activity_at": "2026-05-30T00:00:00+00:00",
                }
            ]
        )
        backend_client.mark_persistent_runtime_sleeping = AsyncMock()
        backend_client.mark_persistent_runtime_stale = AsyncMock()

        container_pool = MagicMock()
        container_pool.find_container_by_runtime_key.return_value = None

        service = RuntimeIdleService(
            settings=StubSettings(),
            backend_client=backend_client,
            container_pool=container_pool,
        )

        asyncio.run(service.scan_once())

        backend_client.mark_persistent_runtime_stale.assert_awaited_once_with(
            runtime_key,
            stop_reason="container_missing",
        )
        backend_client.mark_persistent_runtime_sleeping.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
