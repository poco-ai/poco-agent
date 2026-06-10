import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.core.workspace import WorkspaceManager


class WorkspaceManagerTests(unittest.IsolatedAsyncioTestCase):
    async def test_setup_session_persistence_skips_host_claude_home(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root_path = Path(temp_dir) / "workspace"
            root_path.mkdir(parents=True)
            claude_home = Path(temp_dir) / "home" / ".claude"
            claude_home.mkdir(parents=True)
            sentinel = claude_home / "projects" / "sentinel.txt"
            sentinel.parent.mkdir(parents=True)
            sentinel.write_text("keep", encoding="utf-8")

            manager = WorkspaceManager(mount_path=str(root_path))
            manager.system_claude_home = claude_home

            with patch.object(
                WorkspaceManager,
                "_destructive_claude_symlink_allowed",
                return_value=False,
            ):
                await manager._setup_session_persistence()

            self.assertTrue(sentinel.exists())
            self.assertFalse(claude_home.is_symlink())
            self.assertTrue((root_path / ".claude_data").exists())

    async def test_cleanup_only_unlinks_managed_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root_path = Path(temp_dir) / "workspace"
            root_path.mkdir(parents=True)
            managed_target = root_path / ".claude_data"
            managed_target.mkdir()

            manager = WorkspaceManager(mount_path=str(root_path))
            claude_home = Path(temp_dir) / "home" / ".claude"
            claude_home.parent.mkdir(parents=True)
            manager.system_claude_home = claude_home
            manager.system_claude_home.symlink_to(managed_target)

            await manager.cleanup()
            self.assertFalse(manager.system_claude_home.exists())

            other_target = Path(temp_dir) / "other-claude"
            other_target.mkdir()
            manager.system_claude_home.symlink_to(other_target)

            await manager.cleanup()
            self.assertTrue(manager.system_claude_home.is_symlink())
            self.assertEqual(manager.system_claude_home.resolve(), other_target.resolve())


if __name__ == "__main__":
    unittest.main()
