import unittest
from unittest.mock import MagicMock, patch

from app.services.executor_manager_client import ExecutorManagerClient


class ExecutorManagerClientTests(unittest.TestCase):
    def test_delete_container_sends_internal_token(self) -> None:
        settings = MagicMock(
            executor_manager_url="http://executor-manager",
            internal_api_token="internal-token",
        )
        response = MagicMock()
        response.raise_for_status.return_value = None
        http_client = MagicMock()
        http_client.post.return_value = response

        with (
            patch(
                "app.services.executor_manager_client.get_settings",
                return_value=settings,
            ),
            patch(
                "app.services.executor_manager_client.httpx.Client",
                return_value=http_client,
            ),
        ):
            ExecutorManagerClient().delete_container("container-1")

        http_client.post.assert_called_once()
        _, kwargs = http_client.post.call_args
        self.assertEqual(kwargs["headers"]["X-Internal-Token"], "internal-token")
        self.assertEqual(kwargs["json"]["container_id"], "container-1")


if __name__ == "__main__":
    unittest.main()
