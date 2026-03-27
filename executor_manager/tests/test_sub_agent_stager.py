import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.services.sub_agent_stager import SubAgentStager


class TestSubAgentStagerInit(unittest.TestCase):
    """Test SubAgentStager.__init__."""

    def test_init_with_defaults(self) -> None:
        with patch(
            "app.services.sub_agent_stager.WorkspaceManager"
        ) as mock_workspace_cls:
            mock_workspace_cls.return_value = MagicMock()

            SubAgentStager()

            mock_workspace_cls.assert_called_once()

    def test_init_with_dependencies(self) -> None:
        mock_workspace = MagicMock()

        stager = SubAgentStager(workspace_manager=mock_workspace)

        assert stager.workspace_manager is mock_workspace


class TestSubAgentStagerValidateSubagentName(unittest.TestCase):
    """Test SubAgentStager._validate_subagent_name."""

    def test_valid_name_simple(self) -> None:
        SubAgentStager._validate_subagent_name("my-agent")

    def test_valid_name_with_dots(self) -> None:
        SubAgentStager._validate_subagent_name("my.agent.name")

    def test_valid_name_with_underscores(self) -> None:
        SubAgentStager._validate_subagent_name("my_agent")

    def test_valid_name_with_numbers(self) -> None:
        SubAgentStager._validate_subagent_name("agent123")

    def test_valid_name_complex(self) -> None:
        SubAgentStager._validate_subagent_name("my-agent_v2.0")

    def test_invalid_name_dot_raises(self) -> None:
        with self.assertRaises(AppException) as ctx:
            SubAgentStager._validate_subagent_name(".")

        assert ctx.exception.error_code == ErrorCode.BAD_REQUEST

    def test_invalid_name_double_dot_raises(self) -> None:
        with self.assertRaises(AppException) as ctx:
            SubAgentStager._validate_subagent_name("..")

        assert ctx.exception.error_code == ErrorCode.BAD_REQUEST

    def test_invalid_name_with_spaces_raises(self) -> None:
        with self.assertRaises(AppException) as ctx:
            SubAgentStager._validate_subagent_name("my agent")

        assert ctx.exception.error_code == ErrorCode.BAD_REQUEST

    def test_invalid_name_with_slash_raises(self) -> None:
        with self.assertRaises(AppException) as ctx:
            SubAgentStager._validate_subagent_name("my/agent")

        assert ctx.exception.error_code == ErrorCode.BAD_REQUEST

    def test_invalid_name_with_special_chars_raises(self) -> None:
        with self.assertRaises(AppException) as ctx:
            SubAgentStager._validate_subagent_name("my@agent")

        assert ctx.exception.error_code == ErrorCode.BAD_REQUEST


class TestSubAgentStagerCleanAgentsDir(unittest.TestCase):
    """Test SubAgentStager._clean_agents_dir."""

    def test_removes_markdown_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_root = Path(tmpdir)
            (agents_root / "agent1.md").write_text("# Agent 1")
            (agents_root / "agent2.md").write_text("# Agent 2")
            (agents_root / "keep.txt").write_text("not an agent")

            removed = SubAgentStager._clean_agents_dir(agents_root)

            assert removed == 2
            assert not (agents_root / "agent1.md").exists()
            assert not (agents_root / "agent2.md").exists()
            assert (agents_root / "keep.txt").exists()

    def test_empty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_root = Path(tmpdir)

            removed = SubAgentStager._clean_agents_dir(agents_root)

            assert removed == 0

    def test_skips_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_root = Path(tmpdir)
            (agents_root / "subdir").mkdir()

            removed = SubAgentStager._clean_agents_dir(agents_root)

            assert removed == 0
            assert (agents_root / "subdir").exists()

    def test_skips_non_markdown_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_root = Path(tmpdir)
            (agents_root / "file.txt").write_text("content")
            (agents_root / "file.py").write_text("code")

            removed = SubAgentStager._clean_agents_dir(agents_root)

            assert removed == 0
            assert (agents_root / "file.txt").exists()
            assert (agents_root / "file.py").exists()

    def test_handles_unlink_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_root = Path(tmpdir)
            (agents_root / "agent.md").write_text("# Agent")

            with patch.object(
                Path, "unlink", side_effect=PermissionError("access denied")
            ):
                removed = SubAgentStager._clean_agents_dir(agents_root)

                assert removed == 0


class TestSubAgentStagerStageRawAgents(unittest.TestCase):
    """Test SubAgentStager.stage_raw_agents."""

    def test_empty_raw_agents_returns_empty_dict(self) -> None:
        mock_workspace = MagicMock()

        stager = SubAgentStager(workspace_manager=mock_workspace)

        result = stager.stage_raw_agents(
            user_id="user-123", session_id="session-456", raw_agents=None
        )
        assert result == {}

        result = stager.stage_raw_agents(
            user_id="user-123", session_id="session-456", raw_agents={}
        )
        assert result == {}

    def test_stages_raw_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = SubAgentStager(workspace_manager=mock_workspace)

            raw_agents = {
                "test-agent": "# Test Agent\n\nThis is a test agent.",
                "another": "# Another Agent",
            }

            result = stager.stage_raw_agents(
                user_id="user-123", session_id="session-456", raw_agents=raw_agents
            )

            assert len(result) == 2
            assert "test-agent" in result
            assert "another" in result

            # Check files were created
            agents_root = workspace_path / "workspace" / ".claude_data" / "agents"
            assert (agents_root / "test-agent.md").exists()
            assert (agents_root / "another.md").exists()

            # Check content
            content = (agents_root / "test-agent.md").read_text()
            assert "Test Agent" in content

    def test_skips_non_string_raw_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = SubAgentStager(workspace_manager=mock_workspace)

            raw_agents = {
                "valid-agent": "# Valid",
                "invalid1": 123,
                "invalid2": None,
                "invalid3": {"nested": "dict"},
            }

            result = stager.stage_raw_agents(
                user_id="user-123", session_id="session-456", raw_agents=raw_agents
            )

            assert len(result) == 1
            assert "valid-agent" in result
            assert "invalid1" not in result

    def test_cleans_old_raw_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = SubAgentStager(workspace_manager=mock_workspace)

            # Create old agent
            agents_root = workspace_path / "workspace" / ".claude_data" / "agents"
            agents_root.mkdir(parents=True, exist_ok=True)
            (agents_root / "old-agent.md").write_text("# Old Agent")

            raw_agents = {
                "new-agent": "# New Agent",
            }

            result = stager.stage_raw_agents(
                user_id="user-123", session_id="session-456", raw_agents=raw_agents
            )

            assert "new-agent" in result
            assert not (agents_root / "old-agent.md").exists()

    def test_validates_subagent_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = SubAgentStager(workspace_manager=mock_workspace)

            raw_agents = {
                "invalid agent": "# Invalid Agent",
            }

            with self.assertRaises(AppException) as ctx:
                stager.stage_raw_agents(
                    user_id="user-123", session_id="session-456", raw_agents=raw_agents
                )

            assert ctx.exception.error_code == ErrorCode.BAD_REQUEST
            assert "Invalid subagent name" in ctx.exception.message

    def test_raises_on_path_traversal_escape(self) -> None:
        """Test that path traversal is detected (line 71-75)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = SubAgentStager(workspace_manager=mock_workspace)

            agents_root = workspace_path / "workspace" / ".claude_data" / "agents"
            agents_root.mkdir(parents=True, exist_ok=True)

            outside_dir = Path(tmpdir) / "outside"
            outside_dir.mkdir()

            try:
                escape_link = agents_root / "escape.md"
                escape_link.symlink_to(outside_dir / "escaped.md")

                raw_agents = {
                    "escape": "# Escape Agent",
                }

                with self.assertRaises(AppException) as ctx:
                    stager.stage_raw_agents(
                        user_id="user-123",
                        session_id="session-456",
                        raw_agents=raw_agents,
                    )

                assert ctx.exception.error_code == ErrorCode.BAD_REQUEST
                assert "Invalid subagent path" in ctx.exception.message
            except OSError:
                pass

    def test_raises_on_write_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = SubAgentStager(workspace_manager=mock_workspace)

            raw_agents = {
                "test-agent": "# Test",
            }

            with patch.object(
                Path, "write_text", side_effect=PermissionError("access denied")
            ):
                with self.assertRaises(AppException) as ctx:
                    stager.stage_raw_agents(
                        user_id="user-123",
                        session_id="session-456",
                        raw_agents=raw_agents,
                    )

                assert ctx.exception.error_code == ErrorCode.EXTERNAL_SERVICE_ERROR
                assert "Failed to stage subagent" in ctx.exception.message

    def test_handles_unicode_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = SubAgentStager(workspace_manager=mock_workspace)

            raw_agents = {
                "unicode-agent": "# Unicode 测试\n\nEmoji: 🎉",
            }

            result = stager.stage_raw_agents(
                user_id="user-123", session_id="session-456", raw_agents=raw_agents
            )

            assert "unicode-agent" in result

            agents_root = workspace_path / "workspace" / ".claude_data" / "agents"
            content = (agents_root / "unicode-agent.md").read_text(encoding="utf-8")
            assert "测试" in content
            assert "🎉" in content

    def test_adds_trailing_newline_if_missing(self) -> None:
        """Test that trailing newline is added if missing (lines 78-79)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = SubAgentStager(workspace_manager=mock_workspace)

            raw_agents = {
                "no-newline": "# No Newline",  # No trailing newline
            }

            stager.stage_raw_agents(
                user_id="user-123", session_id="session-456", raw_agents=raw_agents
            )

            agents_root = workspace_path / "workspace" / ".claude_data" / "agents"
            content = (agents_root / "no-newline.md").read_text()
            assert content.endswith("\n")

    def test_preserves_existing_trailing_newline(self) -> None:
        """Test that existing trailing newline is preserved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = SubAgentStager(workspace_manager=mock_workspace)

            raw_agents = {
                "with-newline": "# With Newline\n",  # Has trailing newline
            }

            stager.stage_raw_agents(
                user_id="user-123", session_id="session-456", raw_agents=raw_agents
            )

            agents_root = workspace_path / "workspace" / ".claude_data" / "agents"
            content = (agents_root / "with-newline.md").read_text()
            assert content == "# With Newline\n"

    def test_empty_markdown_is_written(self) -> None:
        """Test that empty markdown string is handled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            stager = SubAgentStager(workspace_manager=mock_workspace)

            raw_agents = {
                "empty": "",  # Empty string
            }

            result = stager.stage_raw_agents(
                user_id="user-123", session_id="session-456", raw_agents=raw_agents
            )

            assert "empty" in result

            agents_root = workspace_path / "workspace" / ".claude_data" / "agents"
            content = (agents_root / "empty.md").read_text()
            # Empty string, no newline added (line 78: if text and ...)
            assert content == ""


if __name__ == "__main__":
    unittest.main()
