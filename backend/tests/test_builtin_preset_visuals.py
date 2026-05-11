from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.lifecycle.bootstrap import LifecycleBootstrapService
from app.lifecycle.builtin_preset_visuals import (
    BuiltinPresetVisualBootstrapService,
    _resolve_preset_visual_assets_root,
)


class BuiltinPresetVisualsTests(unittest.TestCase):
    def test_resolve_assets_root_supports_source_checkout_layout(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            assets_root = repo_root / "assets" / "icons" / "presets"
            assets_root.mkdir(parents=True)
            module_file = (
                repo_root
                / "backend"
                / "app"
                / "lifecycle"
                / "builtin_preset_visuals.py"
            )

            self.assertEqual(
                _resolve_preset_visual_assets_root(module_file),
                assets_root,
            )

    def test_resolve_assets_root_supports_container_layout(self) -> None:
        with TemporaryDirectory() as temp_dir:
            app_root = Path(temp_dir) / "app"
            assets_root = app_root / "assets" / "icons" / "presets"
            assets_root.mkdir(parents=True)
            module_file = app_root / "app" / "lifecycle" / "builtin_preset_visuals.py"

            self.assertEqual(
                _resolve_preset_visual_assets_root(module_file),
                assets_root,
            )

    def test_discover_assets_returns_all_repo_svg_files_with_stable_storage_keys(
        self,
    ) -> None:
        assets_root = (
            Path(__file__).resolve().parents[2] / "assets" / "icons" / "presets"
        )
        expected_keys = sorted(path.stem for path in assets_root.glob("*.svg"))

        discovered = BuiltinPresetVisualBootstrapService._discover_assets()

        self.assertEqual([item.key for item in discovered], expected_keys)
        self.assertTrue(
            all(
                item.storage_key == f"builtin/preset-visuals/{item.key}/asset.svg"
                for item in discovered
            )
        )
        self.assertTrue(
            all(item.source.startswith("icons/presets/") for item in discovered)
        )

    @patch("app.lifecycle.builtin_preset_visuals.PresetVisualRepository")
    def test_bootstrap_uploads_new_assets_and_creates_catalog_records(
        self,
        repository,
    ) -> None:
        asset = BuiltinPresetVisualBootstrapService._discover_assets()[0]
        db = Mock()
        storage = Mock()
        storage.exists.return_value = False
        repository.list_managed.return_value = []
        repository.get_by_key.return_value = None

        with (
            patch.object(
                BuiltinPresetVisualBootstrapService,
                "_discover_assets",
                return_value=[asset],
            ),
            patch.object(
                BuiltinPresetVisualBootstrapService,
                "_build_storage_service",
                return_value=storage,
            ),
        ):
            BuiltinPresetVisualBootstrapService.bootstrap_builtin_preset_visuals(db)

        storage.upload_file.assert_called_once_with(
            file_path=str(asset.file_path),
            key=asset.storage_key,
            content_type="image/svg+xml",
        )
        repository.create.assert_called_once()
        created_visual = repository.create.call_args.args[1]
        self.assertEqual(created_visual.key, asset.key)
        self.assertEqual(created_visual.storage_key, asset.storage_key)
        self.assertTrue(created_visual.is_active)

    @patch("app.lifecycle.builtin_preset_visuals.PresetVisualRepository")
    def test_bootstrap_marks_missing_assets_inactive_and_removes_storage(
        self,
        repository,
    ) -> None:
        db = Mock()
        storage = Mock()
        stale_visual = SimpleNamespace(
            key="removed-visual",
            storage_key="builtin/preset-visuals/removed-visual/asset.svg",
            managed_by="lifecycle",
            is_active=True,
        )
        repository.list_managed.return_value = [stale_visual]

        with (
            patch.object(
                BuiltinPresetVisualBootstrapService,
                "_discover_assets",
                return_value=[],
            ),
            patch.object(
                BuiltinPresetVisualBootstrapService,
                "_build_storage_service",
                return_value=storage,
            ),
        ):
            BuiltinPresetVisualBootstrapService.bootstrap_builtin_preset_visuals(db)

        self.assertFalse(stale_visual.is_active)
        storage.delete_prefix.assert_called_once_with(
            prefix="builtin/preset-visuals/removed-visual"
        )
        db.flush.assert_called()

    @patch("app.lifecycle.bootstrap.SessionLocal")
    @patch(
        "app.lifecycle.bootstrap.BuiltinPresetVisualBootstrapService.bootstrap_builtin_preset_visuals"
    )
    @patch(
        "app.lifecycle.bootstrap.McpServerBootstrapService.bootstrap_builtin_servers"
    )
    @patch("app.lifecycle.bootstrap.SkillBootstrapService.bootstrap_builtin_skills")
    def test_lifecycle_bootstrap_invokes_preset_visual_bootstrap(
        self,
        bootstrap_skills,
        bootstrap_servers,
        bootstrap_preset_visuals,
        session_local,
    ) -> None:
        db = Mock()
        session_local.return_value = db

        LifecycleBootstrapService.bootstrap_all()

        bootstrap_skills.assert_called_once_with(db)
        bootstrap_servers.assert_called_once_with(db)
        bootstrap_preset_visuals.assert_called_once_with(db)


if __name__ == "__main__":
    unittest.main()
