import unittest
from datetime import UTC, datetime
from uuid import UUID
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.preset import PresetResponse, PresetVisualSummary
from app.schemas.project import ProjectResponse


def build_preset_response(preset_id: int = 1, name: str = "Frontend") -> PresetResponse:
    now = datetime.now(UTC)
    return PresetResponse(
        preset_id=preset_id,
        user_id="user-1",
        name=name,
        description="Reusable preset",
        visual_key="preset-visual-01",
        visual_url="/api/v1/presets/visuals/preset-visual-01/content",
        visual_version="abc123",
        prompt_template=None,
        browser_enabled=True,
        memory_enabled=False,
        skill_ids=[1],
        mcp_server_ids=[2],
        plugin_ids=[3],
        subagent_configs=[],
        created_at=now,
        updated_at=now,
    )


def build_project_response(
    project_id: UUID, *, default_preset_id: int | None
) -> ProjectResponse:
    now = datetime.now(UTC)
    return ProjectResponse(
        id=project_id,
        user_id="user-1",
        name="Project",
        description="Reusable project",
        default_model=None,
        default_preset_id=default_preset_id,
        local_mounts=[],
        created_at=now,
        updated_at=now,
    )


class PresetApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)
        self.headers = {"X-User-Id": "user-1"}

    @patch("app.api.v1.presets.service.list_presets")
    def test_list_presets_returns_response_envelope(self, list_presets) -> None:
        list_presets.return_value = [build_preset_response()]

        response = self.client.get("/api/v1/presets", headers=self.headers)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"][0]["preset_id"], 1)
        self.assertEqual(body["data"][0]["name"], "Frontend")
        list_presets.assert_called_once()

    @patch("app.api.v1.presets.service.create_preset")
    def test_create_preset_returns_created_payload(self, create_preset) -> None:
        create_preset.return_value = build_preset_response(preset_id=7, name="Backend")

        response = self.client.post(
            "/api/v1/presets",
            headers=self.headers,
            json={
                "name": "Backend",
                "description": "Backend preset",
                "visual_key": "preset-visual-01",
                "browser_enabled": False,
                "memory_enabled": True,
                "skill_ids": [],
                "mcp_server_ids": [],
                "plugin_ids": [],
                "subagent_configs": [],
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["preset_id"], 7)
        self.assertEqual(body["data"]["name"], "Backend")
        self.assertEqual(body["data"]["visual_key"], "preset-visual-01")
        create_preset.assert_called_once()

    @patch("app.api.v1.presets.service.list_preset_visuals")
    def test_list_preset_visuals_returns_response_envelope(
        self,
        list_preset_visuals,
    ) -> None:
        list_preset_visuals.return_value = [
            PresetVisualSummary(
                key="preset-visual-01",
                name="Preset Visual 01",
                version="abc123",
                url="/api/v1/presets/visuals/preset-visual-01/content",
            )
        ]

        response = self.client.get("/api/v1/presets/visuals", headers=self.headers)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"][0]["key"], "preset-visual-01")
        self.assertEqual(
            body["data"][0]["url"],
            "/api/v1/presets/visuals/preset-visual-01/content",
        )
        list_preset_visuals.assert_called_once()

    @patch("app.api.v1.presets.service.delete_preset")
    def test_delete_preset_returns_deleted_id(self, delete_preset) -> None:
        response = self.client.delete("/api/v1/presets/9", headers=self.headers)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["id"], 9)
        delete_preset.assert_called_once()


class ProjectApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)
        self.headers = {"X-User-Id": "user-1"}
        self.project_id = "f219f040-6ec9-4d2f-9cd3-7d2f93f75368"

    @patch("app.api.v1.projects.service.update_project")
    def test_update_project_returns_default_preset_id(self, update_project) -> None:
        update_project.return_value = build_project_response(
            UUID(self.project_id),
            default_preset_id=3,
        )

        response = self.client.patch(
            f"/api/v1/projects/{self.project_id}",
            headers=self.headers,
            json={"default_preset_id": 3},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["default_preset_id"], 3)
        update_project.assert_called_once()


if __name__ == "__main__":
    unittest.main()
