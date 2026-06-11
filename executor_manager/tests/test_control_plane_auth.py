import unittest
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1 import executor, schedules, tasks, workspace


INTERNAL_TOKEN = "internal-token"


class ExecutorManagerControlPlaneAuthTests(unittest.TestCase):
    def _app(self) -> FastAPI:
        app = FastAPI()
        app.include_router(workspace.router, prefix="/api/v1")
        app.include_router(tasks.router, prefix="/api/v1")
        app.include_router(executor.router, prefix="/api/v1")
        app.include_router(schedules.router, prefix="/api/v1")

        @app.get("/api/v1/health")
        async def health() -> dict[str, str]:
            return {"status": "healthy"}

        return app

    def _settings(self) -> MagicMock:
        return MagicMock(
            internal_api_token=INTERNAL_TOKEN,
            schedule_config_path=None,
        )

    @contextmanager
    def _with_common_patches(self) -> Iterator[None]:
        task_response = SimpleNamespace(
            model_dump=lambda: {
                "task_id": "task-1",
                "session_id": "session-1",
                "status": "scheduled",
            }
        )
        pool = MagicMock()
        pool.delete_container = AsyncMock()
        pool.get_container_stats.return_value = {
            "total_active": 0,
            "persistent_containers": 0,
            "ephemeral_containers": 0,
            "containers": [],
        }
        schedule_config = SimpleNamespace(enabled=True, rules=[])
        patchers = [
            patch("app.core.deps.get_settings", return_value=self._settings()),
            patch(
                "app.api.v1.workspace.workspace_manager.list_workspace_files",
                return_value=[],
            ),
            patch(
                "app.api.v1.workspace.workspace_manager.delete_workspace",
                return_value=True,
            ),
            patch(
                "app.api.v1.tasks.task_service.create_task",
                new=AsyncMock(return_value=task_response),
            ),
            patch(
                "app.api.v1.executor.TaskDispatcher.get_container_pool",
                return_value=pool,
            ),
            patch(
                "app.api.v1.schedules.get_current_pull_schedule_config",
                return_value=schedule_config,
            ),
        ]
        with ExitStack() as stack:
            tmp_dir = stack.enter_context(TemporaryDirectory())
            preview_file = Path(tmp_dir) / "secret.txt"
            preview_file.write_text("secret", encoding="utf-8")
            stack.enter_context(
                patch(
                    "app.api.v1.workspace.workspace_manager.resolve_workspace_file",
                    return_value=preview_file,
                )
            )
            stack.enter_context(
                patch(
                    "app.api.v1.workspace.workspace_manager.archive_workspace",
                    return_value=str(preview_file),
                )
            )
            for patcher in patchers:
                stack.enter_context(patcher)
            yield

    def test_control_plane_routes_reject_missing_internal_token(self) -> None:
        client = TestClient(self._app())
        requests = [
            (
                "GET",
                "/api/v1/workspace/file/victim/session-1?path=secret.txt",
                None,
            ),
            ("GET", "/api/v1/workspace/files/victim/session-1", None),
            ("POST", "/api/v1/workspace/archive/victim/session-1", None),
            ("DELETE", "/api/v1/workspace/victim/session-1", None),
            (
                "POST",
                "/api/v1/tasks",
                {
                    "prompt": "hello",
                    "user_id": "user-1",
                    "session_id": "session-1",
                    "config": {},
                },
            ),
            ("POST", "/api/v1/executor/delete", {"container_id": "container-1"}),
            ("GET", "/api/v1/executor/load", None),
            ("GET", "/api/v1/schedules", None),
        ]

        with self._with_common_patches():
            for method, path, body in requests:
                with self.subTest(path=path):
                    response = client.request(method, path, json=body)
                    self.assertEqual(response.status_code, 403)

    def test_control_plane_routes_reject_wrong_internal_token(self) -> None:
        client = TestClient(self._app())

        with self._with_common_patches():
            response = client.get(
                "/api/v1/workspace/files/victim/session-1",
                headers={"X-Internal-Token": "wrong-token"},
            )

        self.assertEqual(response.status_code, 403)

    def test_control_plane_routes_reject_callback_token(self) -> None:
        client = TestClient(self._app())
        headers = {"Authorization": "Bearer callback-token"}

        with self._with_common_patches():
            response = client.post(
                "/api/v1/tasks",
                json={
                    "prompt": "hello",
                    "user_id": "user-1",
                    "session_id": "session-1",
                    "config": {},
                },
                headers=headers,
            )

        self.assertEqual(response.status_code, 403)

    def test_control_plane_routes_accept_valid_internal_token(self) -> None:
        client = TestClient(self._app())
        headers = {"X-Internal-Token": INTERNAL_TOKEN}

        with self._with_common_patches():
            workspace_response = client.get(
                "/api/v1/workspace/files/victim/session-1",
                headers=headers,
            )
            task_response = client.post(
                "/api/v1/tasks",
                json={
                    "prompt": "hello",
                    "user_id": "user-1",
                    "session_id": "session-1",
                    "config": {},
                },
                headers=headers,
            )
            executor_response = client.get("/api/v1/executor/load", headers=headers)
            schedules_response = client.get("/api/v1/schedules", headers=headers)

        self.assertEqual(workspace_response.status_code, 200)
        self.assertEqual(task_response.status_code, 200)
        self.assertEqual(executor_response.status_code, 200)
        self.assertEqual(schedules_response.status_code, 200)

    def test_health_route_stays_public(self) -> None:
        response = TestClient(self._app()).get("/api/v1/health")

        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
