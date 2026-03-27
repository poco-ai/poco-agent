"""Tests for workspace_export_service.py."""

import tempfile
import unittest
import zipfile
from pathlib import Path, PurePosixPath
from unittest.mock import MagicMock, patch

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.services.workspace_export_service import (
    _ALLOWED_HIDDEN_SKILL_ROOTS,
    _SKILL_VISIBLE_ROOT,
    _VISIBLE_DRAFT_ROOT,
    WorkspaceExportService,
)


class TestConstants(unittest.TestCase):
    """Test module-level constants."""

    def test_allowed_hidden_skill_roots(self) -> None:
        """Test _ALLOWED_HIDDEN_SKILL_ROOTS contains expected values."""
        assert ".config" in _ALLOWED_HIDDEN_SKILL_ROOTS
        assert ".config_data" in _ALLOWED_HIDDEN_SKILL_ROOTS
        assert len(_ALLOWED_HIDDEN_SKILL_ROOTS) == 2

    def test_skill_visible_root(self) -> None:
        """Test _SKILL_VISIBLE_ROOT path."""
        assert _SKILL_VISIBLE_ROOT == PurePosixPath("/.config/skills")

    def test_visible_draft_root(self) -> None:
        """Test _VISIBLE_DRAFT_ROOT path."""
        assert _VISIBLE_DRAFT_ROOT == PurePosixPath("/skills")


class TestNormalizeWorkspacePath(unittest.TestCase):
    """Test WorkspaceExportService._normalize_workspace_path."""

    def test_normalize_simple_path(self) -> None:
        """Test normalizing a simple path."""
        result = WorkspaceExportService._normalize_workspace_path("skills/my-skill")
        assert result == "/skills/my-skill"

    def test_normalize_path_with_backslashes(self) -> None:
        """Test normalizing path with backslashes."""
        result = WorkspaceExportService._normalize_workspace_path(
            "skills\\my-skill\\subdir"
        )
        assert result == "/skills/my-skill/subdir"

    def test_normalize_path_with_leading_slash(self) -> None:
        """Test normalizing path with leading slash."""
        result = WorkspaceExportService._normalize_workspace_path("/skills/my-skill")
        assert result == "/skills/my-skill"

    def test_normalize_path_with_workspace_prefix(self) -> None:
        """Test normalizing path with /workspace/ prefix."""
        result = WorkspaceExportService._normalize_workspace_path(
            "/workspace/skills/my-skill"
        )
        assert result == "/skills/my-skill"

    def test_normalize_path_with_whitespace(self) -> None:
        """Test normalizing path with leading/trailing whitespace."""
        result = WorkspaceExportService._normalize_workspace_path(
            "  /skills/my-skill  "
        )
        assert result == "/skills/my-skill"

    def test_normalize_empty_path_raises(self) -> None:
        """Test empty path raises AppException."""
        with self.assertRaises(AppException) as ctx:
            WorkspaceExportService._normalize_workspace_path("")
        assert ctx.exception.error_code == ErrorCode.BAD_REQUEST
        assert "Invalid workspace folder path" in ctx.exception.message

    def test_normalize_none_path_raises(self) -> None:
        """Test None path raises AppException."""
        with self.assertRaises(AppException) as ctx:
            WorkspaceExportService._normalize_workspace_path(None)  # type: ignore
        assert ctx.exception.error_code == ErrorCode.BAD_REQUEST

    def test_normalize_workspace_root_raises(self) -> None:
        """Test /workspace path raises AppException."""
        with self.assertRaises(AppException) as ctx:
            WorkspaceExportService._normalize_workspace_path("/workspace")
        assert ctx.exception.error_code == ErrorCode.BAD_REQUEST
        assert "must point to a folder, not /workspace" in ctx.exception.message

    def test_normalize_path_with_dot_raises(self) -> None:
        """Test path with '.' raises AppException."""
        with self.assertRaises(AppException) as ctx:
            WorkspaceExportService._normalize_workspace_path("skills/./my-skill")
        assert ctx.exception.error_code == ErrorCode.BAD_REQUEST

    def test_normalize_path_with_double_dot_raises(self) -> None:
        """Test path with '..' raises AppException."""
        with self.assertRaises(AppException) as ctx:
            WorkspaceExportService._normalize_workspace_path("skills/../my-skill")
        assert ctx.exception.error_code == ErrorCode.BAD_REQUEST

    def test_normalize_path_removes_duplicate_slashes(self) -> None:
        """Test duplicate slashes are collapsed."""
        result = WorkspaceExportService._normalize_workspace_path(
            "skills//my-skill///subdir"
        )
        assert result == "/skills/my-skill/subdir"


class TestResolveWorkspaceDir(unittest.TestCase):
    """Test WorkspaceExportService._resolve_workspace_dir."""

    def test_resolve_simple_path(self) -> None:
        """Test resolving a simple relative path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir)
            result = WorkspaceExportService._resolve_workspace_dir(
                workspace_dir=workspace_dir,
                relative_path="/skills/my-skill",
            )
            assert result == workspace_dir / "skills" / "my-skill"

    def test_resolve_path_with_multiple_leading_slashes(self) -> None:
        """Test resolving path with multiple leading slashes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir)
            result = WorkspaceExportService._resolve_workspace_dir(
                workspace_dir=workspace_dir,
                relative_path="///skills/my-skill",
            )
            assert result == workspace_dir / "skills" / "my-skill"

    def test_resolve_path_escape_raises(self) -> None:
        """Test path escaping workspace raises AppException."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir)
            with self.assertRaises(AppException) as ctx:
                WorkspaceExportService._resolve_workspace_dir(
                    workspace_dir=workspace_dir,
                    relative_path="/../outside",
                )
            assert ctx.exception.error_code == ErrorCode.BAD_REQUEST
            assert "escapes workspace" in ctx.exception.message

    def test_resolve_path_with_create_parent(self) -> None:
        """Test creating parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir)
            result = WorkspaceExportService._resolve_workspace_dir(
                workspace_dir=workspace_dir,
                relative_path="/skills/my-skill",
                create_parent=True,
            )
            assert result.parent.exists()

    def test_resolve_path_without_create_parent(self) -> None:
        """Test not creating parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir)
            result = WorkspaceExportService._resolve_workspace_dir(
                workspace_dir=workspace_dir,
                relative_path="/skills/my-skill",
                create_parent=False,
            )
            assert not result.parent.exists()


class TestIsVisibleSkillFolder(unittest.TestCase):
    """Test WorkspaceExportService._is_visible_skill_folder."""

    def test_visible_skill_folder(self) -> None:
        """Test visible skill folder path."""
        result = WorkspaceExportService._is_visible_skill_folder(
            "/.config/skills/my-skill"
        )
        assert result is True

    def test_hidden_config_path(self) -> None:
        """Test hidden config path is not visible."""
        result = WorkspaceExportService._is_visible_skill_folder(
            "/.config_data/skills/my-skill"
        )
        assert result is False

    def test_skills_draft_path(self) -> None:
        """Test skills draft path is not visible."""
        result = WorkspaceExportService._is_visible_skill_folder("/skills/my-skill")
        assert result is False

    def test_wrong_depth(self) -> None:
        """Test path with wrong depth is not visible."""
        result = WorkspaceExportService._is_visible_skill_folder(
            "/.config/skills/my-skill/subdir"
        )
        assert result is False

    def test_missing_config_segment(self) -> None:
        """Test path missing .config segment."""
        result = WorkspaceExportService._is_visible_skill_folder(
            "/other/skills/my-skill"
        )
        assert result is False


class TestPreferVisibleWorkspaceDraft(unittest.TestCase):
    """Test WorkspaceExportService._prefer_visible_workspace_draft."""

    def test_non_visible_skill_returns_original(self) -> None:
        """Test non-visible skill path returns original."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir)
            source_dir = workspace_dir / "skills" / "my-skill"
            source_dir.mkdir(parents=True)

            result_path, result_dir = (
                WorkspaceExportService._prefer_visible_workspace_draft(
                    workspace_dir=workspace_dir,
                    normalized_folder_path="/skills/my-skill",
                    source_dir=source_dir,
                )
            )
            assert result_path == "/skills/my-skill"
            assert result_dir == source_dir

    def test_visible_skill_without_draft_returns_original(self) -> None:
        """Test visible skill without draft returns original."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir)
            source_dir = workspace_dir / ".config" / "skills" / "my-skill"
            source_dir.mkdir(parents=True)

            result_path, result_dir = (
                WorkspaceExportService._prefer_visible_workspace_draft(
                    workspace_dir=workspace_dir,
                    normalized_folder_path="/.config/skills/my-skill",
                    source_dir=source_dir,
                )
            )
            assert result_path == "/.config/skills/my-skill"
            assert result_dir == source_dir

    def test_visible_skill_with_draft_returns_draft(self) -> None:
        """Test visible skill with draft returns draft."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir)

            # Create source skill
            source_dir = workspace_dir / ".config" / "skills" / "my-skill"
            source_dir.mkdir(parents=True)
            (source_dir / "SKILL.md").write_text("# My Skill")

            # Create visible draft
            draft_dir = workspace_dir / "skills" / "my-skill"
            draft_dir.mkdir(parents=True)
            (draft_dir / "SKILL.md").write_text("# My Skill Draft")

            result_path, result_dir = (
                WorkspaceExportService._prefer_visible_workspace_draft(
                    workspace_dir=workspace_dir,
                    normalized_folder_path="/.config/skills/my-skill",
                    source_dir=source_dir,
                )
            )
            assert result_path == "/skills/my-skill"
            assert result_dir == draft_dir

    def test_visible_skill_draft_without_skill_md_returns_original(self) -> None:
        """Test draft without SKILL.md returns original."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir)

            # Create source skill
            source_dir = workspace_dir / ".config" / "skills" / "my-skill"
            source_dir.mkdir(parents=True)
            (source_dir / "SKILL.md").write_text("# My Skill")

            # Create visible draft without SKILL.md
            draft_dir = workspace_dir / "skills" / "my-skill"
            draft_dir.mkdir(parents=True)
            # No SKILL.md in draft

            result_path, result_dir = (
                WorkspaceExportService._prefer_visible_workspace_draft(
                    workspace_dir=workspace_dir,
                    normalized_folder_path="/.config/skills/my-skill",
                    source_dir=source_dir,
                )
            )
            assert result_path == "/.config/skills/my-skill"
            assert result_dir == source_dir


class TestIsAllowedHiddenSkillPath(unittest.TestCase):
    """Test WorkspaceExportService._is_allowed_hidden_skill_path."""

    def test_allowed_config_path(self) -> None:
        """Test .config/skills is allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir)
            skill_path = workspace_dir / ".config" / "skills" / "my-skill"
            skill_path.mkdir(parents=True)

            result = WorkspaceExportService._is_allowed_hidden_skill_path(
                skill_path, workspace_dir
            )
            assert result is True

    def test_allowed_config_data_path(self) -> None:
        """Test .config_data/skills is allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir)
            skill_path = workspace_dir / ".config_data" / "skills" / "my-skill"
            skill_path.mkdir(parents=True)

            result = WorkspaceExportService._is_allowed_hidden_skill_path(
                skill_path, workspace_dir
            )
            assert result is True

    def test_allowed_config_root(self) -> None:
        """Test .config root directory is allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir)
            config_path = workspace_dir / ".config"
            config_path.mkdir(parents=True)

            result = WorkspaceExportService._is_allowed_hidden_skill_path(
                config_path, workspace_dir
            )
            assert result is True

    def test_disallowed_hidden_path(self) -> None:
        """Test other hidden paths are not allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir)
            hidden_path = workspace_dir / ".hidden" / "file.txt"
            hidden_path.mkdir(parents=True)

            result = WorkspaceExportService._is_allowed_hidden_skill_path(
                hidden_path, workspace_dir
            )
            assert result is False

    def test_config_non_skills_subdir(self) -> None:
        """Test .config with non-skills subdir is not allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir)
            other_path = workspace_dir / ".config" / "other"
            other_path.mkdir(parents=True)

            result = WorkspaceExportService._is_allowed_hidden_skill_path(
                other_path, workspace_dir
            )
            assert result is False

    def test_path_outside_workspace(self) -> None:
        """Test path outside workspace returns False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir)
            outside_path = Path(tmpdir).parent / "outside"

            result = WorkspaceExportService._is_allowed_hidden_skill_path(
                outside_path, workspace_dir
            )
            assert result is False


class TestCollectFolderFiles(unittest.TestCase):
    """Test WorkspaceExportService._collect_folder_files."""

    def test_collect_folder_files(self) -> None:
        """Test collecting files from a folder."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir)
            folder_dir = workspace_dir / "skills" / "my-skill"
            folder_dir.mkdir(parents=True)
            (folder_dir / "file1.txt").write_text("content1")
            (folder_dir / "subdir").mkdir()
            (folder_dir / "subdir" / "file2.txt").write_text("content2")

            result = WorkspaceExportService._collect_folder_files(
                workspace_dir=workspace_dir,
                folder_dir=folder_dir,
            )

            assert len(result) == 2
            file_names = {f.name for f in result}
            assert "file1.txt" in file_names
            assert "file2.txt" in file_names

    def test_collect_folder_files_skips_symlinks(self) -> None:
        """Test that symlinks are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir)
            folder_dir = workspace_dir / "skills" / "my-skill"
            folder_dir.mkdir(parents=True)
            (folder_dir / "real.txt").write_text("content")
            (folder_dir / "link.txt").symlink_to(folder_dir / "real.txt")

            result = WorkspaceExportService._collect_folder_files(
                workspace_dir=workspace_dir,
                folder_dir=folder_dir,
            )

            assert len(result) == 1
            assert result[0].name == "real.txt"

    def test_collect_folder_files_empty(self) -> None:
        """Test collecting from empty folder."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir)
            folder_dir = workspace_dir / "empty"
            folder_dir.mkdir(parents=True)

            result = WorkspaceExportService._collect_folder_files(
                workspace_dir=workspace_dir,
                folder_dir=folder_dir,
            )

            assert result == []


class TestShouldSkip(unittest.TestCase):
    """Test WorkspaceExportService._should_skip."""

    def test_skip_by_ignore_names(self) -> None:
        """Test skipping by ignore_names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir)
            skip_path = workspace_dir / "node_modules"
            skip_path.mkdir()

            service = WorkspaceExportService()
            result = service._should_skip(
                skip_path,
                workspace_dir=workspace_dir,
                ignore_names={"node_modules", ".git"},
                ignore_dot=False,
            )
            assert result is True

    def test_skip_dot_files(self) -> None:
        """Test skipping dot files when ignore_dot=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir)
            dot_path = workspace_dir / ".hidden"
            dot_path.mkdir()

            service = WorkspaceExportService()
            result = service._should_skip(
                dot_path,
                workspace_dir=workspace_dir,
                ignore_names=set(),
                ignore_dot=True,
            )
            assert result is True

    def test_skip_allowed_hidden_skill_path(self) -> None:
        """Test not skipping allowed hidden skill paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir)
            skill_path = workspace_dir / ".config" / "skills" / "my-skill"
            skill_path.mkdir(parents=True)

            service = WorkspaceExportService()
            result = service._should_skip(
                skill_path,
                workspace_dir=workspace_dir,
                ignore_names=set(),
                ignore_dot=True,
            )
            assert result is False

    def test_skip_symlink(self) -> None:
        """Test skipping symlinks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir)
            real_path = workspace_dir / "real"
            real_path.mkdir()
            link_path = workspace_dir / "link"
            link_path.symlink_to(real_path)

            service = WorkspaceExportService()
            result = service._should_skip(
                link_path,
                workspace_dir=workspace_dir,
                ignore_names=set(),
                ignore_dot=False,
            )
            assert result is True

    def test_no_skip_normal_path(self) -> None:
        """Test not skipping normal paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir)
            normal_path = workspace_dir / "skills"
            normal_path.mkdir()

            service = WorkspaceExportService()
            result = service._should_skip(
                normal_path,
                workspace_dir=workspace_dir,
                ignore_names=set(),
                ignore_dot=False,
            )
            assert result is False


class TestCollectFiles(unittest.TestCase):
    """Test WorkspaceExportService._collect_files."""

    def test_collect_files(self) -> None:
        """Test collecting files from workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir)
            (workspace_dir / "file1.txt").write_text("content1")
            (workspace_dir / "subdir").mkdir()
            (workspace_dir / "subdir" / "file2.txt").write_text("content2")

            mock_wm = MagicMock()
            mock_wm._ignore_names = set()
            mock_wm.ignore_dot_files = False

            with patch(
                "app.services.workspace_export_service.workspace_manager",
                mock_wm,
            ):
                service = WorkspaceExportService()
                result = service._collect_files(workspace_dir)

            assert len(result) == 2
            file_names = {f.name for f in result}
            assert "file1.txt" in file_names
            assert "file2.txt" in file_names

    def test_collect_files_skips_ignored_names(self) -> None:
        """Test that ignored directories are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir)
            (workspace_dir / "file.txt").write_text("content")
            (workspace_dir / "node_modules").mkdir()
            (workspace_dir / "node_modules" / "skip.txt").write_text("skip")

            mock_wm = MagicMock()
            mock_wm._ignore_names = {"node_modules"}
            mock_wm.ignore_dot_files = False

            with patch(
                "app.services.workspace_export_service.workspace_manager",
                mock_wm,
            ):
                service = WorkspaceExportService()
                result = service._collect_files(workspace_dir)

            assert len(result) == 1
            assert result[0].name == "file.txt"

    def test_collect_files_skips_dot_files(self) -> None:
        """Test that dot files are skipped when ignore_dot is True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir)
            (workspace_dir / "file.txt").write_text("content")
            (workspace_dir / ".hidden").write_text("hidden")

            mock_wm = MagicMock()
            mock_wm._ignore_names = set()
            mock_wm.ignore_dot_files = True

            with patch(
                "app.services.workspace_export_service.workspace_manager",
                mock_wm,
            ):
                service = WorkspaceExportService()
                result = service._collect_files(workspace_dir)

            assert len(result) == 1
            assert result[0].name == "file.txt"

    def test_collect_files_includes_allowed_hidden(self) -> None:
        """Test that allowed hidden skill paths are included."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir)
            (workspace_dir / "file.txt").write_text("content")
            skill_dir = workspace_dir / ".config" / "skills" / "my-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# Skill")

            mock_wm = MagicMock()
            mock_wm._ignore_names = set()
            mock_wm.ignore_dot_files = True

            with patch(
                "app.services.workspace_export_service.workspace_manager",
                mock_wm,
            ):
                service = WorkspaceExportService()
                result = service._collect_files(workspace_dir)

            assert len(result) == 2
            file_names = {f.name for f in result}
            assert "file.txt" in file_names
            assert "SKILL.md" in file_names

    def test_collect_files_skips_symlinks(self) -> None:
        """Test that symlinks are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir)
            real_file = workspace_dir / "real.txt"
            real_file.write_text("content")
            (workspace_dir / "link.txt").symlink_to(real_file)

            mock_wm = MagicMock()
            mock_wm._ignore_names = set()
            mock_wm.ignore_dot_files = False

            with patch(
                "app.services.workspace_export_service.workspace_manager",
                mock_wm,
            ):
                service = WorkspaceExportService()
                result = service._collect_files(workspace_dir)

            assert len(result) == 1
            assert result[0].name == "real.txt"


class TestCreateArchive(unittest.TestCase):
    """Test WorkspaceExportService._create_archive."""

    def test_create_archive(self) -> None:
        """Test creating archive from files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir) / "workspace"
            workspace_dir.mkdir()
            (workspace_dir / "file1.txt").write_text("content1")
            (workspace_dir / "file2.txt").write_text("content2")

            temp_dir = Path(tmpdir) / "temp"
            temp_dir.mkdir()

            files = [
                workspace_dir / "file1.txt",
                workspace_dir / "file2.txt",
            ]

            mock_wm = MagicMock()
            mock_wm.temp_dir = temp_dir

            with patch(
                "app.services.workspace_export_service.workspace_manager",
                mock_wm,
            ):
                service = WorkspaceExportService()
                archive_path = service._create_archive(
                    workspace_dir=workspace_dir,
                    session_id="test-session",
                    files=files,
                )

            assert archive_path.exists()
            assert archive_path.suffix == ".zip"
            assert archive_path.stem == "test-session"

            # Verify archive contents
            with zipfile.ZipFile(archive_path, "r") as zf:
                names = zf.namelist()
                assert "workspace/file1.txt" in names
                assert "workspace/file2.txt" in names

    def test_create_archive_with_subdirectories(self) -> None:
        """Test creating archive with nested files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir) / "workspace"
            workspace_dir.mkdir()
            (workspace_dir / "subdir").mkdir()
            (workspace_dir / "subdir" / "nested.txt").write_text("nested content")

            temp_dir = Path(tmpdir) / "temp"
            temp_dir.mkdir()

            files = [workspace_dir / "subdir" / "nested.txt"]

            mock_wm = MagicMock()
            mock_wm.temp_dir = temp_dir

            with patch(
                "app.services.workspace_export_service.workspace_manager",
                mock_wm,
            ):
                service = WorkspaceExportService()
                archive_path = service._create_archive(
                    workspace_dir=workspace_dir,
                    session_id="test-session",
                    files=files,
                )

            with zipfile.ZipFile(archive_path, "r") as zf:
                names = zf.namelist()
                assert "workspace/subdir/nested.txt" in names


class TestExportWorkspace(unittest.TestCase):
    """Test WorkspaceExportService.export_workspace."""

    def test_export_workspace_success(self) -> None:
        """Test successful workspace export."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir) / "workspace"
            workspace_dir.mkdir()
            (workspace_dir / "file.txt").write_text("content")

            temp_dir = Path(tmpdir) / "temp"
            temp_dir.mkdir()

            mock_wm = MagicMock()
            mock_wm.resolve_user_id.return_value = "user-123"
            mock_wm.get_session_workspace_dir.return_value = workspace_dir
            mock_wm.temp_dir = temp_dir
            mock_wm._ignore_names = set()
            mock_wm.ignore_dot_files = False

            mock_storage = MagicMock()

            with (
                patch(
                    "app.services.workspace_export_service.workspace_manager",
                    mock_wm,
                ),
                patch(
                    "app.services.workspace_export_service.storage_service",
                    mock_storage,
                ),
            ):
                service = WorkspaceExportService()
                result = service.export_workspace("session-456")

            assert result.workspace_export_status == "ready"
            assert result.workspace_files_prefix is not None
            assert result.workspace_manifest_key is not None
            assert result.workspace_archive_key is not None
            assert result.error is None

            # Verify storage calls
            assert mock_storage.upload_file.called
            assert mock_storage.put_object.called

    def test_export_workspace_user_not_found(self) -> None:
        """Test export when user_id cannot be resolved."""
        mock_wm = MagicMock()
        mock_wm.resolve_user_id.return_value = None
        mock_storage = MagicMock()

        with (
            patch(
                "app.services.workspace_export_service.workspace_manager",
                mock_wm,
            ),
            patch(
                "app.services.workspace_export_service.storage_service",
                mock_storage,
            ),
        ):
            service = WorkspaceExportService()
            result = service.export_workspace("unknown-session")

        assert result.workspace_export_status == "failed"
        assert result.error is not None
        assert "Unable to resolve user_id" in result.error

    def test_export_workspace_dir_not_found(self) -> None:
        """Test export when workspace directory not found."""
        mock_wm = MagicMock()
        mock_wm.resolve_user_id.return_value = "user-123"
        mock_wm.get_session_workspace_dir.return_value = None
        mock_storage = MagicMock()

        with (
            patch(
                "app.services.workspace_export_service.workspace_manager",
                mock_wm,
            ),
            patch(
                "app.services.workspace_export_service.storage_service",
                mock_storage,
            ),
        ):
            service = WorkspaceExportService()
            result = service.export_workspace("session-456")

        assert result.workspace_export_status == "failed"
        assert result.error is not None
        assert "Workspace directory not found" in result.error

    def test_export_workspace_app_exception(self) -> None:
        """Test export handles AppException."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir) / "workspace"
            workspace_dir.mkdir()
            (workspace_dir / "file.txt").write_text("content")

            temp_dir = Path(tmpdir) / "temp"
            temp_dir.mkdir()

            mock_wm = MagicMock()
            mock_wm.resolve_user_id.return_value = "user-123"
            mock_wm.get_session_workspace_dir.return_value = workspace_dir
            mock_wm.temp_dir = temp_dir
            mock_wm._ignore_names = set()
            mock_wm.ignore_dot_files = False

            mock_storage = MagicMock()
            mock_storage.upload_file.side_effect = AppException(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="S3 upload failed",
            )

            with (
                patch(
                    "app.services.workspace_export_service.workspace_manager",
                    mock_wm,
                ),
                patch(
                    "app.services.workspace_export_service.storage_service",
                    mock_storage,
                ),
            ):
                service = WorkspaceExportService()
                result = service.export_workspace("session-456")

            assert result.workspace_export_status == "failed"
            assert result.error is not None
            assert "S3 upload failed" in result.error

    def test_export_workspace_generic_exception(self) -> None:
        """Test export handles generic exception."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir) / "workspace"
            workspace_dir.mkdir()
            (workspace_dir / "file.txt").write_text("content")

            temp_dir = Path(tmpdir) / "temp"
            temp_dir.mkdir()

            mock_wm = MagicMock()
            mock_wm.resolve_user_id.return_value = "user-123"
            mock_wm.get_session_workspace_dir.return_value = workspace_dir
            mock_wm.temp_dir = temp_dir
            mock_wm._ignore_names = set()
            mock_wm.ignore_dot_files = False

            mock_storage = MagicMock()
            mock_storage.upload_file.side_effect = Exception("Unexpected error")

            with (
                patch(
                    "app.services.workspace_export_service.workspace_manager",
                    mock_wm,
                ),
                patch(
                    "app.services.workspace_export_service.storage_service",
                    mock_storage,
                ),
            ):
                service = WorkspaceExportService()
                result = service.export_workspace("session-456")

            assert result.workspace_export_status == "failed"
            assert result.error is not None
            assert "Unexpected error" in result.error


class TestStageSkillSubmissionFolder(unittest.TestCase):
    """Test WorkspaceExportService.stage_skill_submission_folder."""

    def test_stage_skill_folder_success(self) -> None:
        """Test successful skill folder staging copies to visible location."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir) / "workspace"
            workspace_dir.mkdir()
            skill_dir = workspace_dir / "skills" / "my-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# My Skill")

            mock_wm = MagicMock()
            mock_wm.resolve_user_id.return_value = "user-123"
            mock_wm.get_session_workspace_dir.return_value = workspace_dir
            mock_wm._ignore_names = set()
            mock_wm.ignore_dot_files = False

            mock_storage = MagicMock()

            with (
                patch(
                    "app.services.workspace_export_service.workspace_manager",
                    mock_wm,
                ),
                patch(
                    "app.services.workspace_export_service.storage_service",
                    mock_storage,
                ),
            ):
                service = WorkspaceExportService()
                result = service.stage_skill_submission_folder(
                    "session-456", folder_path="skills/my-skill"
                )

            # Non-visible skill folders get copied to .config/skills/
            assert result == "/.config/skills/my-skill"

    def test_stage_skill_folder_user_not_found(self) -> None:
        """Test staging when user_id cannot be resolved."""
        mock_wm = MagicMock()
        mock_wm.resolve_user_id.return_value = None
        mock_storage = MagicMock()

        with (
            patch(
                "app.services.workspace_export_service.workspace_manager",
                mock_wm,
            ),
            patch(
                "app.services.workspace_export_service.storage_service",
                mock_storage,
            ),
        ):
            service = WorkspaceExportService()

            with self.assertRaises(AppException) as ctx:
                service.stage_skill_submission_folder(
                    "unknown-session", folder_path="skills/my-skill"
                )

        assert ctx.exception.error_code == ErrorCode.WORKSPACE_NOT_FOUND

    def test_stage_skill_folder_workspace_not_found(self) -> None:
        """Test staging when workspace not found."""
        mock_wm = MagicMock()
        mock_wm.resolve_user_id.return_value = "user-123"
        mock_wm.get_session_workspace_dir.return_value = None
        mock_storage = MagicMock()

        with (
            patch(
                "app.services.workspace_export_service.workspace_manager",
                mock_wm,
            ),
            patch(
                "app.services.workspace_export_service.storage_service",
                mock_storage,
            ),
        ):
            service = WorkspaceExportService()

            with self.assertRaises(AppException) as ctx:
                service.stage_skill_submission_folder(
                    "session-456", folder_path="skills/my-skill"
                )

        assert ctx.exception.error_code == ErrorCode.WORKSPACE_NOT_FOUND

    def test_stage_skill_folder_not_found(self) -> None:
        """Test staging when folder not found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir) / "workspace"
            workspace_dir.mkdir()

            mock_wm = MagicMock()
            mock_wm.resolve_user_id.return_value = "user-123"
            mock_wm.get_session_workspace_dir.return_value = workspace_dir

            mock_storage = MagicMock()

            with (
                patch(
                    "app.services.workspace_export_service.workspace_manager",
                    mock_wm,
                ),
                patch(
                    "app.services.workspace_export_service.storage_service",
                    mock_storage,
                ),
            ):
                service = WorkspaceExportService()

                with self.assertRaises(AppException) as ctx:
                    service.stage_skill_submission_folder(
                        "session-456", folder_path="skills/nonexistent"
                    )

            assert ctx.exception.error_code == ErrorCode.NOT_FOUND
            assert "Skill folder not found" in ctx.exception.message

    def test_stage_skill_folder_no_skill_md(self) -> None:
        """Test staging when SKILL.md missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir) / "workspace"
            workspace_dir.mkdir()
            skill_dir = workspace_dir / "skills" / "my-skill"
            skill_dir.mkdir(parents=True)
            # No SKILL.md

            mock_wm = MagicMock()
            mock_wm.resolve_user_id.return_value = "user-123"
            mock_wm.get_session_workspace_dir.return_value = workspace_dir

            mock_storage = MagicMock()

            with (
                patch(
                    "app.services.workspace_export_service.workspace_manager",
                    mock_wm,
                ),
                patch(
                    "app.services.workspace_export_service.storage_service",
                    mock_storage,
                ),
            ):
                service = WorkspaceExportService()

                with self.assertRaises(AppException) as ctx:
                    service.stage_skill_submission_folder(
                        "session-456", folder_path="skills/my-skill"
                    )

            assert ctx.exception.error_code == ErrorCode.BAD_REQUEST
            assert "SKILL.md" in ctx.exception.message

    def test_stage_skill_folder_visible_skill(self) -> None:
        """Test staging visible skill folder (no copy needed)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir) / "workspace"
            workspace_dir.mkdir()
            skill_dir = workspace_dir / ".config" / "skills" / "my-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# My Skill")

            mock_wm = MagicMock()
            mock_wm.resolve_user_id.return_value = "user-123"
            mock_wm.get_session_workspace_dir.return_value = workspace_dir
            mock_wm._ignore_names = set()
            mock_wm.ignore_dot_files = False

            mock_storage = MagicMock()

            with (
                patch(
                    "app.services.workspace_export_service.workspace_manager",
                    mock_wm,
                ),
                patch(
                    "app.services.workspace_export_service.storage_service",
                    mock_storage,
                ),
            ):
                service = WorkspaceExportService()
                result = service.stage_skill_submission_folder(
                    "session-456", folder_path=".config/skills/my-skill"
                )

            assert result == "/.config/skills/my-skill"


class TestExportWorkspaceFolder(unittest.TestCase):
    """Test WorkspaceExportService.export_workspace_folder."""

    def test_export_folder_success(self) -> None:
        """Test successful folder export."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir) / "workspace"
            workspace_dir.mkdir()
            folder_dir = workspace_dir / "skills" / "my-skill"
            folder_dir.mkdir(parents=True)
            (folder_dir / "SKILL.md").write_text("# My Skill")

            mock_wm = MagicMock()
            mock_wm.resolve_user_id.return_value = "user-123"
            mock_wm.get_session_workspace_dir.return_value = workspace_dir
            mock_wm._ignore_names = set()
            mock_wm.ignore_dot_files = False

            mock_storage = MagicMock()

            with (
                patch(
                    "app.services.workspace_export_service.workspace_manager",
                    mock_wm,
                ),
                patch(
                    "app.services.workspace_export_service.storage_service",
                    mock_storage,
                ),
            ):
                service = WorkspaceExportService()
                result = service.export_workspace_folder(
                    "session-456", folder_path="skills/my-skill"
                )

            assert result.workspace_export_status == "ready"
            assert result.workspace_files_prefix is not None
            assert result.workspace_manifest_key is not None

    def test_export_folder_user_not_found(self) -> None:
        """Test export when user_id cannot be resolved."""
        mock_wm = MagicMock()
        mock_wm.resolve_user_id.return_value = None
        mock_storage = MagicMock()

        with (
            patch(
                "app.services.workspace_export_service.workspace_manager",
                mock_wm,
            ),
            patch(
                "app.services.workspace_export_service.storage_service",
                mock_storage,
            ),
        ):
            service = WorkspaceExportService()
            result = service.export_workspace_folder(
                "unknown-session", folder_path="skills/my-skill"
            )

        assert result.workspace_export_status == "failed"
        assert result.error is not None
        assert "Unable to resolve user_id" in result.error

    def test_export_folder_dir_not_found(self) -> None:
        """Test export when workspace not found."""
        mock_wm = MagicMock()
        mock_wm.resolve_user_id.return_value = "user-123"
        mock_wm.get_session_workspace_dir.return_value = None
        mock_storage = MagicMock()

        with (
            patch(
                "app.services.workspace_export_service.workspace_manager",
                mock_wm,
            ),
            patch(
                "app.services.workspace_export_service.storage_service",
                mock_storage,
            ),
        ):
            service = WorkspaceExportService()
            result = service.export_workspace_folder(
                "session-456", folder_path="skills/my-skill"
            )

        assert result.workspace_export_status == "failed"
        assert result.error is not None
        assert "Workspace directory not found" in result.error

    def test_export_folder_not_found(self) -> None:
        """Test export when folder not found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir) / "workspace"
            workspace_dir.mkdir()

            mock_wm = MagicMock()
            mock_wm.resolve_user_id.return_value = "user-123"
            mock_wm.get_session_workspace_dir.return_value = workspace_dir

            mock_storage = MagicMock()

            with (
                patch(
                    "app.services.workspace_export_service.workspace_manager",
                    mock_wm,
                ),
                patch(
                    "app.services.workspace_export_service.storage_service",
                    mock_storage,
                ),
            ):
                service = WorkspaceExportService()
                result = service.export_workspace_folder(
                    "session-456", folder_path="skills/nonexistent"
                )

            assert result.workspace_export_status == "failed"
            assert result.error is not None
            assert "Workspace folder not found" in result.error

    def test_export_folder_empty(self) -> None:
        """Test export when folder is empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir) / "workspace"
            workspace_dir.mkdir()
            folder_dir = workspace_dir / "empty"
            folder_dir.mkdir(parents=True)

            mock_wm = MagicMock()
            mock_wm.resolve_user_id.return_value = "user-123"
            mock_wm.get_session_workspace_dir.return_value = workspace_dir

            mock_storage = MagicMock()

            with (
                patch(
                    "app.services.workspace_export_service.workspace_manager",
                    mock_wm,
                ),
                patch(
                    "app.services.workspace_export_service.storage_service",
                    mock_storage,
                ),
            ):
                service = WorkspaceExportService()
                result = service.export_workspace_folder(
                    "session-456", folder_path="empty"
                )

            assert result.workspace_export_status == "failed"
            assert result.error is not None
            assert "Workspace folder is empty" in result.error

    def test_export_folder_app_exception(self) -> None:
        """Test export handles AppException."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir) / "workspace"
            workspace_dir.mkdir()
            folder_dir = workspace_dir / "skills" / "my-skill"
            folder_dir.mkdir(parents=True)
            (folder_dir / "SKILL.md").write_text("# Skill")

            mock_wm = MagicMock()
            mock_wm.resolve_user_id.return_value = "user-123"
            mock_wm.get_session_workspace_dir.return_value = workspace_dir
            mock_wm._ignore_names = set()
            mock_wm.ignore_dot_files = False

            mock_storage = MagicMock()
            mock_storage.upload_file.side_effect = AppException(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Upload failed",
            )

            with (
                patch(
                    "app.services.workspace_export_service.workspace_manager",
                    mock_wm,
                ),
                patch(
                    "app.services.workspace_export_service.storage_service",
                    mock_storage,
                ),
            ):
                service = WorkspaceExportService()
                result = service.export_workspace_folder(
                    "session-456", folder_path="skills/my-skill"
                )

            assert result.workspace_export_status == "failed"
            assert result.error is not None
            assert "Upload failed" in result.error

    def test_export_folder_generic_exception(self) -> None:
        """Test export handles generic exception."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir) / "workspace"
            workspace_dir.mkdir()
            folder_dir = workspace_dir / "skills" / "my-skill"
            folder_dir.mkdir(parents=True)
            (folder_dir / "SKILL.md").write_text("# Skill")

            mock_wm = MagicMock()
            mock_wm.resolve_user_id.return_value = "user-123"
            mock_wm.get_session_workspace_dir.return_value = workspace_dir
            mock_wm._ignore_names = set()
            mock_wm.ignore_dot_files = False

            mock_storage = MagicMock()
            mock_storage.upload_file.side_effect = Exception("Unexpected")

            with (
                patch(
                    "app.services.workspace_export_service.workspace_manager",
                    mock_wm,
                ),
                patch(
                    "app.services.workspace_export_service.storage_service",
                    mock_storage,
                ),
            ):
                service = WorkspaceExportService()
                result = service.export_workspace_folder(
                    "session-456", folder_path="skills/my-skill"
                )

            assert result.workspace_export_status == "failed"
            assert result.error is not None
            assert "Unexpected" in result.error


class TestExportWorkspaceEdgeCases(unittest.TestCase):
    """Test edge cases for better coverage."""

    def test_export_workspace_cleanup_failure(self) -> None:
        """Test export handles archive cleanup failure gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir) / "workspace"
            workspace_dir.mkdir()
            (workspace_dir / "file.txt").write_text("content")

            temp_dir = Path(tmpdir) / "temp"
            temp_dir.mkdir()

            mock_wm = MagicMock()
            mock_wm.resolve_user_id.return_value = "user-123"
            mock_wm.get_session_workspace_dir.return_value = workspace_dir
            mock_wm.temp_dir = temp_dir
            mock_wm._ignore_names = set()
            mock_wm.ignore_dot_files = False

            mock_storage = MagicMock()

            with (
                patch(
                    "app.services.workspace_export_service.workspace_manager",
                    mock_wm,
                ),
                patch(
                    "app.services.workspace_export_service.storage_service",
                    mock_storage,
                ),
                patch.object(
                    Path, "unlink", side_effect=PermissionError("Cannot delete")
                ),
            ):
                service = WorkspaceExportService()
                result = service.export_workspace("session-456")

            # Should still succeed despite cleanup failure
            assert result.workspace_export_status == "ready"

    def test_stage_skill_folder_existing_destination(self) -> None:
        """Test staging when destination already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir) / "workspace"
            workspace_dir.mkdir()

            # Source skill folder
            skill_dir = workspace_dir / "skills" / "my-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# My Skill")

            # Existing destination (should be replaced)
            existing_dest = workspace_dir / ".config" / "skills" / "my-skill"
            existing_dest.mkdir(parents=True)
            (existing_dest / "old.md").write_text("# Old")

            mock_wm = MagicMock()
            mock_wm.resolve_user_id.return_value = "user-123"
            mock_wm.get_session_workspace_dir.return_value = workspace_dir
            mock_wm._ignore_names = set()
            mock_wm.ignore_dot_files = False

            mock_storage = MagicMock()

            with (
                patch(
                    "app.services.workspace_export_service.workspace_manager",
                    mock_wm,
                ),
                patch(
                    "app.services.workspace_export_service.storage_service",
                    mock_storage,
                ),
            ):
                service = WorkspaceExportService()
                result = service.stage_skill_submission_folder(
                    "session-456", folder_path="skills/my-skill"
                )

            # Destination should exist with new content
            assert result == "/.config/skills/my-skill"

    def test_collect_files_with_broken_symlink(self) -> None:
        """Test collecting files skips broken symlinks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir)
            (workspace_dir / "file.txt").write_text("content")
            # Create broken symlink
            (workspace_dir / "broken").symlink_to(workspace_dir / "nonexistent")

            mock_wm = MagicMock()
            mock_wm._ignore_names = set()
            mock_wm.ignore_dot_files = False

            with patch(
                "app.services.workspace_export_service.workspace_manager",
                mock_wm,
            ):
                service = WorkspaceExportService()
                result = service._collect_files(workspace_dir)

            # Only real file should be collected
            assert len(result) == 1
            assert result[0].name == "file.txt"

    def test_is_allowed_hidden_skill_path_empty_parts(self) -> None:
        """Test _is_allowed_hidden_skill_path with workspace root."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir)

            # Test workspace root itself
            result = WorkspaceExportService._is_allowed_hidden_skill_path(
                workspace_dir, workspace_dir
            )
            assert result is False


if __name__ == "__main__":
    unittest.main()
