import unittest
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.preset import Preset
from app.models.preset_visual import PresetVisual
from app.schemas.preset import PresetCreateRequest, PresetUpdateRequest
from app.schemas.session import SessionCreateRequest, TaskConfig
from app.services.preset_service import PresetService
from app.services.session_service import SessionService


class PresetServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.storage_service = MagicMock()
        self.service = PresetService(storage_service=self.storage_service)
        self.db = MagicMock()
        self.user_id = "user-1"
        self.now = datetime.now(UTC)

    @patch("app.services.preset_service.PresetRepository.exists_by_user_name")
    def test_create_preset_rejects_duplicate_name(
        self, exists_by_user_name: MagicMock
    ) -> None:
        exists_by_user_name.return_value = True

        with self.assertRaises(AppException) as context:
            self.service.create_preset(
                self.db,
                self.user_id,
                PresetCreateRequest(
                    name="  Frontend  ",
                    visual_key="preset-visual-01",
                ),
            )

        self.assertEqual(context.exception.error_code, ErrorCode.PRESET_ALREADY_EXISTS)
        exists_by_user_name.assert_called_once_with(self.db, self.user_id, "Frontend")

    @patch.object(PresetService, "_validate_components")
    @patch("app.services.preset_service.PresetVisualRepository.get_by_key")
    @patch("app.services.preset_service.PresetRepository.create")
    @patch("app.services.preset_service.PresetRepository.exists_by_user_name")
    def test_create_preset_persists_trimmed_fields(
        self,
        exists_by_user_name: MagicMock,
        create: MagicMock,
        get_visual_by_key: MagicMock,
        validate_components: MagicMock,
    ) -> None:
        exists_by_user_name.return_value = False
        get_visual_by_key.return_value = PresetVisual(
            id=1,
            key="preset-visual-01",
            name="Preset Visual 01",
            storage_key="builtin/preset-visuals/preset-visual-01/asset.svg",
            hash="abc123",
            version="abc123",
            source="icons/presets/preset-visual-01.svg",
            managed_by="lifecycle",
            is_active=True,
            created_at=self.now,
            updated_at=self.now,
        )
        created_preset: Preset | None = None

        def capture_create(_db: MagicMock, preset: Preset) -> Preset:
            nonlocal created_preset
            created_preset = preset
            preset.id = 11
            preset.created_at = self.now
            preset.updated_at = self.now
            return preset

        create.side_effect = capture_create
        self.db.refresh.side_effect = lambda _: None

        result = self.service.create_preset(
            self.db,
            self.user_id,
            PresetCreateRequest(
                name="  Frontend Delivery  ",
                description="  Reusable flow  ",
                visual_key="preset-visual-01",
                browser_enabled=True,
                skill_ids=[1, 2],
            ),
        )

        self.assertIsNotNone(created_preset)
        assert created_preset is not None
        self.assertEqual(created_preset.name, "Frontend Delivery")
        self.assertEqual(created_preset.description, "Reusable flow")
        self.assertEqual(created_preset.visual_key, "preset-visual-01")
        self.assertEqual(created_preset.user_id, self.user_id)
        self.assertTrue(created_preset.browser_enabled)
        self.assertEqual(created_preset.skill_ids, [1, 2])
        validate_components.assert_called_once()
        self.assertGreaterEqual(get_visual_by_key.call_count, 1)
        self.db.commit.assert_called_once()
        self.assertEqual(result.preset_id, 11)
        self.assertEqual(result.name, "Frontend Delivery")
        self.assertEqual(result.description, "Reusable flow")
        self.assertEqual(result.visual_key, "preset-visual-01")
        self.assertEqual(
            result.visual_url,
            "/api/v1/presets/visuals/preset-visual-01/content",
        )
        self.assertEqual(result.visual_version, "abc123")

    @patch.object(PresetService, "_validate_components")
    @patch("app.services.preset_service.PresetRepository.exists_by_user_name")
    @patch("app.services.preset_service.PresetRepository.get_by_id")
    def test_update_preset_rejects_blank_name(
        self,
        get_by_id: MagicMock,
        exists_by_user_name: MagicMock,
        validate_components: MagicMock,
    ) -> None:
        get_by_id.return_value = Preset(
            id=7,
            user_id=self.user_id,
            name="Existing",
            description=None,
            visual_key="preset-visual-01",
            prompt_template=None,
            browser_enabled=False,
            memory_enabled=False,
            skill_ids=[],
            mcp_server_ids=[],
            plugin_ids=[],
            subagent_configs=[],
            is_deleted=False,
            created_at=self.now,
            updated_at=self.now,
        )
        exists_by_user_name.return_value = False

        with self.assertRaises(AppException) as context:
            self.service.update_preset(
                self.db,
                self.user_id,
                7,
                PresetUpdateRequest(name="   "),
            )

        self.assertEqual(context.exception.error_code, ErrorCode.BAD_REQUEST)
        validate_components.assert_not_called()

    @patch(
        "app.services.preset_service.PresetRepository.count_projects_using_as_default"
    )
    @patch("app.services.preset_service.PresetRepository.get_by_id")
    def test_delete_preset_rejects_project_usage(
        self,
        get_by_id: MagicMock,
        count_projects_using_as_default: MagicMock,
    ) -> None:
        get_by_id.return_value = Preset(
            id=9,
            user_id=self.user_id,
            name="Shared",
            description=None,
            visual_key="preset-visual-01",
            prompt_template=None,
            browser_enabled=False,
            memory_enabled=False,
            skill_ids=[],
            mcp_server_ids=[],
            plugin_ids=[],
            subagent_configs=[],
            is_deleted=False,
            created_at=self.now,
            updated_at=self.now,
        )
        count_projects_using_as_default.return_value = 2

        with self.assertRaises(AppException) as context:
            self.service.delete_preset(self.db, self.user_id, 9)

        self.assertEqual(context.exception.error_code, ErrorCode.BAD_REQUEST)
        self.db.commit.assert_not_called()

    @patch("app.services.preset_service.PresetRepository.exists_by_user_name")
    @patch("app.services.preset_service.PresetVisualRepository.get_by_key")
    def test_create_preset_rejects_unknown_visual_key(
        self,
        get_visual_by_key: MagicMock,
        exists_by_user_name: MagicMock,
    ) -> None:
        exists_by_user_name.return_value = False
        get_visual_by_key.return_value = None

        with self.assertRaises(AppException) as context:
            self.service.create_preset(
                self.db,
                self.user_id,
                PresetCreateRequest(
                    name="Frontend Delivery",
                    visual_key="missing-visual",
                ),
            )

        self.assertEqual(context.exception.error_code, ErrorCode.BAD_REQUEST)
        self.assertIn("Invalid preset visual key", context.exception.message)

    @patch("app.services.preset_service.PresetVisualRepository.list_active")
    def test_list_preset_visuals_uses_backend_visual_content_urls(
        self,
        list_active: MagicMock,
    ) -> None:
        list_active.return_value = [
            PresetVisual(
                id=1,
                key="preset-visual-01",
                name="Preset Visual 01",
                storage_key="builtin/preset-visuals/preset-visual-01/asset.svg",
                hash="abc123",
                version="abc123",
                source="icons/presets/preset-visual-01.svg",
                managed_by="lifecycle",
                is_active=True,
                created_at=self.now,
                updated_at=self.now,
            )
        ]

        result = self.service.list_preset_visuals(self.db)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].key, "preset-visual-01")
        self.assertEqual(
            result[0].url,
            "/api/v1/presets/visuals/preset-visual-01/content",
        )


class SessionPresetConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = SessionService()
        self.db = MagicMock()
        self.user_id = "user-1"

    @patch("app.services.session_service.SessionRepository.create")
    def test_create_session_persists_only_explicit_preset_config(
        self,
        create: MagicMock,
    ) -> None:
        session = MagicMock()
        create.return_value = session

        self.service.create_session(
            self.db,
            self.user_id,
            SessionCreateRequest(config=TaskConfig(preset_id=8)),
        )

        create.assert_called_once_with(
            session_db=self.db,
            user_id=self.user_id,
            config={"preset_id": 8},
            project_id=None,
            kind="chat",
        )
        self.db.commit.assert_called_once()
        self.db.refresh.assert_called_once_with(session)


if __name__ == "__main__":
    unittest.main()
