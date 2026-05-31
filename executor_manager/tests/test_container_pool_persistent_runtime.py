import asyncio
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import MagicMock

import docker.errors

from app.schemas.filesystem import MountResolutionResult
from app.services.container_pool import ContainerPool


class ContainerPoolPersistentRuntimeTests(unittest.TestCase):
    @staticmethod
    def _build_pool_for_create() -> ContainerPool:
        pool = ContainerPool.__new__(ContainerPool)
        pool.settings = SimpleNamespace(
            anthropic_base_url="https://api.example.test",
            anthropic_api_key="",
            callback_base_url="http://manager.test",
            callback_token="token",
            default_model="claude-test",
            executor_browser_image="executor:full",
            executor_image="executor:lite",
            executor_local_browser_image=None,
            executor_local_image=None,
            executor_prefer_local_image=False,
            executor_published_host="localhost",
            executor_timezone="Asia/Shanghai",
            playwright_mcp_image_responses="omit",
            playwright_mcp_output_mode="file",
            poco_browser_viewport_size="1366x768",
        )
        pool.workspace_manager = MagicMock()
        pool.workspace_manager.get_workspace_volume.return_value = "/tmp/workspace"
        pool.local_mount_service = MagicMock()
        pool.local_mount_service.build_runtime_config.return_value = (
            {},
            MountResolutionResult(resolved_mounts=[], mount_fingerprint="fp"),
        )
        pool.docker_client = MagicMock()
        pool.docker_client.containers.get.side_effect = docker.errors.NotFound(
            "missing"
        )
        pool.containers = {}
        pool.session_to_container = {}
        pool.runtime_to_container = {}
        pool._wait_for_container_ready = MagicMock()
        pool._wait_for_port_mapping = MagicMock(return_value="18000")
        pool._wait_for_service_ready = MagicMock()
        return pool

    def test_resolve_runtime_container_id_uses_owner_specific_prefix(self) -> None:
        pool = ContainerPool.__new__(ContainerPool)

        agent_runtime_id = pool._resolve_persistent_runtime_container_id(
            {
                "persistent_runtime_key": f"server_agent:{uuid.uuid4()}",
                "container_mode": "persistent",
            }
        )
        assignment_id = uuid.uuid4()
        assignment_runtime_id = pool._resolve_persistent_runtime_container_id(
            {
                "persistent_runtime_key": f"agent_assignment:{assignment_id}",
                "container_mode": "persistent",
            }
        )

        self.assertIsNotNone(agent_runtime_id)
        self.assertTrue(agent_runtime_id.startswith("agent-"))
        self.assertEqual(assignment_runtime_id, f"assignment-{str(assignment_id)[:8]}")

    def test_find_container_by_runtime_key_rehydrates_from_docker_labels(self) -> None:
        runtime_key = f"agent_assignment:{uuid.uuid4()}"
        container = MagicMock()
        container.labels = {
            "container_id": "assignment-12345678",
            "persistent_runtime_key": runtime_key,
        }

        pool = ContainerPool.__new__(ContainerPool)
        pool.containers = {}
        pool.runtime_to_container = {}
        pool.docker_client = MagicMock()
        pool.docker_client.containers.list.return_value = [container]

        result = pool.find_container_by_runtime_key(runtime_key)

        self.assertIs(result, container)
        self.assertEqual(
            pool.runtime_to_container[runtime_key],
            "assignment-12345678",
        )

    def test_persistent_container_is_created_without_auto_remove(self) -> None:
        runtime_key = f"server_agent:{uuid.uuid4()}"
        container = MagicMock()
        container.labels = {
            "container_id": f"agent-{runtime_key.split(':', maxsplit=1)[1][:8]}",
            "persistent_runtime_key": runtime_key,
        }
        pool = self._build_pool_for_create()
        pool.docker_client.containers.run.return_value = container

        asyncio.run(
            pool.get_or_create_container(
                session_id=str(uuid.uuid4()),
                user_id="user-1",
                task_config={"persistent_runtime_key": runtime_key},
                container_mode="persistent",
            )
        )

        _, kwargs = pool.docker_client.containers.run.call_args
        self.assertIs(kwargs["auto_remove"], False)

    def test_reusing_stopped_persistent_container_starts_it_before_waiting(self) -> None:
        runtime_key = f"server_agent:{uuid.uuid4()}"
        logical_container_id = f"agent-{runtime_key.split(':', maxsplit=1)[1][:8]}"
        container = MagicMock()
        container.status = "exited"
        container.labels = {
            "container_id": logical_container_id,
            "container_mode": "persistent",
            "browser_enabled": "false",
            "filesystem_mode": "sandbox",
            "mount_fingerprint": "fp",
            "persistent_runtime_key": runtime_key,
        }
        pool = self._build_pool_for_create()
        pool.containers[logical_container_id] = container
        pool.runtime_to_container[runtime_key] = logical_container_id

        asyncio.run(
            pool.get_or_create_container(
                session_id=str(uuid.uuid4()),
                user_id="user-1",
                task_config={"persistent_runtime_key": runtime_key},
                container_mode="persistent",
            )
        )

        container.start.assert_called_once_with()

    def test_reuse_mismatch_flags_persistent_container_with_auto_remove(self) -> None:
        container = MagicMock()
        container.labels = {
            "container_mode": "persistent",
            "browser_enabled": "false",
            "filesystem_mode": "sandbox",
            "mount_fingerprint": "fp",
        }
        container.attrs = {"HostConfig": {"AutoRemove": True}}
        pool = ContainerPool.__new__(ContainerPool)

        reasons = pool._get_reuse_mismatch_reasons(
            container=container,
            browser_enabled=False,
            filesystem_mode="sandbox",
            mount_fingerprint="fp",
        )

        self.assertIn("auto_remove", reasons)


if __name__ == "__main__":
    unittest.main()
