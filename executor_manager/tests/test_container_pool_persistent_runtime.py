import unittest
import uuid
from unittest.mock import MagicMock

from app.services.container_pool import ContainerPool


class ContainerPoolPersistentRuntimeTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
