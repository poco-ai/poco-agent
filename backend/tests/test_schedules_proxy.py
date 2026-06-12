import unittest
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.schedules import router


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        pass

    def read(self) -> bytes:
        return b'{"code":0,"data":{"rules":[]},"message":"ok"}'


class SchedulesProxyTests(unittest.TestCase):
    def test_schedules_proxy_sends_internal_token_to_executor_manager(self) -> None:
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        settings = MagicMock(
            executor_manager_url="http://executor-manager",
            internal_api_token="internal-token",
        )

        with (
            patch("app.api.v1.schedules.get_settings", return_value=settings),
            patch("app.api.v1.schedules.urlopen", return_value=_Response()) as open_url,
        ):
            response = TestClient(app).get("/api/v1/schedules")

        self.assertEqual(response.status_code, 200)
        request = open_url.call_args.args[0]
        self.assertEqual(request.get_header("X-internal-token"), "internal-token")


if __name__ == "__main__":
    unittest.main()
