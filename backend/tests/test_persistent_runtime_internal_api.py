import unittest
import uuid
from datetime import UTC, datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.deps import get_db, require_internal_token
from app.main import create_app
from app.schemas.persistent_runtime import PersistentRuntimeResponse


def build_runtime_response(*, runtime_key: str) -> PersistentRuntimeResponse:
    now = datetime.now(UTC)
    return PersistentRuntimeResponse(
        persistent_runtime_id=uuid.uuid4(),
        runtime_key=runtime_key,
        owner_type="server_agent",
        owner_id=uuid.uuid4(),
        agent_identity_id=uuid.uuid4(),
        assignment_id=None,
        session_id=None,
        container_id=None,
        lifecycle_state="sleeping",
        auto_resume=True,
        idle_timeout_seconds=900,
        warm_retention_seconds=120,
        keepalive_until=None,
        last_activity_at=None,
        last_started_at=None,
        last_stopped_at=None,
        last_stop_reason=None,
        worker_id=None,
        browser_enabled=False,
        filesystem_fingerprint=None,
        metadata_json=None,
        created_at=now,
        updated_at=now,
    )


class PersistentRuntimeInternalApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)
        self.app.dependency_overrides[require_internal_token] = lambda: None
        self.app.dependency_overrides[get_db] = lambda: object()

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    @patch("app.api.v1.internal_persistent_runtimes.service.get_runtime")
    def test_get_runtime_returns_payload(self, get_runtime) -> None:
        runtime_key = f"server_agent:{uuid.uuid4()}"
        runtime = build_runtime_response(runtime_key=runtime_key)
        get_runtime.return_value = runtime

        response = self.client.get(
            f"/api/v1/internal/persistent-runtimes/{runtime_key}",
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["runtime_key"], runtime_key)

    @patch("app.api.v1.internal_persistent_runtimes.service.extend_keepalive")
    def test_extend_keepalive_returns_updated_runtime(self, extend_keepalive) -> None:
        runtime_key = f"server_agent:{uuid.uuid4()}"
        runtime = build_runtime_response(runtime_key=runtime_key)
        extend_keepalive.return_value = runtime

        response = self.client.post(
            f"/api/v1/internal/persistent-runtimes/{runtime_key}/keepalive",
            json={"duration_seconds": 3600},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["runtime_key"], runtime_key)
        extend_keepalive.assert_called_once()


if __name__ == "__main__":
    unittest.main()
