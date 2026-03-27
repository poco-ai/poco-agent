import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.services.claude_md_stager import ClaudeMdStager


class TestClaudeMdStagerInit(unittest.TestCase):
    """Test ClaudeMdStager.__init__."""

    def test_init_with_defaults(self) -> None:
        with patch(
            "app.services.claude_md_stager.WorkspaceManager"
        ) as mock_workspace_cls:
            mock_workspace_cls.return_value = MagicMock()

            ClaudeMdStager()

            mock_workspace_cls.assert_called_once()

    def test_init_with_dependencies(self) -> None:
        mock_workspace = MagicMock()

        stager = ClaudeMdStager(workspace_manager=mock_workspace)

        assert stager.workspace_manager is mock_workspace


class TestClaudeMdStagerStage(unittest.TestCase):
    """Test ClaudeMdStager.stage."""

    def test_stage_disabled_no_content(self) -> None:
        """Test staging when disabled with no content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = ClaudeMdStager(workspace_manager=mock_workspace)

            result = stager.stage(
                user_id="user-123",
                session_id="session-456",
                enabled=False,
                content="",
            )

            assert result["enabled"] is False
            assert "path" in result
            assert result["removed"] is False

    def test_stage_disabled_with_content(self) -> None:
        """Test staging when disabled but content provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = ClaudeMdStager(workspace_manager=mock_workspace)

            result = stager.stage(
                user_id="user-123",
                session_id="session-456",
                enabled=False,
                content="# Some content",
            )

            assert result["enabled"] is False

    def test_stage_enabled_with_content(self) -> None:
        """Test staging when enabled with content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = ClaudeMdStager(workspace_manager=mock_workspace)

            result = stager.stage(
                user_id="user-123",
                session_id="session-456",
                enabled=True,
                content="# Test CLAUDE.md\n\nSome instructions.",
            )

            assert result["enabled"] is True
            assert "path" in result
            assert "bytes" in result
            assert result["bytes"] > 0

            # Check file was created
            claude_root = workspace_path / "workspace" / ".claude_data"
            target_file = claude_root / "CLAUDE.md"
            assert target_file.exists()

            content = target_file.read_text()
            assert "Test CLAUDE.md" in content

    def test_stage_enabled_empty_content(self) -> None:
        """Test staging when enabled but content is empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = ClaudeMdStager(workspace_manager=mock_workspace)

            result = stager.stage(
                user_id="user-123",
                session_id="session-456",
                enabled=True,
                content="",
            )

            assert result["enabled"] is False

    def test_stage_enabled_whitespace_only_content(self) -> None:
        """Test staging when enabled but content is whitespace only."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = ClaudeMdStager(workspace_manager=mock_workspace)

            result = stager.stage(
                user_id="user-123",
                session_id="session-456",
                enabled=True,
                content="   \n\t  ",
            )

            assert result["enabled"] is False

    def test_stage_removes_existing_file_when_disabled(self) -> None:
        """Test that existing file is removed when disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = ClaudeMdStager(workspace_manager=mock_workspace)

            # Create existing file
            claude_root = workspace_path / "workspace" / ".claude_data"
            claude_root.mkdir(parents=True, exist_ok=True)
            target_file = claude_root / "CLAUDE.md"
            target_file.write_text("# Old content")

            result = stager.stage(
                user_id="user-123",
                session_id="session-456",
                enabled=False,
                content="",
            )

            assert result["enabled"] is False
            assert result["removed"] is True
            assert not target_file.exists()

    def test_stage_removes_existing_file_when_empty_content(self) -> None:
        """Test that existing file is removed when content is empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = ClaudeMdStager(workspace_manager=mock_workspace)

            # Create existing file
            claude_root = workspace_path / "workspace" / ".claude_data"
            claude_root.mkdir(parents=True, exist_ok=True)
            target_file = claude_root / "CLAUDE.md"
            target_file.write_text("# Old content")

            result = stager.stage(
                user_id="user-123",
                session_id="session-456",
                enabled=True,
                content="",
            )

            assert result["enabled"] is False
            assert result["removed"] is True
            assert not target_file.exists()

    def test_stage_no_removal_when_no_existing_file(self) -> None:
        """Test that removed is False when no existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = ClaudeMdStager(workspace_manager=mock_workspace)

            result = stager.stage(
                user_id="user-123",
                session_id="session-456",
                enabled=False,
                content="",
            )

            assert result["enabled"] is False
            assert result["removed"] is False

    def test_stage_handles_unlink_failure(self) -> None:
        """Test that unlink failure is handled gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = ClaudeMdStager(workspace_manager=mock_workspace)

            # Create existing file
            claude_root = workspace_path / "workspace" / ".claude_data"
            claude_root.mkdir(parents=True, exist_ok=True)
            target_file = claude_root / "CLAUDE.md"
            target_file.write_text("# Old content")

            with patch.object(
                Path, "unlink", side_effect=PermissionError("access denied")
            ):
                result = stager.stage(
                    user_id="user-123",
                    session_id="session-456",
                    enabled=False,
                    content="",
                )

                assert result["enabled"] is False
                assert result["removed"] is False

    def test_stage_adds_trailing_newline_if_missing(self) -> None:
        """Test that trailing newline is added if missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = ClaudeMdStager(workspace_manager=mock_workspace)

            result = stager.stage(
                user_id="user-123",
                session_id="session-456",
                enabled=True,
                content="# No trailing newline",
            )

            assert result["enabled"] is True

            claude_root = workspace_path / "workspace" / ".claude_data"
            target_file = claude_root / "CLAUDE.md"
            content = target_file.read_text()
            assert content.endswith("\n")

    def test_stage_preserves_existing_trailing_newline(self) -> None:
        """Test that existing trailing newline is preserved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = ClaudeMdStager(workspace_manager=mock_workspace)

            result = stager.stage(
                user_id="user-123",
                session_id="session-456",
                enabled=True,
                content="# With trailing newline\n",
            )

            assert result["enabled"] is True

            claude_root = workspace_path / "workspace" / ".claude_data"
            target_file = claude_root / "CLAUDE.md"
            content = target_file.read_text()
            assert content == "# With trailing newline\n"

    def test_stage_handles_non_string_content(self) -> None:
        """Test that non-string content is normalized to empty string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = ClaudeMdStager(workspace_manager=mock_workspace)

            result = stager.stage(
                user_id="user-123",
                session_id="session-456",
                enabled=True,
                content=None,  # Non-string
            )

            assert result["enabled"] is False

    def test_stage_handles_non_string_content_dict(self) -> None:
        """Test that non-string content (dict) is normalized to empty string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = ClaudeMdStager(workspace_manager=mock_workspace)

            result = stager.stage(
                user_id="user-123",
                session_id="session-456",
                enabled=True,
                content={"key": "value"},  # Non-string
            )

            assert result["enabled"] is False

    def test_stage_overwrites_existing_file(self) -> None:
        """Test that existing file is overwritten when staging new content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = ClaudeMdStager(workspace_manager=mock_workspace)

            # Stage first content
            stager.stage(
                user_id="user-123",
                session_id="session-456",
                enabled=True,
                content="# First content",
            )

            # Stage new content
            result = stager.stage(
                user_id="user-123",
                session_id="session-456",
                enabled=True,
                content="# Second content",
            )

            assert result["enabled"] is True

            claude_root = workspace_path / "workspace" / ".claude_data"
            target_file = claude_root / "CLAUDE.md"
            content = target_file.read_text()
            assert "Second content" in content
            assert "First content" not in content

    def test_stage_unicode_content(self) -> None:
        """Test that unicode content is handled correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = ClaudeMdStager(workspace_manager=mock_workspace)

            result = stager.stage(
                user_id="user-123",
                session_id="session-456",
                enabled=True,
                content="# Unicode 测试 🎉",
            )

            assert result["enabled"] is True

            claude_root = workspace_path / "workspace" / ".claude_data"
            target_file = claude_root / "CLAUDE.md"
            content = target_file.read_text(encoding="utf-8")
            assert "测试" in content
            assert "🎉" in content


if __name__ == "__main__":
    unittest.main()
