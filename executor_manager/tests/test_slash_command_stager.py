import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.services.slash_command_stager import SlashCommandStager


class TestSlashCommandStagerInit(unittest.TestCase):
    """Test SlashCommandStager.__init__."""

    def test_init_with_defaults(self) -> None:
        with patch(
            "app.services.slash_command_stager.WorkspaceManager"
        ) as mock_workspace_cls:
            mock_workspace_cls.return_value = MagicMock()

            SlashCommandStager()

            mock_workspace_cls.assert_called_once()

    def test_init_with_dependencies(self) -> None:
        mock_workspace = MagicMock()

        stager = SlashCommandStager(workspace_manager=mock_workspace)

        assert stager.workspace_manager is mock_workspace


class TestSlashCommandStagerValidateCommandName(unittest.TestCase):
    """Test SlashCommandStager._validate_command_name."""

    def test_valid_name_simple(self) -> None:
        SlashCommandStager._validate_command_name("my-command")

    def test_valid_name_with_dots(self) -> None:
        SlashCommandStager._validate_command_name("my.command.name")

    def test_valid_name_with_underscores(self) -> None:
        SlashCommandStager._validate_command_name("my_command")

    def test_valid_name_with_numbers(self) -> None:
        SlashCommandStager._validate_command_name("command123")

    def test_valid_name_complex(self) -> None:
        SlashCommandStager._validate_command_name("my-command_v2.0")

    def test_invalid_name_dot_raises(self) -> None:
        with self.assertRaises(AppException) as ctx:
            SlashCommandStager._validate_command_name(".")

        assert ctx.exception.error_code == ErrorCode.BAD_REQUEST

    def test_invalid_name_double_dot_raises(self) -> None:
        with self.assertRaises(AppException) as ctx:
            SlashCommandStager._validate_command_name("..")

        assert ctx.exception.error_code == ErrorCode.BAD_REQUEST

    def test_invalid_name_with_spaces_raises(self) -> None:
        with self.assertRaises(AppException) as ctx:
            SlashCommandStager._validate_command_name("my command")

        assert ctx.exception.error_code == ErrorCode.BAD_REQUEST

    def test_invalid_name_with_slash_raises(self) -> None:
        with self.assertRaises(AppException) as ctx:
            SlashCommandStager._validate_command_name("my/command")

        assert ctx.exception.error_code == ErrorCode.BAD_REQUEST

    def test_invalid_name_with_special_chars_raises(self) -> None:
        with self.assertRaises(AppException) as ctx:
            SlashCommandStager._validate_command_name("my@command")

        assert ctx.exception.error_code == ErrorCode.BAD_REQUEST


class TestSlashCommandStagerCleanCommandsDir(unittest.TestCase):
    """Test SlashCommandStager._clean_commands_dir."""

    def test_removes_markdown_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            commands_root = Path(tmpdir)
            (commands_root / "cmd1.md").write_text("# Command 1")
            (commands_root / "cmd2.md").write_text("# Command 2")
            (commands_root / "keep.txt").write_text("not a command")

            removed = SlashCommandStager._clean_commands_dir(commands_root)

            assert removed == 2
            assert not (commands_root / "cmd1.md").exists()
            assert not (commands_root / "cmd2.md").exists()
            assert (commands_root / "keep.txt").exists()

    def test_empty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            commands_root = Path(tmpdir)

            removed = SlashCommandStager._clean_commands_dir(commands_root)

            assert removed == 0

    def test_skips_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            commands_root = Path(tmpdir)
            (commands_root / "subdir").mkdir()

            removed = SlashCommandStager._clean_commands_dir(commands_root)

            assert removed == 0
            assert (commands_root / "subdir").exists()

    def test_skips_non_markdown_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            commands_root = Path(tmpdir)
            (commands_root / "file.txt").write_text("content")
            (commands_root / "file.py").write_text("code")

            removed = SlashCommandStager._clean_commands_dir(commands_root)

            assert removed == 0
            assert (commands_root / "file.txt").exists()
            assert (commands_root / "file.py").exists()

    def test_handles_unlink_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            commands_root = Path(tmpdir)
            (commands_root / "cmd.md").write_text("# Command")

            with patch.object(
                Path, "unlink", side_effect=PermissionError("access denied")
            ):
                removed = SlashCommandStager._clean_commands_dir(commands_root)

                # Should handle the exception and return 0
                assert removed == 0


class TestSlashCommandStagerStageCommands(unittest.TestCase):
    """Test SlashCommandStager.stage_commands."""

    def test_empty_commands_returns_empty_dict(self) -> None:
        mock_workspace = MagicMock()

        stager = SlashCommandStager(workspace_manager=mock_workspace)

        result = stager.stage_commands(
            user_id="user-123", session_id="session-456", commands=None
        )
        assert result == {}

        result = stager.stage_commands(
            user_id="user-123", session_id="session-456", commands={}
        )
        assert result == {}

    def test_stages_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = SlashCommandStager(workspace_manager=mock_workspace)

            commands = {
                "test-cmd": "# Test Command\n\nThis is a test command.",
                "another": "# Another Command",
            }

            result = stager.stage_commands(
                user_id="user-123", session_id="session-456", commands=commands
            )

            assert len(result) == 2
            assert "test-cmd" in result
            assert "another" in result

            # Check files were created
            commands_root = workspace_path / "workspace" / ".claude_data" / "commands"
            assert (commands_root / "test-cmd.md").exists()
            assert (commands_root / "another.md").exists()

            # Check content
            content = (commands_root / "test-cmd.md").read_text()
            assert "Test Command" in content

    def test_skips_non_string_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = SlashCommandStager(workspace_manager=mock_workspace)

            commands = {
                "valid-cmd": "# Valid",
                "invalid1": 123,
                "invalid2": None,
                "invalid3": {"nested": "dict"},
            }

            result = stager.stage_commands(
                user_id="user-123", session_id="session-456", commands=commands
            )

            assert len(result) == 1
            assert "valid-cmd" in result
            assert "invalid1" not in result

    def test_cleans_old_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = SlashCommandStager(workspace_manager=mock_workspace)

            # Create old command
            commands_root = workspace_path / "workspace" / ".claude_data" / "commands"
            commands_root.mkdir(parents=True, exist_ok=True)
            (commands_root / "old-cmd.md").write_text("# Old Command")

            commands = {
                "new-cmd": "# New Command",
            }

            result = stager.stage_commands(
                user_id="user-123", session_id="session-456", commands=commands
            )

            assert "new-cmd" in result
            assert not (commands_root / "old-cmd.md").exists()

    def test_validates_command_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = SlashCommandStager(workspace_manager=mock_workspace)

            commands = {
                "invalid cmd": "# Invalid Command",
            }

            with self.assertRaises(AppException) as ctx:
                stager.stage_commands(
                    user_id="user-123", session_id="session-456", commands=commands
                )

            assert ctx.exception.error_code == ErrorCode.BAD_REQUEST
            assert "Invalid slash command name" in ctx.exception.message

    def test_raises_on_path_traversal_escape(self) -> None:
        """Test that path traversal is detected (line 71-75)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = SlashCommandStager(workspace_manager=mock_workspace)

            # Create commands directory with symlink
            commands_root = workspace_path / "workspace" / ".claude_data" / "commands"
            commands_root.mkdir(parents=True, exist_ok=True)

            # Create a valid name but resolve to outside path via symlink
            outside_dir = Path(tmpdir) / "outside"
            outside_dir.mkdir()

            try:
                escape_link = commands_root / "escape.md"
                escape_link.symlink_to(outside_dir / "escaped.md")

                # The code checks if commands_root_resolved is in target_file.parents
                # For a symlink, the resolved path would be outside
                commands = {
                    "escape": "# Escape Command",
                }

                # This should raise because the resolved path's parent is not commands_root
                with self.assertRaises(AppException) as ctx:
                    stager.stage_commands(
                        user_id="user-123", session_id="session-456", commands=commands
                    )

                assert ctx.exception.error_code == ErrorCode.BAD_REQUEST
                assert "Invalid slash command path" in ctx.exception.message
            except OSError:
                # Skip on systems without symlink support
                pass

    def test_raises_on_write_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = SlashCommandStager(workspace_manager=mock_workspace)

            commands = {
                "test-cmd": "# Test",
            }

            with patch.object(
                Path, "write_text", side_effect=PermissionError("access denied")
            ):
                with self.assertRaises(AppException) as ctx:
                    stager.stage_commands(
                        user_id="user-123", session_id="session-456", commands=commands
                    )

                assert ctx.exception.error_code == ErrorCode.EXTERNAL_SERVICE_ERROR
                assert "Failed to stage slash command" in ctx.exception.message

    def test_handles_unicode_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = SlashCommandStager(workspace_manager=mock_workspace)

            commands = {
                "unicode-cmd": "# Unicode 测试\n\nEmoji: 🎉",
            }

            result = stager.stage_commands(
                user_id="user-123", session_id="session-456", commands=commands
            )

            assert "unicode-cmd" in result

            commands_root = workspace_path / "workspace" / ".claude_data" / "commands"
            content = (commands_root / "unicode-cmd.md").read_text(encoding="utf-8")
            assert "测试" in content
            assert "🎉" in content


if __name__ == "__main__":
    unittest.main()
