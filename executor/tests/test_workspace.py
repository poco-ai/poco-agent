import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.workspace import DEFAULT_GIT_EXCLUDES, WorkspaceManager
from app.schemas.request import TaskConfig


@pytest.mark.asyncio
class TestWorkspaceManagerAsyncMethods:
    """Test async methods of WorkspaceManager."""

    async def test_setup_session_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / "home"
            home.mkdir(parents=True)
            workspace = Path(tmpdir) / "workspace"
            workspace.mkdir()

            manager = WorkspaceManager(mount_path=str(workspace))
            manager.persistent_claude_data = workspace / ".claude_data"
            manager.system_claude_home = home / ".claude"

            await manager._setup_session_persistence()

            assert manager.persistent_claude_data.exists()
            assert manager.system_claude_home.is_symlink()

    async def test_setup_session_persistence_removes_existing_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / "home"
            home.mkdir(parents=True)
            workspace = Path(tmpdir) / "workspace"
            workspace.mkdir()

            manager = WorkspaceManager(mount_path=str(workspace))
            manager.persistent_claude_data = workspace / ".claude_data"
            manager.system_claude_home = home / ".claude"

            # Create an existing symlink
            old_target = Path(tmpdir) / "old_target"
            old_target.mkdir()
            manager.system_claude_home.symlink_to(old_target)

            await manager._setup_session_persistence()

            assert manager.system_claude_home.is_symlink()
            assert (
                manager.system_claude_home.resolve() == manager.persistent_claude_data
            )

    async def test_cleanup_removes_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / "home"
            home.mkdir(parents=True)
            workspace = Path(tmpdir) / "workspace"
            workspace.mkdir()

            manager = WorkspaceManager(mount_path=str(workspace))
            manager.system_claude_home = home / ".claude"
            manager.persistent_claude_data = workspace / ".claude_data"
            manager.persistent_claude_data.mkdir()

            # Create symlink
            manager.system_claude_home.symlink_to(manager.persistent_claude_data)

            await manager.cleanup()

            assert not manager.system_claude_home.exists()

    async def test_cleanup_with_askpass_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            askpass_file = Path(tmpdir) / "askpass.sh"
            askpass_file.write_text("#!/bin/sh\necho test")

            workspace = Path(tmpdir) / "workspace"
            workspace.mkdir()
            home = Path(tmpdir) / "home"
            home.mkdir()

            manager = WorkspaceManager(mount_path=str(workspace))
            manager.system_claude_home = home / ".claude"
            manager._git_askpass_path = str(askpass_file)

            await manager.cleanup()

            assert not askpass_file.exists()
            assert manager._git_askpass_path is None

    async def test_prepare_creates_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / "home"
            home.mkdir(parents=True)
            workspace_path = Path(tmpdir) / "workspace"

            manager = WorkspaceManager(mount_path=str(workspace_path))
            manager.persistent_claude_data = workspace_path / ".claude_data"
            manager.system_claude_home = home / ".claude"

            config = MagicMock(spec=TaskConfig)
            config.repo_url = None
            config.git_branch = None
            config.git_token = None

            with patch.object(manager, "_ensure_git_repo"):
                await manager.prepare(config)

                assert workspace_path.exists()
                assert manager.inputs_root.exists()

    async def test_ensure_inputs_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)

            manager = WorkspaceManager(mount_path=str(workspace_path))

            manager._ensure_inputs_dir(workspace_path)

            assert manager.inputs_root.exists()

    async def test_ensure_inputs_dir_with_subpath(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            repo_path = workspace_path / "repo"
            repo_path.mkdir()

            manager = WorkspaceManager(mount_path=str(workspace_path))
            manager.inputs_root.mkdir()

            manager._ensure_inputs_dir(repo_path)

            # Should create symlink in repo_path
            assert (repo_path / "inputs").is_symlink()


class TestWorkspaceManagerInit(unittest.TestCase):
    """Test WorkspaceManager.__init__."""

    def test_init_default_path(self) -> None:
        with patch.dict(os.environ, {"WORKSPACE_PATH": "/workspace"}):
            with patch.object(Path, "home", return_value=Path("/home/user")):
                manager = WorkspaceManager()
                assert manager.root_path == Path("/workspace")
                assert manager.work_path == Path("/workspace")

    def test_init_custom_path(self) -> None:
        with patch.object(Path, "home", return_value=Path("/home/user")):
            manager = WorkspaceManager(mount_path="/custom/workspace")
            assert manager.root_path == Path("/custom/workspace")


class TestWorkspaceManagerDeriveRepoPath(unittest.TestCase):
    """Test WorkspaceManager._derive_repo_path."""

    def test_derive_simple_url(self) -> None:
        manager = WorkspaceManager(mount_path="/workspace")
        result = manager._derive_repo_path("https://github.com/owner/repo")
        assert result == Path("/workspace/repo")

    def test_derive_url_with_git_suffix(self) -> None:
        manager = WorkspaceManager(mount_path="/workspace")
        result = manager._derive_repo_path("https://github.com/owner/repo.git")
        assert result == Path("/workspace/repo")

    def test_derive_url_with_query(self) -> None:
        manager = WorkspaceManager(mount_path="/workspace")
        result = manager._derive_repo_path("https://github.com/owner/repo?foo=bar")
        assert result == Path("/workspace/repo")

    def test_derive_url_with_fragment(self) -> None:
        manager = WorkspaceManager(mount_path="/workspace")
        result = manager._derive_repo_path("https://github.com/owner/repo#main")
        assert result == Path("/workspace/repo")

    def test_derive_empty_url(self) -> None:
        manager = WorkspaceManager(mount_path="/workspace")
        result = manager._derive_repo_path("")
        assert result == Path("/workspace/repo")


class TestWorkspaceManagerEnsureGitRepo(unittest.TestCase):
    """Test WorkspaceManager._ensure_git_repo."""

    def test_existing_repo(self) -> None:
        with patch(
            "app.core.workspace.is_repository", return_value=True
        ) as mock_is_repo:
            WorkspaceManager._ensure_git_repo(Path("/workspace"))
            mock_is_repo.assert_called_once_with(Path("/workspace"))

    def test_init_new_repo(self) -> None:
        with patch("app.core.workspace.is_repository", return_value=False):
            with patch("app.core.workspace.init_repository") as mock_init:
                WorkspaceManager._ensure_git_repo(Path("/workspace"))
                mock_init.assert_called_once_with(Path("/workspace"))

    def test_init_fails_silently(self) -> None:
        with patch("app.core.workspace.is_repository", return_value=False):
            with patch(
                "app.core.workspace.init_repository", side_effect=Exception("fail")
            ):
                # Should not raise
                WorkspaceManager._ensure_git_repo(Path("/workspace"))


class TestWorkspaceManagerBuildGitEnv(unittest.TestCase):
    """Test WorkspaceManager._build_git_env."""

    def test_no_token(self) -> None:
        manager = WorkspaceManager(mount_path="/workspace")
        result = manager._build_git_env("https://github.com/owner/repo", None)
        assert result == {"GIT_TERMINAL_PROMPT": "0"}

    def test_token_with_github_url(self) -> None:
        manager = WorkspaceManager(mount_path="/workspace")
        with patch.object(manager, "_ensure_git_askpass", return_value="/tmp/askpass"):
            result = manager._build_git_env("https://github.com/owner/repo", "mytoken")
            assert "GIT_ASKPASS" in result
            assert result["GIT_ASKPASS"] == "/tmp/askpass"
            assert result["POCO_GIT_TOKEN"] == "mytoken"

    def test_token_with_non_github_url(self) -> None:
        manager = WorkspaceManager(mount_path="/workspace")
        result = manager._build_git_env("https://gitlab.com/owner/repo", "mytoken")
        assert result == {"GIT_TERMINAL_PROMPT": "0"}

    def test_token_with_invalid_url(self) -> None:
        manager = WorkspaceManager(mount_path="/workspace")
        result = manager._build_git_env("not-a-url", "mytoken")
        assert result == {"GIT_TERMINAL_PROMPT": "0"}


class TestWorkspaceManagerEnsureGitAskpass(unittest.TestCase):
    """Test WorkspaceManager._ensure_git_askpass."""

    def test_creates_askpass_script(self) -> None:
        manager = WorkspaceManager(mount_path="/workspace")
        with tempfile.TemporaryDirectory() as tmpdir:
            # Patch the home directory to avoid polluting the real one
            with patch.object(Path, "home", return_value=Path(tmpdir)):
                path = manager._ensure_git_askpass()
                assert Path(path).exists()
                # Check that the script content is correct
                content = Path(path).read_text()
                assert "POCO_GIT_USERNAME" in content
                assert "POCO_GIT_TOKEN" in content

    def test_reuses_existing_script(self) -> None:
        manager = WorkspaceManager(mount_path="/workspace")
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, "home", return_value=Path(tmpdir)):
                path1 = manager._ensure_git_askpass()
                path2 = manager._ensure_git_askpass()
                assert path1 == path2


class TestWorkspaceManagerEnsureGitExcludes(unittest.TestCase):
    """Test WorkspaceManager._ensure_git_excludes."""

    def test_not_a_repo(self) -> None:
        with patch("app.core.workspace.is_repository", return_value=False):
            manager = WorkspaceManager(mount_path="/workspace")
            # Should not raise
            manager._ensure_git_excludes(Path("/workspace"))

    def test_creates_excludes_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            git_dir = repo_path / ".git"
            git_dir.mkdir()
            (git_dir / "info").mkdir()

            with patch("app.core.workspace.is_repository", return_value=True):
                manager = WorkspaceManager(mount_path=tmpdir)
                manager._ensure_git_excludes(repo_path)

                exclude_file = git_dir / "info" / "exclude"
                assert exclude_file.exists()
                content = exclude_file.read_text()
                for pattern in DEFAULT_GIT_EXCLUDES:
                    assert pattern in content

    def test_appends_to_existing_excludes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            git_dir = repo_path / ".git"
            info_dir = git_dir / "info"
            info_dir.mkdir(parents=True)

            exclude_file = info_dir / "exclude"
            exclude_file.write_text("existing_pattern\n")

            with patch("app.core.workspace.is_repository", return_value=True):
                manager = WorkspaceManager(mount_path=tmpdir)
                manager._ensure_git_excludes(repo_path)

                content = exclude_file.read_text()
                assert "existing_pattern" in content
                assert ".git/" in content


class TestWorkspaceManagerPrepareRepository(unittest.TestCase):
    """Test WorkspaceManager._prepare_repository."""

    def test_no_repo_url(self) -> None:
        manager = WorkspaceManager(mount_path="/workspace")
        config = MagicMock(spec=TaskConfig)
        config.repo_url = None
        config.git_branch = None
        config.git_token = None

        with patch.object(manager, "_ensure_git_repo") as mock_ensure:
            result = manager._prepare_repository(config)
            assert result == Path("/workspace")
            mock_ensure.assert_called_once()

    def test_with_repo_url(self) -> None:
        manager = WorkspaceManager(mount_path="/workspace")
        config = MagicMock(spec=TaskConfig)
        config.repo_url = "https://github.com/owner/repo"
        config.git_branch = "main"
        config.git_token = None

        with patch.object(
            manager,
            "_ensure_cloned_repo",
            return_value=Path("/workspace/repo"),
        ) as mock_clone:
            result = manager._prepare_repository(config)
            assert result == Path("/workspace/repo")
            mock_clone.assert_called_once()


class TestDefaultGitExcludes(unittest.TestCase):
    """Test DEFAULT_GIT_EXCLUDES constant."""

    def test_contains_common_patterns(self) -> None:
        assert ".git/" in DEFAULT_GIT_EXCLUDES
        assert "node_modules/" in DEFAULT_GIT_EXCLUDES
        assert "__pycache__/" in DEFAULT_GIT_EXCLUDES
        assert ".venv/" in DEFAULT_GIT_EXCLUDES


class TestWorkspaceManagerEnsureClonedRepo(unittest.TestCase):
    """Test WorkspaceManager._ensure_cloned_repo."""

    def test_existing_repo_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WorkspaceManager(mount_path=tmpdir)

            with patch("app.core.workspace.is_repository", return_value=True):
                with patch.object(manager, "_checkout_branch") as mock_checkout:
                    repo_path = Path(tmpdir) / "repo"
                    repo_path.mkdir()

                    manager._ensure_cloned_repo(
                        "https://github.com/owner/repo",
                        "main",
                        git_token=None,
                    )

                    mock_checkout.assert_called_once()

    def test_path_exists_not_repo_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WorkspaceManager(mount_path=tmpdir)
            repo_path = Path(tmpdir) / "repo"
            repo_path.mkdir()

            with patch("app.core.workspace.is_repository", return_value=False):
                with pytest.raises(RuntimeError, match="not a git repository"):
                    manager._ensure_cloned_repo(
                        "https://github.com/owner/repo",
                        None,
                        git_token=None,
                    )

    def test_clone_repo_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WorkspaceManager(mount_path=tmpdir)

            with patch("app.core.workspace.is_repository", return_value=False):
                with patch("app.core.workspace.clone") as mock_clone:
                    mock_clone.return_value = Path(tmpdir) / "repo"

                    manager._ensure_cloned_repo(
                        "https://github.com/owner/repo",
                        "main",
                        git_token=None,
                    )

                    mock_clone.assert_called_once()

    def test_clone_repo_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WorkspaceManager(mount_path=tmpdir)

            with patch("app.core.workspace.is_repository", return_value=False):
                from app.utils.git.operations import GitCommandError

                with patch(
                    "app.core.workspace.clone",
                    side_effect=GitCommandError("clone failed", 1),
                ):
                    with pytest.raises(RuntimeError, match="Failed to clone"):
                        manager._ensure_cloned_repo(
                            "https://github.com/owner/repo",
                            None,
                            git_token=None,
                        )


class TestWorkspaceManagerCheckoutBranch(unittest.TestCase):
    """Test WorkspaceManager._checkout_branch."""

    def test_no_branch_skips(self) -> None:
        WorkspaceManager._checkout_branch(Path("/workspace"), None)
        # Should not raise

    def test_checkout_success(self) -> None:
        with patch("app.core.workspace.fetch") as mock_fetch:
            with patch("app.core.workspace.checkout") as mock_checkout:
                WorkspaceManager._checkout_branch(
                    Path("/workspace"), "main", env={"FOO": "bar"}
                )
                mock_fetch.assert_called_once()
                mock_checkout.assert_called_once()

    def test_checkout_fails(self) -> None:
        from app.utils.git.operations import GitCommandError

        with patch(
            "app.core.workspace.fetch",
            side_effect=GitCommandError("fetch failed", 1),
        ):
            with pytest.raises(RuntimeError, match="Failed to checkout"):
                WorkspaceManager._checkout_branch(Path("/workspace"), "main")


class TestWorkspaceManagerEnsureGitExcludesExtra(unittest.TestCase):
    """Test WorkspaceManager._ensure_git_excludes with extra patterns."""

    def test_with_env_extra_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            git_dir = repo_path / ".git"
            info_dir = git_dir / "info"
            info_dir.mkdir(parents=True)

            with patch("app.core.workspace.is_repository", return_value=True):
                with patch.dict(
                    os.environ,
                    {"WORKSPACE_GIT_IGNORE": "custom_pattern,another_pattern"},
                ):
                    manager = WorkspaceManager(mount_path=tmpdir)
                    manager._ensure_git_excludes(repo_path)

                    content = (info_dir / "exclude").read_text()
                    assert "custom_pattern" in content
                    assert "another_pattern" in content

    def test_failed_read_existing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            git_dir = repo_path / ".git"
            info_dir = git_dir / "info"
            info_dir.mkdir(parents=True)

            exclude_file = info_dir / "exclude"
            exclude_file.write_text("existing")

            with patch("app.core.workspace.is_repository", return_value=True):
                # Simulate read failure
                with patch.object(
                    Path,
                    "read_text",
                    side_effect=PermissionError("cannot read"),
                ):
                    manager = WorkspaceManager(mount_path=tmpdir)
                    # Should not raise, just log warning
                    manager._ensure_git_excludes(repo_path)

    def test_failed_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            git_dir = repo_path / ".git"
            info_dir = git_dir / "info"
            info_dir.mkdir(parents=True)

            with patch("app.core.workspace.is_repository", return_value=True):
                with patch.object(
                    Path,
                    "write_text",
                    side_effect=PermissionError("cannot write"),
                ):
                    manager = WorkspaceManager(mount_path=tmpdir)
                    # Should not raise, just log warning
                    manager._ensure_git_excludes(repo_path)


if __name__ == "__main__":
    unittest.main()
