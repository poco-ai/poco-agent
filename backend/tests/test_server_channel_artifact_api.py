import unittest
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.deps import get_current_user, get_db
from app.main import create_app
from app.models.user import User
from app.schemas.channel_artifact import ChannelArtifactCandidateResponse
from app.schemas.workspace import FileNode


def build_artifact_tree() -> list[FileNode]:
    return [
        FileNode(
            id="group/agent/1",
            name="api-specialist",
            type="folder",
            path="group/agent/1",
            children=[
                FileNode(
                    id="group/agent/1//plans/rate-limit-plan.md",
                    name="rate-limit-plan.md",
                    type="file",
                    path="/plans/rate-limit-plan.md",
                    url="https://example.com/rate-limit-plan.md",
                    mimeType="text/markdown",
                )
            ],
        )
    ]


class ServerChannelArtifactApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)
        self.current_user = User(
            id="user-1",
            primary_email="alice@example.com",
            display_name="Alice",
            avatar_url=None,
            status="active",
        )
        self.app.dependency_overrides[get_current_user] = lambda: self.current_user
        self.app.dependency_overrides[get_db] = lambda: object()

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    @patch("app.api.v1.server_channel_artifacts.service.list_channel_artifact_nodes")
    def test_list_channel_artifacts_returns_grouped_tree(
        self,
        list_channel_artifact_nodes,
    ) -> None:
        server_id = uuid.uuid4()
        channel_id = uuid.uuid4()
        list_channel_artifact_nodes.return_value = build_artifact_tree()

        response = self.client.get(
            f"/api/v1/servers/{server_id}/channels/{channel_id}/artifacts",
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"][0]["name"], "api-specialist")
        self.assertEqual(
            body["data"][0]["children"][0]["url"],
            "https://example.com/rate-limit-plan.md",
        )
        list_channel_artifact_nodes.assert_called_once()

    @patch("app.api.v1.server_channel_artifacts.service.list_channel_artifact_candidates")
    def test_list_channel_artifact_candidates_returns_flat_payload(
        self,
        list_channel_artifact_candidates,
    ) -> None:
        server_id = uuid.uuid4()
        channel_id = uuid.uuid4()
        artifact_id = uuid.uuid4()
        list_channel_artifact_candidates.return_value = [
            ChannelArtifactCandidateResponse(
                artifact_id=artifact_id,
                display_name="design.md",
                logical_path="/Uploads/design.md",
                mime_type="text/markdown",
                size_bytes=128,
                source_kind="user_upload",
                published_by_user_id="user-1",
                created_at=None,
            )
        ]

        response = self.client.get(
            f"/api/v1/servers/{server_id}/channels/{channel_id}/artifacts/candidates",
            params={"q": "design", "limit": 10},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"][0]["artifact_id"], str(artifact_id))
        self.assertEqual(body["data"][0]["logical_path"], "/Uploads/design.md")
        list_channel_artifact_candidates.assert_called_once()


if __name__ == "__main__":
    unittest.main()
