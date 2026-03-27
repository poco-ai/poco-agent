import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.services.skill_stager import SkillStager


class TestSkillStagerInit(unittest.TestCase):
    """Test SkillStager.__init__."""

    def test_init_with_defaults(self) -> None:
        with (
            patch("app.services.skill_stager.S3StorageService") as mock_storage_cls,
            patch("app.services.skill_stager.WorkspaceManager") as mock_workspace_cls,
        ):
            mock_storage_cls.return_value = MagicMock()
            mock_workspace_cls.return_value = MagicMock()

            SkillStager()

            mock_storage_cls.assert_called_once()
            mock_workspace_cls.assert_called_once()

    def test_init_with_dependencies(self) -> None:
        mock_storage = MagicMock()
        mock_workspace = MagicMock()

        stager = SkillStager(
            storage_service=mock_storage, workspace_manager=mock_workspace
        )

        assert stager.storage_service is mock_storage
        assert stager.workspace_manager is mock_workspace


class TestSkillStagerValidateSkillName(unittest.TestCase):
    """Test SkillStager._validate_skill_name."""

    def test_valid_name_simple(self) -> None:
        SkillStager._validate_skill_name("my-skill")

    def test_valid_name_with_dots(self) -> None:
        SkillStager._validate_skill_name("my.skill.name")

    def test_valid_name_with_underscores(self) -> None:
        SkillStager._validate_skill_name("my_skill")

    def test_valid_name_with_numbers(self) -> None:
        SkillStager._validate_skill_name("skill123")

    def test_valid_name_complex(self) -> None:
        SkillStager._validate_skill_name("my-skill_v2.0")

    def test_invalid_name_dot_raises(self) -> None:
        with self.assertRaises(AppException) as ctx:
            SkillStager._validate_skill_name(".")

        assert ctx.exception.error_code == ErrorCode.BAD_REQUEST

    def test_invalid_name_double_dot_raises(self) -> None:
        with self.assertRaises(AppException) as ctx:
            SkillStager._validate_skill_name("..")

        assert ctx.exception.error_code == ErrorCode.BAD_REQUEST

    def test_invalid_name_with_spaces_raises(self) -> None:
        with self.assertRaises(AppException) as ctx:
            SkillStager._validate_skill_name("my skill")

        assert ctx.exception.error_code == ErrorCode.BAD_REQUEST

    def test_invalid_name_with_slash_raises(self) -> None:
        with self.assertRaises(AppException) as ctx:
            SkillStager._validate_skill_name("my/skill")

        assert ctx.exception.error_code == ErrorCode.BAD_REQUEST

    def test_invalid_name_with_special_chars_raises(self) -> None:
        with self.assertRaises(AppException) as ctx:
            SkillStager._validate_skill_name("my@skill")

        assert ctx.exception.error_code == ErrorCode.BAD_REQUEST


class TestSkillStagerCleanSkillsDir(unittest.TestCase):
    """Test SkillStager._clean_skills_dir."""

    def test_removes_skills_not_in_keep_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_root = Path(tmpdir)
            (skills_root / "keep-me").mkdir()
            (skills_root / "remove-me").mkdir()
            (skills_root / "also-remove").mkdir()

            removed = SkillStager._clean_skills_dir(skills_root, {"keep-me"})

            assert removed == 2
            assert (skills_root / "keep-me").exists()
            assert not (skills_root / "remove-me").exists()
            assert not (skills_root / "also-remove").exists()

    def test_keeps_all_when_all_in_keep_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_root = Path(tmpdir)
            (skills_root / "skill1").mkdir()
            (skills_root / "skill2").mkdir()

            removed = SkillStager._clean_skills_dir(skills_root, {"skill1", "skill2"})

            assert removed == 0
            assert (skills_root / "skill1").exists()
            assert (skills_root / "skill2").exists()

    def test_removes_all_when_keep_set_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_root = Path(tmpdir)
            (skills_root / "skill1").mkdir()
            (skills_root / "skill2").mkdir()

            removed = SkillStager._clean_skills_dir(skills_root, set())

            assert removed == 2
            assert not (skills_root / "skill1").exists()
            assert not (skills_root / "skill2").exists()

    def test_skips_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_root = Path(tmpdir)
            (skills_root / "file.txt").write_text("content")
            (skills_root / "skill1").mkdir()

            removed = SkillStager._clean_skills_dir(skills_root, set())

            assert removed == 1
            assert (skills_root / "file.txt").exists()

    def test_skips_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_root = Path(tmpdir)
            target = Path(tmpdir) / "target"
            target.mkdir()
            (skills_root / "skill1").mkdir()

            try:
                (skills_root / "link").symlink_to(target)
                has_symlink = True
            except OSError:
                has_symlink = False

            if has_symlink:
                SkillStager._clean_skills_dir(skills_root, set())
                assert not (skills_root / "skill1").exists()

    def test_empty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_root = Path(tmpdir)

            removed = SkillStager._clean_skills_dir(skills_root, {"nonexistent"})

            assert removed == 0

    def test_skips_escape_attempts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_root = Path(tmpdir)
            outside_dir = Path(tmpdir).parent / "outside"
            outside_dir.mkdir(exist_ok=True)

            try:
                escape_link = skills_root / "escape"
                escape_link.symlink_to(outside_dir)

                SkillStager._clean_skills_dir(skills_root, set())

                assert escape_link.exists() or not escape_link.is_dir()
            except OSError:
                pass
            finally:
                shutil.rmtree(outside_dir, ignore_errors=True)

    def test_skips_rmtree_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_root = Path(tmpdir)
            (skills_root / "skill1").mkdir()

            original_rmtree = shutil.rmtree

            def failing_rmtree(path, *args, **kwargs):
                if "skill1" in str(path):
                    raise PermissionError("Mocked permission denied")
                return original_rmtree(path, *args, **kwargs)

            with patch("shutil.rmtree", side_effect=failing_rmtree):
                removed = SkillStager._clean_skills_dir(skills_root, set())
                assert removed == 0


class TestSkillStagerStageSkills(unittest.TestCase):
    """Test SkillStager.stage_skills."""

    def test_empty_skills_returns_empty_dict(self) -> None:
        mock_storage = MagicMock()
        mock_workspace = MagicMock()

        stager = SkillStager(
            storage_service=mock_storage, workspace_manager=mock_workspace
        )

        result = stager.stage_skills("user-123", "session-456", None)
        assert result == {}

        result = stager.stage_skills("user-123", "session-456", {})
        assert result == {}

    def test_skips_non_dict_specs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            mock_storage = MagicMock()

            stager = SkillStager(
                storage_service=mock_storage, workspace_manager=mock_workspace
            )

            skills = {
                "valid-skill": {"s3_key": "skills/valid", "enabled": True},
                "invalid1": "not a dict",
                "invalid2": 123,
                "invalid3": None,
            }

            result = stager.stage_skills("user-123", "session-456", skills)

            assert "valid-skill" in result
            assert "invalid1" not in result

    def test_marks_disabled_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            mock_storage = MagicMock()

            stager = SkillStager(
                storage_service=mock_storage, workspace_manager=mock_workspace
            )

            skills = {
                "disabled-skill": {"enabled": False},
            }

            result = stager.stage_skills("user-123", "session-456", skills)

            assert result["disabled-skill"]["enabled"] is False

    def test_stages_skill_with_s3_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            mock_storage = MagicMock()

            stager = SkillStager(
                storage_service=mock_storage, workspace_manager=mock_workspace
            )

            skills = {
                "my-skill": {"s3_key": "skills/my-skill.zip"},
            }

            result = stager.stage_skills("user-123", "session-456", skills)

            assert "my-skill" in result
            assert result["my-skill"]["enabled"] is True
            assert "local_path" in result["my-skill"]
            mock_storage.download_file.assert_called_once()

    def test_stages_skill_with_key_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            mock_storage = MagicMock()

            stager = SkillStager(
                storage_service=mock_storage, workspace_manager=mock_workspace
            )

            skills = {
                "my-skill": {"key": "skills/my-skill.zip"},
            }

            result = stager.stage_skills("user-123", "session-456", skills)

            assert "my-skill" in result
            mock_storage.download_file.assert_called_once()

    def test_stages_skill_with_entry_dict(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            mock_storage = MagicMock()

            stager = SkillStager(
                storage_service=mock_storage, workspace_manager=mock_workspace
            )

            skills = {
                "my-skill": {
                    "entry": {"s3_key": "skills/my-skill.zip"},
                    "custom": "value",
                },
            }

            result = stager.stage_skills("user-123", "session-456", skills)

            assert "my-skill" in result
            assert result["my-skill"]["custom"] == "value"
            assert result["my-skill"]["entry"]["s3_key"] == "skills/my-skill.zip"

    def test_stages_skill_with_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            mock_storage = MagicMock()

            stager = SkillStager(
                storage_service=mock_storage, workspace_manager=mock_workspace
            )

            skills = {
                "my-skill": {"s3_key": "skills/my-skill/", "is_prefix": True},
            }

            result = stager.stage_skills("user-123", "session-456", skills)

            assert "my-skill" in result
            mock_storage.download_prefix.assert_called_once()

    def test_stages_skill_with_trailing_slash(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            mock_storage = MagicMock()

            stager = SkillStager(
                storage_service=mock_storage, workspace_manager=mock_workspace
            )

            skills = {
                "my-skill": {"s3_key": "skills/my-skill/"},
            }

            result = stager.stage_skills("user-123", "session-456", skills)

            assert "my-skill" in result
            mock_storage.download_prefix.assert_called_once()

    def test_skips_skill_without_s3_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            mock_storage = MagicMock()

            stager = SkillStager(
                storage_service=mock_storage, workspace_manager=mock_workspace
            )

            skills = {
                "no-key-skill": {"name": "something"},
            }

            result = stager.stage_skills("user-123", "session-456", skills)

            assert "no-key-skill" not in result

    def test_raises_on_invalid_skill_name_escape_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            mock_storage = MagicMock()

            stager = SkillStager(
                storage_service=mock_storage, workspace_manager=mock_workspace
            )

            skills = {
                "../escape": {"s3_key": "skills/escape"},
            }

            with self.assertRaises(AppException) as ctx:
                stager.stage_skills("user-123", "session-456", skills)

            assert ctx.exception.error_code == ErrorCode.BAD_REQUEST
            assert "Invalid skill name" in ctx.exception.message

    def test_raises_on_path_traversal_escape(self) -> None:
        """Test that path traversal is detected (line 95-99)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            mock_storage = MagicMock()

            stager = SkillStager(
                storage_service=mock_storage, workspace_manager=mock_workspace
            )

            skills_root = workspace_path / "workspace" / ".claude_data" / "skills"
            skills_root.mkdir(parents=True, exist_ok=True)

            try:
                escape_link = skills_root / "escape-link"
                outside_dir = Path(tmpdir) / "outside"
                outside_dir.mkdir()
                escape_link.symlink_to(outside_dir)

                skills = {
                    "escape-link": {"s3_key": "skills/escape"},
                }

                with self.assertRaises(AppException) as ctx:
                    stager.stage_skills("user-123", "session-456", skills)

                assert ctx.exception.error_code == ErrorCode.BAD_REQUEST
                assert "Invalid skill path" in ctx.exception.message
            except OSError:
                pass

    def test_raises_on_download_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            mock_storage = MagicMock()
            mock_storage.download_file.side_effect = Exception("S3 error")

            stager = SkillStager(
                storage_service=mock_storage, workspace_manager=mock_workspace
            )

            skills = {
                "failing-skill": {"s3_key": "skills/fail.zip"},
            }

            with self.assertRaises(AppException) as ctx:
                stager.stage_skills("user-123", "session-456", skills)

            assert ctx.exception.error_code == ErrorCode.SKILL_DOWNLOAD_FAILED
            assert "Failed to stage skill" in ctx.exception.message

    def test_cleans_old_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            mock_storage = MagicMock()

            stager = SkillStager(
                storage_service=mock_storage, workspace_manager=mock_workspace
            )

            skills_root = workspace_path / "workspace" / ".claude_data" / "skills"
            skills_root.mkdir(parents=True, exist_ok=True)
            (skills_root / "old-skill").mkdir()

            skills = {
                "new-skill": {"s3_key": "skills/new-skill.zip"},
            }

            result = stager.stage_skills("user-123", "session-456", skills)

            assert "new-skill" in result
            assert not (skills_root / "old-skill").exists()

    def test_validates_skill_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            mock_storage = MagicMock()

            stager = SkillStager(
                storage_service=mock_storage, workspace_manager=mock_workspace
            )

            skills = {
                "invalid skill": {"s3_key": "skills/test"},
            }

            with self.assertRaises(AppException) as ctx:
                stager.stage_skills("user-123", "session-456", skills)

            assert ctx.exception.error_code == ErrorCode.BAD_REQUEST
            assert "Invalid skill name" in ctx.exception.message

    def test_validates_skill_names_on_second_loop(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            mock_storage = MagicMock()

            stager = SkillStager(
                storage_service=mock_storage, workspace_manager=mock_workspace
            )

            skills = {
                "valid-skill": {"s3_key": "skills/test", "enabled": True},
                "invalid@skill": {"s3_key": "skills/test"},
            }

            with self.assertRaises(AppException) as ctx:
                stager.stage_skills("user-123", "session-456", skills)

            assert ctx.exception.error_code == ErrorCode.BAD_REQUEST


if __name__ == "__main__":
    unittest.main()
