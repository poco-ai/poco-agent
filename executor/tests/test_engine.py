import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


from app.core.engine import AgentExecutor, _temporary_env_overrides
from app.schemas.request import TaskConfig


class TestTemporaryEnvOverrides(unittest.TestCase):
    """Test _temporary_env_overrides context manager."""

    def test_sets_new_env_var(self) -> None:
        with _temporary_env_overrides({"NEW_VAR": "new_value"}):
            assert os.environ.get("NEW_VAR") == "new_value"
        assert "NEW_VAR" not in os.environ

    def test_overrides_existing_env_var(self) -> None:
        os.environ["EXISTING_VAR"] = "old_value"
        try:
            with _temporary_env_overrides({"EXISTING_VAR": "new_value"}):
                assert os.environ.get("EXISTING_VAR") == "new_value"
            assert os.environ.get("EXISTING_VAR") == "old_value"
        finally:
            del os.environ["EXISTING_VAR"]

    def test_restores_none_for_new_var(self) -> None:
        with _temporary_env_overrides({"TEMP_VAR": "temp"}):
            assert os.environ.get("TEMP_VAR") == "temp"
        assert "TEMP_VAR" not in os.environ


class TestAgentExecutorInit(unittest.TestCase):
    """Test AgentExecutor.__init__."""

    def test_init_with_defaults(self) -> None:
        with patch.object(Path, "home", return_value=Path("/home/user")):
            with patch.dict(os.environ, {"WORKSPACE_PATH": "/workspace"}):
                executor = AgentExecutor(
                    session_id="session-123",
                    hooks=[],
                )

                assert executor.session_id == "session-123"
                assert executor.sdk_session_id is None
                assert executor.run_id is None

    def test_init_with_custom_values(self) -> None:
        with patch.object(Path, "home", return_value=Path("/home/user")):
            with patch.dict(os.environ, {"WORKSPACE_PATH": "/workspace"}):
                executor = AgentExecutor(
                    session_id="session-123",
                    hooks=[],
                    sdk_session_id="sdk-session-456",
                    run_id="run-789",
                )

                assert executor.sdk_session_id == "sdk-session-456"
                assert executor.run_id == "run-789"


class TestAgentExecutorBuildInputHint(unittest.TestCase):
    """Test AgentExecutor._build_input_hint."""

    def test_no_input_files(self) -> None:
        with patch.object(Path, "home", return_value=Path("/home/user")):
            with patch.dict(os.environ, {"WORKSPACE_PATH": "/workspace"}):
                executor = AgentExecutor(session_id="session-123", hooks=[])
                config = MagicMock(spec=TaskConfig)
                config.input_files = None

                result = executor._build_input_hint(config)
                assert result is None

    def test_empty_input_files(self) -> None:
        with patch.object(Path, "home", return_value=Path("/home/user")):
            with patch.dict(os.environ, {"WORKSPACE_PATH": "/workspace"}):
                executor = AgentExecutor(session_id="session-123", hooks=[])
                config = MagicMock(spec=TaskConfig)
                config.input_files = []

                result = executor._build_input_hint(config)
                assert result is None

    def test_with_input_files(self) -> None:
        with patch.object(Path, "home", return_value=Path("/home/user")):
            with patch.dict(os.environ, {"WORKSPACE_PATH": "/workspace"}):
                executor = AgentExecutor(session_id="session-123", hooks=[])
                config = MagicMock(spec=TaskConfig)

                file1 = MagicMock()
                file1.path = "/inputs/file1.txt"
                file1.name = "file1.txt"

                file2 = MagicMock()
                file2.path = None
                file2.name = "file2.txt"

                config.input_files = [file1, file2]

                result = executor._build_input_hint(config)

                assert result is not None
                assert "inputs/" in result
                assert "file1.txt" in result
                assert "file2.txt" in result
                assert "Do not modify" in result


class TestAgentExecutorDiscoverPlugins(unittest.TestCase):
    """Test AgentExecutor._discover_plugins."""

    def test_no_plugins_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, "home", return_value=Path(tmpdir)):
                executor = AgentExecutor(session_id="session-123", hooks=[])
                executor.workspace.root_path = Path(tmpdir)

                result = executor._discover_plugins()
                assert result == []

    def test_with_valid_plugin(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, "home", return_value=Path(tmpdir)):
                executor = AgentExecutor(session_id="session-123", hooks=[])
                executor.workspace.root_path = Path(tmpdir)

                # Create a valid plugin structure
                plugin_dir = Path(tmpdir) / ".claude_data" / "plugins" / "my-plugin"
                plugin_dir.mkdir(parents=True)
                manifest_dir = plugin_dir / ".claude-plugin"
                manifest_dir.mkdir()
                (manifest_dir / "plugin.json").write_text("{}")

                result = executor._discover_plugins()
                assert len(result) == 1
                assert result[0]["type"] == "local"
                assert "my-plugin" in result[0]["path"]

    def test_with_multiple_plugins_sorted(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, "home", return_value=Path(tmpdir)):
                executor = AgentExecutor(session_id="session-123", hooks=[])
                executor.workspace.root_path = Path(tmpdir)

                plugins_dir = Path(tmpdir) / ".claude_data" / "plugins"

                # Create multiple plugins
                for name in ["zebra-plugin", "alpha-plugin", "beta-plugin"]:
                    plugin_dir = plugins_dir / name
                    plugin_dir.mkdir(parents=True)
                    manifest_dir = plugin_dir / ".claude-plugin"
                    manifest_dir.mkdir()
                    (manifest_dir / "plugin.json").write_text("{}")

                result = executor._discover_plugins()
                assert len(result) == 3
                # Verify sorted order
                paths = [p["path"] for p in result]
                names = [Path(p).name for p in paths]
                assert names == ["alpha-plugin", "beta-plugin", "zebra-plugin"]

    def test_with_invalid_plugin_no_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, "home", return_value=Path(tmpdir)):
                executor = AgentExecutor(session_id="session-123", hooks=[])
                executor.workspace.root_path = Path(tmpdir)

                # Create a plugin directory without manifest
                plugin_dir = (
                    Path(tmpdir) / ".claude_data" / "plugins" / "invalid-plugin"
                )
                plugin_dir.mkdir(parents=True)

                result = executor._discover_plugins()
                assert result == []

    def test_skips_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, "home", return_value=Path(tmpdir)):
                executor = AgentExecutor(session_id="session-123", hooks=[])
                executor.workspace.root_path = Path(tmpdir)

                plugins_dir = Path(tmpdir) / ".claude_data" / "plugins"
                plugins_dir.mkdir(parents=True)

                # Create a symlink
                symlink = plugins_dir / "symlink-plugin"
                target = Path(tmpdir) / "target"
                target.mkdir()
                symlink.symlink_to(target)

                result = executor._discover_plugins()
                assert result == []

    def test_handles_permission_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, "home", return_value=Path(tmpdir)):
                executor = AgentExecutor(session_id="session-123", hooks=[])
                executor.workspace.root_path = Path(tmpdir)

                plugins_dir = Path(tmpdir) / ".claude_data" / "plugins"
                plugins_dir.mkdir(parents=True)

                # Mock iterdir to raise exception
                with patch.object(
                    Path, "iterdir", side_effect=PermissionError("access denied")
                ):
                    result = executor._discover_plugins()
                    assert result == []

    def test_skips_files_in_plugins_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, "home", return_value=Path(tmpdir)):
                executor = AgentExecutor(session_id="session-123", hooks=[])
                executor.workspace.root_path = Path(tmpdir)

                plugins_dir = Path(tmpdir) / ".claude_data" / "plugins"
                plugins_dir.mkdir(parents=True)

                # Create a file (not a directory)
                (plugins_dir / "some-file.txt").write_text("test")

                result = executor._discover_plugins()
                assert result == []


class TestAgentExecutorInjectPlaywrightMcp(unittest.TestCase):
    """Test AgentExecutor._inject_playwright_mcp."""

    def test_injects_when_not_present(self) -> None:
        with patch.object(Path, "home", return_value=Path("/home/user")):
            with patch.dict(os.environ, {"WORKSPACE_PATH": "/workspace"}):
                executor = AgentExecutor(session_id="session-123", hooks=[])

                mcp_servers = {}
                result = executor._inject_playwright_mcp(mcp_servers)

                assert "__poco_playwright" in result
                assert result["__poco_playwright"]["command"] == "bash"

    def test_skips_when_already_present(self) -> None:
        with patch.object(Path, "home", return_value=Path("/home/user")):
            with patch.dict(os.environ, {"WORKSPACE_PATH": "/workspace"}):
                executor = AgentExecutor(session_id="session-123", hooks=[])

                mcp_servers = {"__poco_playwright": {"command": "existing"}}
                result = executor._inject_playwright_mcp(mcp_servers)

                assert result["__poco_playwright"]["command"] == "existing"

    def test_uses_env_vars(self) -> None:
        with patch.object(Path, "home", return_value=Path("/home/user")):
            with patch.dict(
                os.environ,
                {
                    "WORKSPACE_PATH": "/workspace",
                    "POCO_BROWSER_CDP_ENDPOINT": "http://custom:9999",
                    "POCO_BROWSER_VIEWPORT_SIZE": "1920x1080",
                    "PLAYWRIGHT_MCP_OUTPUT_MODE": "stdout",
                    "PLAYWRIGHT_MCP_IMAGE_RESPONSES": "allow",
                },
            ):
                executor = AgentExecutor(session_id="session-123", hooks=[])

                mcp_servers = {}
                result = executor._inject_playwright_mcp(mcp_servers)

                assert "__poco_playwright" in result
                # Verify custom values are used
                command = result["__poco_playwright"]["args"][-1]
                assert "http://custom:9999" in command
                assert "1920x1080" in command


class TestAgentExecutorInjectMemoryMcp(unittest.TestCase):
    """Test AgentExecutor._inject_memory_mcp."""

    def test_no_memory_client(self) -> None:
        with patch.object(Path, "home", return_value=Path("/home/user")):
            with patch.dict(os.environ, {"WORKSPACE_PATH": "/workspace"}):
                executor = AgentExecutor(session_id="session-123", hooks=[])
                executor.memory_mcp_server = None

                mcp_servers = {}
                result = executor._inject_memory_mcp(mcp_servers)

                assert result == {}

    def test_injects_memory_mcp(self) -> None:
        with patch.object(Path, "home", return_value=Path("/home/user")):
            with patch.dict(os.environ, {"WORKSPACE_PATH": "/workspace"}):
                executor = AgentExecutor(session_id="session-123", hooks=[])
                executor.memory_mcp_server = {"command": "test"}

                mcp_servers = {}
                result = executor._inject_memory_mcp(mcp_servers)

                from app.core.memory import MEMORY_MCP_SERVER_KEY

                assert MEMORY_MCP_SERVER_KEY in result

    def test_skips_if_already_present(self) -> None:
        with patch.object(Path, "home", return_value=Path("/home/user")):
            with patch.dict(os.environ, {"WORKSPACE_PATH": "/workspace"}):
                executor = AgentExecutor(session_id="session-123", hooks=[])
                executor.memory_mcp_server = {"command": "new"}

                from app.core.memory import MEMORY_MCP_SERVER_KEY

                mcp_servers = {MEMORY_MCP_SERVER_KEY: {"command": "existing"}}
                result = executor._inject_memory_mcp(mcp_servers)

                assert result[MEMORY_MCP_SERVER_KEY]["command"] == "existing"


if __name__ == "__main__":
    unittest.main()
