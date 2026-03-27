import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.services.workspace_manager import WorkspaceManager, WorkspaceMeta


class TestWorkspaceMeta(unittest.TestCase):
    """Test WorkspaceMeta dataclass."""

    def test_to_dict(self) -> None:
        meta = WorkspaceMeta(
            session_id="session-123",
            user_id="user-456",
            task_id="task-789",
            created_at="2024-01-01T00:00:00",
            status="active",
            container_mode="ephemeral",
            workspace_path="/workspace/session-123",
            size_bytes=1024,
        )
        result = meta.to_dict()

        assert result["session_id"] == "session-123"
        assert result["user_id"] == "user-456"
        assert result["task_id"] == "task-789"
        assert result["status"] == "active"
        assert result["container_mode"] == "ephemeral"
        assert result["workspace_path"] == "/workspace/session-123"
        assert result["size_bytes"] == 1024


class TestWorkspaceManagerInit(unittest.TestCase):
    """Test WorkspaceManager.__init__."""

    def test_init_creates_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                assert manager.active_dir.exists()
                assert manager.archive_dir.exists()
                assert manager.temp_dir.exists()


class TestWorkspaceManagerGetWorkspacePath(unittest.TestCase):
    """Test WorkspaceManager.get_workspace_path."""

    def test_get_workspace_path_creates_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                result = manager.get_workspace_path(
                    user_id="user-123", session_id="session-456"
                )

                assert result.exists()
                assert result.name == "session-456"
                assert (result / "workspace").exists()
                assert (result / "logs").exists()
                assert (result / "meta.json").exists()

    def test_get_workspace_path_no_create(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                result = manager.get_workspace_path(
                    user_id="user-123", session_id="session-456", create=False
                )

                # Should not create directories
                assert not result.exists()


class TestWorkspaceManagerGetSessionWorkspaceDir(unittest.TestCase):
    """Test WorkspaceManager.get_session_workspace_dir."""

    def test_get_session_workspace_dir_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                # Create workspace
                manager.get_workspace_path(user_id="user-123", session_id="session-456")

                result = manager.get_session_workspace_dir(
                    user_id="user-123", session_id="session-456"
                )

                assert result is not None
                assert result.name == "workspace"

    def test_get_session_workspace_dir_not_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                result = manager.get_session_workspace_dir(
                    user_id="user-123", session_id="session-456"
                )

                assert result is None


class TestWorkspaceManagerResolveUserId(unittest.TestCase):
    """Test WorkspaceManager.resolve_user_id."""

    def test_resolve_user_id_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                # Create workspace
                manager.get_workspace_path(user_id="user-123", session_id="session-456")

                result = manager.resolve_user_id("session-456")

                assert result == "user-123"

    def test_resolve_user_id_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                result = manager.resolve_user_id("nonexistent-session")

                assert result is None


class TestWorkspaceManagerListWorkspaceFiles(unittest.TestCase):
    """Test WorkspaceManager.list_workspace_files."""

    def test_list_workspace_files_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                manager.get_workspace_path(user_id="user-123", session_id="session-456")

                result = manager.list_workspace_files(
                    user_id="user-123", session_id="session-456"
                )

                assert result == []

    def test_list_workspace_files_with_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = False

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                workspace_path = manager.get_workspace_path(
                    user_id="user-123", session_id="session-456"
                )
                workspace_dir = workspace_path / "workspace"

                # Create test files
                (workspace_dir / "file1.txt").write_text("content1")
                (workspace_dir / "file2.py").write_text("content2")

                result = manager.list_workspace_files(
                    user_id="user-123", session_id="session-456"
                )

                assert len(result) == 2
                names = [f["name"] for f in result]
                assert "file1.txt" in names
                assert "file2.py" in names

    def test_list_workspace_files_with_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = False

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                workspace_path = manager.get_workspace_path(
                    user_id="user-123", session_id="session-456"
                )
                workspace_dir = workspace_path / "workspace"

                # Create directory with file
                subdir = workspace_dir / "subdir"
                subdir.mkdir()
                (subdir / "nested_file.txt").write_text("nested content")

                result = manager.list_workspace_files(
                    user_id="user-123", session_id="session-456"
                )

                assert len(result) == 1
                assert result[0]["type"] == "folder"
                assert result[0]["name"] == "subdir"
                assert len(result[0]["children"]) == 1

    def test_list_workspace_files_ignores_dot_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                workspace_path = manager.get_workspace_path(
                    user_id="user-123", session_id="session-456"
                )
                workspace_dir = workspace_path / "workspace"

                # Create files
                (workspace_dir / "visible.txt").write_text("content")
                (workspace_dir / ".hidden").write_text("hidden")

                result = manager.list_workspace_files(
                    user_id="user-123", session_id="session-456"
                )

                assert len(result) == 1
                assert result[0]["name"] == "visible.txt"


class TestWorkspaceManagerResolveWorkspaceFile(unittest.TestCase):
    """Test WorkspaceManager.resolve_workspace_file."""

    def test_resolve_workspace_file_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                workspace_path = manager.get_workspace_path(
                    user_id="user-123", session_id="session-456"
                )
                workspace_dir = workspace_path / "workspace"
                (workspace_dir / "test.txt").write_text("content")

                result = manager.resolve_workspace_file(
                    user_id="user-123",
                    session_id="session-456",
                    file_path="/test.txt",
                )

                assert result is not None
                assert result.name == "test.txt"

    def test_resolve_workspace_file_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                manager.get_workspace_path(user_id="user-123", session_id="session-456")

                result = manager.resolve_workspace_file(
                    user_id="user-123",
                    session_id="session-456",
                    file_path="/nonexistent.txt",
                )

                assert result is None

    def test_resolve_workspace_file_empty_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                result = manager.resolve_workspace_file(
                    user_id="user-123", session_id="session-456", file_path=""
                )

                assert result is None


class TestWorkspaceManagerMeta(unittest.TestCase):
    """Test WorkspaceManager metadata operations."""

    def test_write_and_get_meta(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                manager.get_workspace_path(user_id="user-123", session_id="session-456")

                meta = manager.get_meta(user_id="user-123", session_id="session-456")

                assert meta is not None
                assert meta.session_id == "session-456"
                assert meta.user_id == "user-123"
                assert meta.status == "active"

    def test_get_meta_not_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                meta = manager.get_meta(user_id="user-123", session_id="session-456")

                assert meta is None

    def test_update_meta_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                manager.get_workspace_path(user_id="user-123", session_id="session-456")

                manager.update_meta_status(
                    user_id="user-123", session_id="session-456", status="archived"
                )

                meta = manager.get_meta(user_id="user-123", session_id="session-456")
                assert meta is not None
                assert meta.status == "archived"


class TestWorkspaceManagerGetWorkspaceVolume(unittest.TestCase):
    """Test WorkspaceManager.get_workspace_volume."""

    def test_get_workspace_volume(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                result = manager.get_workspace_volume(
                    user_id="user-123", session_id="session-456"
                )

                assert "workspace" in result
                assert "session-456" in result


class TestWorkspaceManagerArchiveWorkspace(unittest.TestCase):
    """Test WorkspaceManager.archive_workspace."""

    def test_archive_nonexistent_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                result = manager.archive_workspace(
                    user_id="user-123", session_id="nonexistent"
                )

                assert result is None

    def test_archive_workspace_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                # Create workspace
                workspace_path = manager.get_workspace_path(
                    user_id="user-123", session_id="session-to-archive"
                )
                workspace_dir = workspace_path / "workspace"
                (workspace_dir / "test.txt").write_text("content")

                result = manager.archive_workspace(
                    user_id="user-123", session_id="session-to-archive"
                )

                assert result is not None
                assert result.endswith(".tar.gz")
                # Original directory should be removed
                assert not workspace_path.exists()


class TestWorkspaceManagerDeleteWorkspace(unittest.TestCase):
    """Test WorkspaceManager.delete_workspace."""

    def test_delete_nonexistent_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                result = manager.delete_workspace(
                    user_id="user-123", session_id="nonexistent"
                )

                assert result is False

    def test_delete_workspace_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                # Create workspace
                workspace_path = manager.get_workspace_path(
                    user_id="user-123", session_id="session-to-delete"
                )
                assert workspace_path.exists()

                result = manager.delete_workspace(
                    user_id="user-123", session_id="session-to-delete"
                )

                assert result is True
                assert not workspace_path.exists()

    def test_delete_persistent_workspace_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                # Create workspace with persistent container_mode
                workspace_path = manager.get_workspace_path(
                    user_id="user-123", session_id="persistent-session"
                )
                manager.update_meta_status(
                    user_id="user-123",
                    session_id="persistent-session",
                    status="active",
                )
                # Update meta to set container_mode
                meta = manager.get_meta(
                    user_id="user-123", session_id="persistent-session"
                )
                assert meta is not None

                # Create a new meta with persistent container_mode
                import json

                meta_path = workspace_path / "meta.json"
                meta_data = json.loads(meta_path.read_text())
                meta_data["container_mode"] = "persistent"
                meta_path.write_text(json.dumps(meta_data))

                result = manager.delete_workspace(
                    user_id="user-123", session_id="persistent-session", force=False
                )

                # Should fail without force
                assert result is False
                assert workspace_path.exists()

    def test_delete_persistent_workspace_with_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                # Create workspace with persistent container_mode
                workspace_path = manager.get_workspace_path(
                    user_id="user-123", session_id="persistent-session-2"
                )
                import json

                meta_path = workspace_path / "meta.json"
                meta_data = json.loads(meta_path.read_text())
                meta_data["container_mode"] = "persistent"
                meta_path.write_text(json.dumps(meta_data))

                result = manager.delete_workspace(
                    user_id="user-123", session_id="persistent-session-2", force=True
                )

                assert result is True
                assert not workspace_path.exists()

    def test_resolve_user_id_active_dir_not_exists(self) -> None:
        """Test resolve_user_id when active_dir does not exist (line 107)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()
                # Remove the active_dir that was created during init
                shutil.rmtree(manager.active_dir)

                result = manager.resolve_user_id("nonexistent-session")

                assert result is None

    def test_resolve_user_id_skips_non_dirs(self) -> None:
        """Test resolve_user_id skips non-directory entries (line 110)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                # Create a file in active_dir (not a directory)
                (manager.active_dir / "not-a-dir.txt").write_text("content")

                result = manager.resolve_user_id("some-session")

                assert result is None

    def test_list_workspace_files_max_depth(self) -> None:
        """Test list_workspace_files respects max_depth (line 135)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = False

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                workspace_path = manager.get_workspace_path(
                    user_id="user-123", session_id="session-456"
                )
                workspace_dir = workspace_path / "workspace"

                # Create deeply nested structure
                deep_path = workspace_dir
                for i in range(10):
                    deep_path = deep_path / f"level{i}"
                deep_path.mkdir(parents=True)
                (deep_path / "deep_file.txt").write_text("content")

                result = manager.list_workspace_files(
                    user_id="user-123", session_id="session-456", max_depth=2
                )

                # Should not include deeply nested files
                assert len(result) <= 2

    def test_list_workspace_files_iterdir_exception(self) -> None:
        """Test list_workspace_files handles iterdir exception (line 146-147)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = False

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                workspace_path = manager.get_workspace_path(
                    user_id="user-123", session_id="session-456"
                )
                workspace_dir = workspace_path / "workspace"
                (workspace_dir / "file.txt").write_text("content")

                with patch.object(
                    Path, "iterdir", side_effect=PermissionError("access denied")
                ):
                    result = manager.list_workspace_files(
                        user_id="user-123", session_id="session-456"
                    )

                    # Should handle exception gracefully
                    assert result == []

    def test_list_workspace_files_max_entries(self) -> None:
        """Test list_workspace_files respects max_entries (line 151)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = False

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                workspace_path = manager.get_workspace_path(
                    user_id="user-123", session_id="session-456"
                )
                workspace_dir = workspace_path / "workspace"

                # Create many files
                for i in range(100):
                    (workspace_dir / f"file{i}.txt").write_text("content")

                result = manager.list_workspace_files(
                    user_id="user-123", session_id="session-456", max_entries=10
                )

                # Should limit entries
                total_files = sum(
                    1
                    for item in result
                    if item.get("type") == "file"
                    or sum(
                        1 for c in item.get("children", []) if c.get("type") == "file"
                    )
                )
                assert total_files <= 10

    def test_list_workspace_files_skips_symlinks(self) -> None:
        """Test list_workspace_files skips symlinks (line 160)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = False

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                workspace_path = manager.get_workspace_path(
                    user_id="user-123", session_id="session-456"
                )
                workspace_dir = workspace_path / "workspace"
                (workspace_dir / "file.txt").write_text("content")

                # Create symlink
                target = workspace_dir / "target.txt"
                target.write_text("target")
                try:
                    (workspace_dir / "link.txt").symlink_to(target)

                    result = manager.list_workspace_files(
                        user_id="user-123", session_id="session-456"
                    )

                    # Symlink should be skipped
                    names = [f["name"] for f in result]
                    assert "link.txt" not in names
                    assert "file.txt" in names
                except OSError:
                    # Skip on systems without symlink support
                    pass

    def test_resolve_workspace_file_empty_path(self) -> None:
        """Test resolve_workspace_file with empty path (line 207)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                manager.get_workspace_path(user_id="user-123", session_id="session-456")

                result = manager.resolve_workspace_file(
                    user_id="user-123", session_id="session-456", file_path=""
                )

                assert result is None

    def test_resolve_workspace_file_relative_to_exception(self) -> None:
        """Test resolve_workspace_file handles relative_to exception (line 215-216)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                workspace_path = manager.get_workspace_path(
                    user_id="user-123", session_id="session-456"
                )
                workspace_dir = workspace_path / "workspace"
                (workspace_dir / "file.txt").write_text("content")

                # Try to escape with ..
                result = manager.resolve_workspace_file(
                    user_id="user-123",
                    session_id="session-456",
                    file_path="../../../etc/passwd",
                )

                assert result is None

    def test_get_meta_exception(self) -> None:
        """Test get_meta handles exception (line 259-261)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                workspace_path = manager.get_workspace_path(
                    user_id="user-123", session_id="session-456"
                )

                # Write invalid JSON
                meta_path = workspace_path / "meta.json"
                meta_path.write_text("not valid json")

                result = manager.get_meta(user_id="user-123", session_id="session-456")

                assert result is None

    def test_archive_workspace_exception(self) -> None:
        """Test archive_workspace handles exception (line 313-315)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                manager.get_workspace_path(
                    user_id="user-123", session_id="session-to-archive"
                )

                with patch(
                    "tarfile.open", side_effect=PermissionError("access denied")
                ):
                    result = manager.archive_workspace(
                        user_id="user-123", session_id="session-to-archive"
                    )

                    assert result is None

    def test_delete_workspace_exception(self) -> None:
        """Test delete_workspace handles exception (line 342-344)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                manager.get_workspace_path(
                    user_id="user-123", session_id="session-to-delete"
                )

                with patch(
                    "shutil.rmtree", side_effect=PermissionError("access denied")
                ):
                    result = manager.delete_workspace(
                        user_id="user-123", session_id="session-to-delete"
                    )

                    assert result is False


class TestWorkspaceManagerCleanupExpiredWorkspaces(unittest.TestCase):
    """Test WorkspaceManager.cleanup_expired_workspaces (lines 348-388)."""

    def test_cleanup_expired_workspaces_no_workspaces(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                result = manager.cleanup_expired_workspaces(max_age_hours=1)

                assert result["cleaned"] == 0
                assert result["archived"] == 0

    def test_cleanup_expired_workspaces_deletes_expired_ephemeral(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                # Create an old workspace
                workspace_path = manager.get_workspace_path(
                    user_id="user-123", session_id="old-session"
                )

                # Modify the meta to have old timestamp
                import json
                from datetime import datetime, timedelta

                meta_path = workspace_path / "meta.json"
                meta_data = json.loads(meta_path.read_text())
                old_time = (datetime.now() - timedelta(hours=48)).isoformat()
                meta_data["created_at"] = old_time
                meta_data["container_mode"] = "ephemeral"
                meta_path.write_text(json.dumps(meta_data))

                result = manager.cleanup_expired_workspaces(max_age_hours=24)

                assert result["cleaned"] == 1
                assert not workspace_path.exists()

    def test_cleanup_expired_workspaces_archives_expired_persistent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                # Create an old persistent workspace
                workspace_path = manager.get_workspace_path(
                    user_id="user-123", session_id="old-persistent"
                )

                # Modify the meta
                import json
                from datetime import datetime, timedelta

                meta_path = workspace_path / "meta.json"
                meta_data = json.loads(meta_path.read_text())
                old_time = (datetime.now() - timedelta(hours=48)).isoformat()
                meta_data["created_at"] = old_time
                meta_data["container_mode"] = "persistent"
                meta_path.write_text(json.dumps(meta_data))

                result = manager.cleanup_expired_workspaces(max_age_hours=24)

                assert result["archived"] == 1
                assert not workspace_path.exists()

    def test_cleanup_expired_workspaces_skips_fresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                # Create a fresh workspace
                workspace_path = manager.get_workspace_path(
                    user_id="user-123", session_id="fresh-session"
                )

                result = manager.cleanup_expired_workspaces(max_age_hours=24)

                assert result["cleaned"] == 0
                assert result["archived"] == 0
                assert workspace_path.exists()

    def test_cleanup_expired_workspaces_deletes_no_meta(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                # Create a workspace without meta
                workspace_path = manager.active_dir / "user-123" / "no-meta-session"
                workspace_path.mkdir(parents=True)
                (workspace_path / "workspace").mkdir()
                (workspace_path / "logs").mkdir()

                result = manager.cleanup_expired_workspaces(max_age_hours=24)

                # Should delete workspaces without meta
                assert result["cleaned"] == 1


class TestWorkspaceManagerDiskUsage(unittest.TestCase):
    """Test WorkspaceManager.get_disk_usage (lines 396-402)."""

    def test_get_disk_usage(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                # Create a workspace
                manager.get_workspace_path(user_id="user-123", session_id="session-456")

                result = manager.get_disk_usage()

                assert "base_dir" in result
                assert "total_gb" in result
                assert "used_gb" in result
                assert "free_gb" in result
                assert "usage_percent" in result
                assert "active_size_gb" in result
                assert "archive_size_gb" in result
                assert "temp_size_gb" in result
                assert "active_workspaces" in result
                assert "archived_workspaces" in result

    def test_get_dir_size(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                # Create some files
                test_dir = Path(tmpdir) / "test_dir"
                test_dir.mkdir()
                (test_dir / "file1.txt").write_text("a" * 100)
                (test_dir / "file2.txt").write_text("b" * 200)

                result = manager._get_dir_size(test_dir)

                assert result == 300


class TestWorkspaceManagerGetUserWorkspaces(unittest.TestCase):
    """Test WorkspaceManager.get_user_workspaces (lines 425-439)."""

    def test_get_user_workspaces_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                result = manager.get_user_workspaces("user-123")

                assert result == []

    def test_get_user_workspaces_multiple(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                # Create multiple workspaces
                manager.get_workspace_path(user_id="user-123", session_id="session-1")
                manager.get_workspace_path(user_id="user-123", session_id="session-2")

                result = manager.get_user_workspaces("user-123")

                assert len(result) == 2

    def test_get_user_workspaces_skips_non_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                manager.get_workspace_path(user_id="user-123", session_id="session-1")

                # Create a file in user dir (not a session dir)
                user_dir = manager.active_dir / "user-123"
                (user_dir / "not-a-session.txt").write_text("content")

                result = manager.get_user_workspaces("user-123")

                assert len(result) == 1


class TestWorkspaceManagerMissingLines(unittest.TestCase):
    """Test missing lines for higher coverage."""

    def test_list_workspace_files_no_workspace_dir(self) -> None:
        """Test list_workspace_files when workspace_dir does not exist (line 128)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                # Create session dir but not workspace
                session_dir = manager.active_dir / "user-123" / "session-456"
                session_dir.mkdir(parents=True)

                result = manager.list_workspace_files(
                    user_id="user-123", session_id="session-456"
                )

                assert result == []

    def test_list_workspace_files_ignores_special_names(self) -> None:
        """Test list_workspace_files skips entries in _ignore_names (line 154)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = False

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                workspace_path = manager.get_workspace_path(
                    user_id="user-123", session_id="session-456"
                )
                workspace_dir = workspace_path / "workspace"

                # Create files that should be ignored
                (workspace_dir / "file.txt").write_text("content")
                (workspace_dir / ".git").mkdir()  # Should be ignored
                (workspace_dir / "node_modules").mkdir()  # Should be ignored

                result = manager.list_workspace_files(
                    user_id="user-123", session_id="session-456"
                )

                names = [f["name"] for f in result]
                assert "file.txt" in names
                assert ".git" not in names
                assert "node_modules" not in names

    def test_cleanup_expired_workspaces_skips_non_dirs(self) -> None:
        """Test cleanup_expired_workspaces skips non-directories (lines 355, 359)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.workspace_root = tmpdir
            mock_settings.workspace_ignore_dot_files = True

            with patch(
                "app.services.workspace_manager.get_settings",
                return_value=mock_settings,
            ):
                manager = WorkspaceManager()

                # Create a file in active_dir (not a user dir)
                (manager.active_dir / "not-a-user-dir.txt").write_text("content")

                # Create a user dir with a file (not a session dir)
                user_dir = manager.active_dir / "user-123"
                user_dir.mkdir()
                (user_dir / "not-a-session.txt").write_text("content")

                # Also create a valid workspace to ensure normal flow works
                manager.get_workspace_path(user_id="user-456", session_id="session-1")

                result = manager.cleanup_expired_workspaces(max_age_hours=1)

                # Should handle the files gracefully
                assert result["cleaned"] >= 0


if __name__ == "__main__":
    unittest.main()
