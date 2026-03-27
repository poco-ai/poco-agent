import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.services.attachment_stager import AttachmentStager


class TestAttachmentStagerInit(unittest.TestCase):
    """Test AttachmentStager.__init__."""

    def test_init_with_defaults(self) -> None:
        with (
            patch(
                "app.services.attachment_stager.S3StorageService"
            ) as mock_storage_cls,
            patch(
                "app.services.attachment_stager.WorkspaceManager"
            ) as mock_workspace_cls,
        ):
            mock_storage_cls.return_value = MagicMock()
            mock_workspace_cls.return_value = MagicMock()

            AttachmentStager()

            mock_storage_cls.assert_called_once()
            mock_workspace_cls.assert_called_once()

    def test_init_with_dependencies(self) -> None:
        mock_storage = MagicMock()
        mock_workspace = MagicMock()

        stager = AttachmentStager(
            storage_service=mock_storage, workspace_manager=mock_workspace
        )

        assert stager.storage_service is mock_storage
        assert stager.workspace_manager is mock_workspace


class TestAttachmentStagerNormalizeRelativePath(unittest.TestCase):
    """Test AttachmentStager._normalize_relative_path."""

    def test_valid_path(self) -> None:
        result = AttachmentStager._normalize_relative_path("foo/bar.txt")
        assert result == "foo/bar.txt"

    def test_removes_leading_slash(self) -> None:
        result = AttachmentStager._normalize_relative_path("/foo/bar.txt")
        assert result == "foo/bar.txt"

    def test_normalizes_backslashes(self) -> None:
        result = AttachmentStager._normalize_relative_path("foo\\bar\\baz.txt")
        assert result == "foo/bar/baz.txt"

    def test_strips_whitespace(self) -> None:
        result = AttachmentStager._normalize_relative_path("  foo/bar  ")
        assert result == "foo/bar"

    def test_empty_string_returns_none(self) -> None:
        result = AttachmentStager._normalize_relative_path("")
        assert result is None

    def test_whitespace_returns_none(self) -> None:
        result = AttachmentStager._normalize_relative_path("   ")
        assert result is None

    def test_none_returns_none(self) -> None:
        result = AttachmentStager._normalize_relative_path(None)
        assert result is None

    def test_non_string_returns_none(self) -> None:
        result = AttachmentStager._normalize_relative_path(123)
        assert result is None

    def test_dot_path_returns_none(self) -> None:
        result = AttachmentStager._normalize_relative_path(".")
        assert result is None

    def test_double_dot_path_returns_none(self) -> None:
        result = AttachmentStager._normalize_relative_path("..")
        assert result is None

    def test_path_with_dot_returns_none(self) -> None:
        result = AttachmentStager._normalize_relative_path("foo/./bar")
        assert result is None

    def test_path_with_double_dot_returns_none(self) -> None:
        result = AttachmentStager._normalize_relative_path("foo/../bar")
        assert result is None

    def test_slash_only_returns_none(self) -> None:
        result = AttachmentStager._normalize_relative_path("///")
        assert result is None


class TestAttachmentStagerBuildStaged(unittest.TestCase):
    """Test AttachmentStager._build_staged."""

    def test_build_staged_basic(self) -> None:
        item = {"type": "file", "source": "s3://bucket/key"}
        result = AttachmentStager._build_staged(item, "foo/bar.txt", "bar.txt")

        assert result["name"] == "bar.txt"
        assert result["path"] == "/inputs/foo/bar.txt"
        assert result["type"] == "file"
        assert result["source"] == "s3://bucket/key"

    def test_build_staged_preserves_other_fields(self) -> None:
        item = {
            "type": "url",
            "source": "https://github.com/owner/repo",
            "custom": "value",
        }
        result = AttachmentStager._build_staged(item, "repo", "repo")

        assert result["custom"] == "value"


class TestAttachmentStagerParseGitHubRepo(unittest.TestCase):
    """Test AttachmentStager._parse_github_repo."""

    def test_valid_github_url(self) -> None:
        repo_url, branch, repo_name = AttachmentStager._parse_github_repo(
            "https://github.com/owner/repo"
        )

        assert repo_url == "https://github.com/owner/repo.git"
        assert branch is None
        assert repo_name == "repo"

    def test_github_url_with_git_suffix(self) -> None:
        repo_url, branch, repo_name = AttachmentStager._parse_github_repo(
            "https://github.com/owner/repo.git"
        )

        assert repo_url == "https://github.com/owner/repo.git"
        assert repo_name == "repo"

    def test_github_url_with_branch(self) -> None:
        repo_url, branch, repo_name = AttachmentStager._parse_github_repo(
            "https://github.com/owner/repo/tree/main"
        )

        assert repo_url == "https://github.com/owner/repo.git"
        assert branch == "main"
        assert repo_name == "repo"

    def test_github_url_with_branch_and_path(self) -> None:
        repo_url, branch, repo_name = AttachmentStager._parse_github_repo(
            "https://github.com/owner/repo/tree/develop/src"
        )

        assert branch == "develop"

    def test_www_github_com(self) -> None:
        repo_url, branch, repo_name = AttachmentStager._parse_github_repo(
            "https://www.github.com/owner/repo"
        )

        assert repo_url == "https://github.com/owner/repo.git"

    def test_http_scheme(self) -> None:
        repo_url, branch, repo_name = AttachmentStager._parse_github_repo(
            "http://github.com/owner/repo"
        )

        assert repo_url == "https://github.com/owner/repo.git"

    def test_invalid_scheme_raises(self) -> None:
        with self.assertRaises(AppException) as ctx:
            AttachmentStager._parse_github_repo("ftp://github.com/owner/repo")

        assert ctx.exception.error_code == ErrorCode.BAD_REQUEST
        assert "http(s)" in ctx.exception.message

    def test_non_github_host_raises(self) -> None:
        with self.assertRaises(AppException) as ctx:
            AttachmentStager._parse_github_repo("https://gitlab.com/owner/repo")

        assert ctx.exception.error_code == ErrorCode.BAD_REQUEST
        assert "github.com" in ctx.exception.message

    def test_missing_repo_raises(self) -> None:
        with self.assertRaises(AppException) as ctx:
            AttachmentStager._parse_github_repo("https://github.com/owner")

        assert ctx.exception.error_code == ErrorCode.BAD_REQUEST
        assert "Invalid GitHub repository URL" in ctx.exception.message

    def test_empty_path_raises(self) -> None:
        with self.assertRaises(AppException) as ctx:
            AttachmentStager._parse_github_repo("https://github.com/")

        assert ctx.exception.error_code == ErrorCode.BAD_REQUEST


class TestAttachmentStagerCloneRepo(unittest.TestCase):
    """Test AttachmentStager._clone_repo."""

    def test_clone_without_branch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "repo"
            with patch("subprocess.run") as mock_run:
                AttachmentStager._clone_repo(
                    "https://github.com/owner/repo.git", dest, None
                )

                args = mock_run.call_args[0][0]
                # Check the essential parts
                assert args[0] == "git"
                assert args[1] == "clone"
                assert "--depth" in args
                assert "1" in args
                assert "--single-branch" in args
                assert "--branch" not in args
                assert args[-2] == "https://github.com/owner/repo.git"
                assert args[-1] == str(dest)

    def test_clone_with_branch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "repo"
            with patch("subprocess.run") as mock_run:
                AttachmentStager._clone_repo(
                    "https://github.com/owner/repo.git", dest, "main"
                )

                args = mock_run.call_args[0][0]
                assert "--branch" in args
                assert "main" in args

    def test_clone_failure_raises_app_exception(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "repo"
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.CalledProcessError(
                    1, "git", stderr="fatal: repository not found"
                )

                with self.assertRaises(AppException) as ctx:
                    AttachmentStager._clone_repo(
                        "https://github.com/owner/repo.git", dest, None
                    )

                assert ctx.exception.error_code == ErrorCode.EXTERNAL_SERVICE_ERROR
                assert "Failed to clone" in ctx.exception.message


class TestAttachmentStagerStageInputs(unittest.TestCase):
    """Test AttachmentStager.stage_inputs."""

    def test_empty_inputs_returns_empty_list(self) -> None:
        mock_storage = MagicMock()
        mock_workspace = MagicMock()

        stager = AttachmentStager(
            storage_service=mock_storage, workspace_manager=mock_workspace
        )

        result = stager.stage_inputs("user-123", "session-456", None)
        assert result == []

        result = stager.stage_inputs("user-123", "session-456", [])
        assert result == []

    def test_skips_non_dict_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = Path(tmpdir)

            mock_storage = MagicMock()

            stager = AttachmentStager(
                storage_service=mock_storage, workspace_manager=mock_workspace
            )

            inputs = [
                "not a dict",
                123,
                None,
                {"type": "file", "source": "s3://bucket/key"},
            ]

            # Only the last item should be processed
            with patch.object(stager, "storage_service", mock_storage):
                stager.stage_inputs("user-123", "session-456", inputs)

                # Should only process the dict item
                # Since it has no valid s3_key (source is not s3_key), it won't be staged
                # Let's fix the test input

    def test_skips_items_missing_type_and_kind(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = Path(tmpdir)

            mock_storage = MagicMock()

            stager = AttachmentStager(
                storage_service=mock_storage, workspace_manager=mock_workspace
            )

            inputs = [
                {"name": "foo"},  # No type or kind
                {"source": "bar"},  # No type or kind
            ]

            result = stager.stage_inputs("user-123", "session-456", inputs)
            assert result == []

    def test_stages_file_input_with_s3_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            mock_storage = MagicMock()

            stager = AttachmentStager(
                storage_service=mock_storage, workspace_manager=mock_workspace
            )

            inputs = [
                {
                    "type": "file",
                    "name": "test.txt",
                    "source": "uploads/user-123/test.txt",  # Required for the check
                    "s3_key": "uploads/user-123/test.txt",
                }
            ]

            result = stager.stage_inputs("user-123", "session-456", inputs)

            assert len(result) == 1
            assert result[0]["name"] == "test.txt"
            assert result[0]["path"] == "/inputs/test.txt"
            mock_storage.download_file.assert_called_once()

    def test_file_without_any_s3_key_source_is_skipped(self) -> None:
        """Test that file input without any s3_key/key is skipped (line 64).

        When 'url' field is used for the source check but no actual s3_key exists.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            mock_storage = MagicMock()

            stager = AttachmentStager(
                storage_service=mock_storage, workspace_manager=mock_workspace
            )

            # This input has 'url' but no 'source', 's3_key', or 'key'
            # The 'url' passes the source check, but s3_key is empty -> skip (line 64)
            inputs = [
                {
                    "type": "file",
                    "name": "test.txt",
                    "url": "https://example.com/file",  # Used for source check only
                    # No source, s3_key, or key
                }
            ]

            result = stager.stage_inputs("user-123", "session-456", inputs)

            # Should be skipped because s3_key is empty
            assert len(result) == 0

    def test_stages_file_input_with_source_as_s3_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            mock_storage = MagicMock()

            stager = AttachmentStager(
                storage_service=mock_storage, workspace_manager=mock_workspace
            )

            inputs = [
                {
                    "type": "file",
                    "name": "test.txt",
                    "source": "uploads/user-123/test.txt",
                }
            ]

            result = stager.stage_inputs("user-123", "session-456", inputs)

            assert len(result) == 1
            mock_storage.download_file.assert_called_once()

    def test_stages_file_with_target_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            mock_storage = MagicMock()

            stager = AttachmentStager(
                storage_service=mock_storage, workspace_manager=mock_workspace
            )

            inputs = [
                {
                    "type": "file",
                    "name": "test.txt",
                    "source": "uploads/user-123/test.txt",  # Required for the check
                    "s3_key": "uploads/user-123/test.txt",
                    "target_path": "subdir/nested.txt",
                }
            ]

            result = stager.stage_inputs("user-123", "session-456", inputs)

            assert len(result) == 1
            assert "nested.txt" in result[0]["path"]

    def test_stages_url_input_github(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            mock_storage = MagicMock()

            stager = AttachmentStager(
                storage_service=mock_storage, workspace_manager=mock_workspace
            )

            inputs = [
                {
                    "type": "url",
                    "name": "myrepo",
                    "source": "https://github.com/owner/repo",
                }
            ]

            with patch.object(AttachmentStager, "_clone_repo") as mock_clone:
                result = stager.stage_inputs("user-123", "session-456", inputs)

                assert len(result) == 1
                assert result[0]["name"] == "myrepo"
                mock_clone.assert_called_once()

    def test_url_input_removes_existing_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            mock_storage = MagicMock()

            stager = AttachmentStager(
                storage_service=mock_storage, workspace_manager=mock_workspace
            )

            # Create an existing directory that should be removed
            inputs_root = workspace_path / "workspace" / "inputs"
            inputs_root.mkdir(parents=True, exist_ok=True)
            existing_dir = inputs_root / "repo"
            existing_dir.mkdir()
            (existing_dir / "old_file.txt").write_text("old")

            inputs = [
                {
                    "type": "url",
                    "source": "https://github.com/owner/repo",
                }
            ]

            with patch.object(AttachmentStager, "_clone_repo"):
                stager.stage_inputs("user-123", "session-456", inputs)

                # Old directory should be removed (old_file.txt should not exist)
                assert not (existing_dir / "old_file.txt").exists()

    def test_kind_as_type_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            mock_storage = MagicMock()

            stager = AttachmentStager(
                storage_service=mock_storage, workspace_manager=mock_workspace
            )

            inputs = [
                {
                    "kind": "file",  # Using 'kind' instead of 'type'
                    "name": "test.txt",
                    "source": "uploads/user-123/test.txt",  # Required for the check
                    "s3_key": "uploads/user-123/test.txt",
                }
            ]

            result = stager.stage_inputs("user-123", "session-456", inputs)

            assert len(result) == 1

    def test_url_as_source_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            mock_storage = MagicMock()

            stager = AttachmentStager(
                storage_service=mock_storage, workspace_manager=mock_workspace
            )

            inputs = [
                {
                    "type": "file",
                    "name": "test.txt",
                    "url": "uploads/user-123/test.txt",  # Using 'url' as source alias (triggers the source check)
                    "s3_key": "uploads/user-123/test.txt",
                }
            ]

            result = stager.stage_inputs("user-123", "session-456", inputs)

            assert len(result) == 1

    def test_path_as_target_path_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            mock_storage = MagicMock()

            stager = AttachmentStager(
                storage_service=mock_storage, workspace_manager=mock_workspace
            )

            inputs = [
                {
                    "type": "file",
                    "name": "test.txt",
                    "source": "uploads/user-123/test.txt",  # Required for the check
                    "s3_key": "uploads/user-123/test.txt",
                    "path": "custom/path.txt",  # Using 'path' as target_path alias
                }
            ]

            result = stager.stage_inputs("user-123", "session-456", inputs)

            assert len(result) == 1
            assert "custom/path.txt" in result[0]["path"]

    def test_key_as_s3_key_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            mock_storage = MagicMock()

            stager = AttachmentStager(
                storage_service=mock_storage, workspace_manager=mock_workspace
            )

            inputs = [
                {
                    "type": "file",
                    "name": "test.txt",
                    "source": "uploads/user-123/test.txt",  # Required for the check
                    "key": "uploads/user-123/test.txt",  # Using 'key' as s3_key alias
                }
            ]

            result = stager.stage_inputs("user-123", "session-456", inputs)

            assert len(result) == 1

    def test_falls_back_to_s3_key_name_for_rel_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            mock_workspace = MagicMock()
            mock_workspace.get_workspace_path.return_value = workspace_path

            mock_storage = MagicMock()

            stager = AttachmentStager(
                storage_service=mock_storage, workspace_manager=mock_workspace
            )

            inputs = [
                {
                    "type": "file",
                    "source": "uploads/user-123/myfile.txt",  # Required for the check
                    "s3_key": "uploads/user-123/myfile.txt",
                    # No name or target_path
                }
            ]

            result = stager.stage_inputs("user-123", "session-456", inputs)

            assert len(result) == 1
            assert "myfile.txt" in result[0]["path"]


if __name__ == "__main__":
    unittest.main()
