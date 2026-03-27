import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.schemas.project import ProjectCreateRequest, ProjectUpdateRequest
from app.services.project_service import ProjectService


def create_mock_project(
    project_id: uuid.UUID | None = None,
    user_id: str = "user-123",
    name: str = "Test Project",
    repo_url: str | None = None,
    git_branch: str | None = None,
    git_token_env_key: str | None = None,
    is_deleted: bool = False,
) -> MagicMock:
    """Create a properly configured mock project."""
    mock = MagicMock()
    mock.id = project_id or uuid.uuid4()
    mock.user_id = user_id
    mock.name = name
    mock.repo_url = repo_url
    mock.git_branch = git_branch
    mock.git_token_env_key = git_token_env_key
    mock.is_deleted = is_deleted
    mock.created_at = datetime.now(timezone.utc)
    mock.updated_at = datetime.now(timezone.utc)
    return mock


class TestProjectServiceNormalizeOptionalStr(unittest.TestCase):
    """Test _normalize_optional_str static method."""

    def test_none_value(self) -> None:
        result = ProjectService._normalize_optional_str(None)
        self.assertIsNone(result)

    def test_empty_string(self) -> None:
        result = ProjectService._normalize_optional_str("")
        self.assertIsNone(result)

    def test_whitespace_only(self) -> None:
        result = ProjectService._normalize_optional_str("   ")
        self.assertIsNone(result)

    def test_valid_string(self) -> None:
        result = ProjectService._normalize_optional_str("  hello  ")
        self.assertEqual(result, "hello")

    def test_string_no_whitespace(self) -> None:
        result = ProjectService._normalize_optional_str("world")
        self.assertEqual(result, "world")


class TestProjectServiceNormalizeGithubRepoUrl(unittest.TestCase):
    """Test _normalize_github_repo_url static method."""

    def test_valid_https_url(self) -> None:
        result = ProjectService._normalize_github_repo_url(
            "https://github.com/owner/repo"
        )
        self.assertEqual(result, "https://github.com/owner/repo")

    def test_valid_http_url(self) -> None:
        result = ProjectService._normalize_github_repo_url(
            "http://github.com/owner/repo"
        )
        self.assertEqual(result, "https://github.com/owner/repo")

    def test_url_with_www(self) -> None:
        result = ProjectService._normalize_github_repo_url(
            "https://www.github.com/owner/repo"
        )
        self.assertEqual(result, "https://github.com/owner/repo")

    def test_url_with_git_suffix(self) -> None:
        result = ProjectService._normalize_github_repo_url(
            "https://github.com/owner/repo.git"
        )
        self.assertEqual(result, "https://github.com/owner/repo")

    def test_url_with_extra_path(self) -> None:
        result = ProjectService._normalize_github_repo_url(
            "https://github.com/owner/repo/tree/main"
        )
        self.assertEqual(result, "https://github.com/owner/repo")

    def test_invalid_scheme(self) -> None:
        with self.assertRaises(AppException) as ctx:
            ProjectService._normalize_github_repo_url("ftp://github.com/owner/repo")
        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    def test_non_github_host(self) -> None:
        with self.assertRaises(AppException) as ctx:
            ProjectService._normalize_github_repo_url("https://gitlab.com/owner/repo")
        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    def test_missing_repo(self) -> None:
        with self.assertRaises(AppException) as ctx:
            ProjectService._normalize_github_repo_url("https://github.com/owner")
        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    def test_missing_owner_and_repo(self) -> None:
        with self.assertRaises(AppException) as ctx:
            ProjectService._normalize_github_repo_url("https://github.com/")
        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    def test_empty_owner(self) -> None:
        with self.assertRaises(AppException) as ctx:
            ProjectService._normalize_github_repo_url("https://github.com//repo")
        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    def test_empty_repo(self) -> None:
        # This URL has owner but empty repo after stripping trailing slash
        with self.assertRaises(AppException) as ctx:
            ProjectService._normalize_github_repo_url("https://github.com/owner/   ")
        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    def test_uppercase_preserved(self) -> None:
        result = ProjectService._normalize_github_repo_url(
            "https://github.com/Owner/Repo"
        )
        self.assertEqual(result, "https://github.com/Owner/Repo")


class TestProjectServiceNormalizeRepoSettings(unittest.TestCase):
    """Test _normalize_repo_settings class method."""

    def test_no_repo_url(self) -> None:
        result = ProjectService._normalize_repo_settings(
            repo_url=None, git_branch="main", git_token_env_key="TOKEN"
        )
        self.assertEqual(result, (None, None, None))

    def test_empty_repo_url(self) -> None:
        result = ProjectService._normalize_repo_settings(
            repo_url="", git_branch="main", git_token_env_key="TOKEN"
        )
        self.assertEqual(result, (None, None, None))

    def test_valid_repo_url_with_defaults(self) -> None:
        result = ProjectService._normalize_repo_settings(
            repo_url="https://github.com/owner/repo",
            git_branch=None,
            git_token_env_key=None,
        )
        self.assertEqual(result, ("https://github.com/owner/repo", "main", None))

    def test_valid_repo_url_with_branch(self) -> None:
        result = ProjectService._normalize_repo_settings(
            repo_url="https://github.com/owner/repo",
            git_branch="develop",
            git_token_env_key=None,
        )
        self.assertEqual(result, ("https://github.com/owner/repo", "develop", None))

    def test_valid_repo_url_with_token(self) -> None:
        result = ProjectService._normalize_repo_settings(
            repo_url="https://github.com/owner/repo",
            git_branch="main",
            git_token_env_key="GITHUB_TOKEN",
        )
        self.assertEqual(
            result, ("https://github.com/owner/repo", "main", "GITHUB_TOKEN")
        )


class TestProjectServiceListProjects(unittest.TestCase):
    """Test list_projects method."""

    def test_list_projects_empty(self) -> None:
        db = MagicMock()
        user_id = "user-123"
        with patch("app.services.project_service.ProjectRepository") as mock_repo:
            mock_repo.list_by_user.return_value = []
            service = ProjectService()
            result = service.list_projects(db, user_id)
            self.assertEqual(result, [])

    def test_list_projects_with_data(self) -> None:
        db = MagicMock()
        user_id = "user-123"
        mock_project = create_mock_project(user_id=user_id)

        with patch("app.services.project_service.ProjectRepository") as mock_repo:
            mock_repo.list_by_user.return_value = [mock_project]
            service = ProjectService()
            result = service.list_projects(db, user_id)
            self.assertEqual(len(result), 1)


class TestProjectServiceGetProject(unittest.TestCase):
    """Test get_project method."""

    def test_get_project_not_found(self) -> None:
        db = MagicMock()
        user_id = "user-123"
        project_id = uuid.uuid4()
        with patch("app.services.project_service.ProjectRepository") as mock_repo:
            mock_repo.get_by_id.return_value = None
            service = ProjectService()
            with self.assertRaises(AppException) as ctx:
                service.get_project(db, user_id, project_id)
            self.assertEqual(ctx.exception.error_code, ErrorCode.PROJECT_NOT_FOUND)

    def test_get_project_wrong_user(self) -> None:
        db = MagicMock()
        user_id = "user-123"
        project_id = uuid.uuid4()
        mock_project = create_mock_project(user_id="other-user")

        with patch("app.services.project_service.ProjectRepository") as mock_repo:
            mock_repo.get_by_id.return_value = mock_project
            service = ProjectService()
            with self.assertRaises(AppException) as ctx:
                service.get_project(db, user_id, project_id)
            self.assertEqual(ctx.exception.error_code, ErrorCode.PROJECT_NOT_FOUND)

    def test_get_project_success(self) -> None:
        db = MagicMock()
        user_id = "user-123"
        project_id = uuid.uuid4()
        mock_project = create_mock_project(project_id=project_id, user_id=user_id)

        with patch("app.services.project_service.ProjectRepository") as mock_repo:
            mock_repo.get_by_id.return_value = mock_project
            service = ProjectService()
            result = service.get_project(db, user_id, project_id)
            self.assertIsNotNone(result)


class TestProjectServiceCreateProject(unittest.TestCase):
    """Test create_project method."""

    def test_create_project_without_repo(self) -> None:
        db = MagicMock()
        user_id = "user-123"
        request = ProjectCreateRequest(name="Test Project")

        with patch("app.services.project_service.ProjectRepository") as mock_repo:
            mock_project = create_mock_project(user_id=user_id, name="Test Project")

            def set_attrs(p: MagicMock) -> MagicMock:
                p.id = mock_project.id
                p.created_at = mock_project.created_at
                p.updated_at = mock_project.updated_at
                return p

            db.refresh.side_effect = lambda p: set_attrs(p)
            mock_repo.create.return_value = None

            service = ProjectService()
            result = service.create_project(db, user_id, request)

            db.commit.assert_called_once()
            self.assertIsNotNone(result)

    def test_create_project_with_repo(self) -> None:
        db = MagicMock()
        user_id = "user-123"
        request = ProjectCreateRequest(
            name="Test Project",
            repo_url="https://github.com/owner/repo",
            git_branch="develop",
            git_token_env_key="GITHUB_TOKEN",
        )

        with patch("app.services.project_service.ProjectRepository") as mock_repo:
            mock_project = create_mock_project(
                user_id=user_id,
                name="Test Project",
                repo_url="https://github.com/owner/repo",
                git_branch="develop",
                git_token_env_key="GITHUB_TOKEN",
            )

            def set_attrs(p: MagicMock) -> MagicMock:
                p.id = mock_project.id
                p.created_at = mock_project.created_at
                p.updated_at = mock_project.updated_at
                return p

            db.refresh.side_effect = lambda p: set_attrs(p)
            mock_repo.create.return_value = None

            service = ProjectService()
            service.create_project(db, user_id, request)

            db.commit.assert_called_once()


class TestProjectServiceUpdateProject(unittest.TestCase):
    """Test update_project method."""

    def test_update_project_not_found(self) -> None:
        db = MagicMock()
        user_id = "user-123"
        project_id = uuid.uuid4()
        request = ProjectUpdateRequest(name="New Name")

        with patch("app.services.project_service.ProjectRepository") as mock_repo:
            mock_repo.get_by_id.return_value = None
            service = ProjectService()
            with self.assertRaises(AppException) as ctx:
                service.update_project(db, user_id, project_id, request)
            self.assertEqual(ctx.exception.error_code, ErrorCode.PROJECT_NOT_FOUND)

    def test_update_project_wrong_user(self) -> None:
        db = MagicMock()
        user_id = "user-123"
        project_id = uuid.uuid4()
        request = ProjectUpdateRequest(name="New Name")
        mock_project = create_mock_project(user_id="other-user")

        with patch("app.services.project_service.ProjectRepository") as mock_repo:
            mock_repo.get_by_id.return_value = mock_project
            service = ProjectService()
            with self.assertRaises(AppException) as ctx:
                service.update_project(db, user_id, project_id, request)
            self.assertEqual(ctx.exception.error_code, ErrorCode.PROJECT_NOT_FOUND)

    def test_update_project_name(self) -> None:
        db = MagicMock()
        user_id = "user-123"
        project_id = uuid.uuid4()
        request = ProjectUpdateRequest(name="New Name")
        mock_project = create_mock_project(
            project_id=project_id, user_id=user_id, name="Old Name"
        )

        with patch("app.services.project_service.ProjectRepository") as mock_repo:
            mock_repo.get_by_id.return_value = mock_project
            service = ProjectService()
            service.update_project(db, user_id, project_id, request)
            self.assertEqual(mock_project.name, "New Name")
            db.commit.assert_called_once()

    def test_update_project_repo_url(self) -> None:
        db = MagicMock()
        user_id = "user-123"
        project_id = uuid.uuid4()
        request = ProjectUpdateRequest(repo_url="https://github.com/owner/new-repo")
        mock_project = create_mock_project(
            project_id=project_id,
            user_id=user_id,
            repo_url="https://github.com/owner/old-repo",
            git_branch="main",
        )

        with patch("app.services.project_service.ProjectRepository") as mock_repo:
            mock_repo.get_by_id.return_value = mock_project
            service = ProjectService()
            service.update_project(db, user_id, project_id, request)
            self.assertEqual(mock_project.repo_url, "https://github.com/owner/new-repo")
            db.commit.assert_called_once()

    def test_update_git_branch_without_repo_fails(self) -> None:
        db = MagicMock()
        user_id = "user-123"
        project_id = uuid.uuid4()
        request = ProjectUpdateRequest(git_branch="develop")
        mock_project = create_mock_project(
            project_id=project_id, user_id=user_id, repo_url=None
        )

        with patch("app.services.project_service.ProjectRepository") as mock_repo:
            mock_repo.get_by_id.return_value = mock_project
            service = ProjectService()
            with self.assertRaises(AppException) as ctx:
                service.update_project(db, user_id, project_id, request)
            self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    def test_update_git_token_without_repo_fails(self) -> None:
        db = MagicMock()
        user_id = "user-123"
        project_id = uuid.uuid4()
        request = ProjectUpdateRequest(git_token_env_key="TOKEN")
        mock_project = create_mock_project(
            project_id=project_id, user_id=user_id, repo_url=None
        )

        with patch("app.services.project_service.ProjectRepository") as mock_repo:
            mock_repo.get_by_id.return_value = mock_project
            service = ProjectService()
            with self.assertRaises(AppException) as ctx:
                service.update_project(db, user_id, project_id, request)
            self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    def test_update_git_branch_with_repo(self) -> None:
        db = MagicMock()
        user_id = "user-123"
        project_id = uuid.uuid4()
        request = ProjectUpdateRequest(git_branch="develop")
        mock_project = create_mock_project(
            project_id=project_id,
            user_id=user_id,
            repo_url="https://github.com/owner/repo",
            git_branch="main",
        )

        with patch("app.services.project_service.ProjectRepository") as mock_repo:
            mock_repo.get_by_id.return_value = mock_project
            service = ProjectService()
            service.update_project(db, user_id, project_id, request)
            self.assertEqual(mock_project.git_branch, "develop")
            db.commit.assert_called_once()

    def test_update_git_token_env_key_with_repo(self) -> None:
        db = MagicMock()
        user_id = "user-123"
        project_id = uuid.uuid4()
        request = ProjectUpdateRequest(git_token_env_key="MY_TOKEN")
        mock_project = create_mock_project(
            project_id=project_id,
            user_id=user_id,
            repo_url="https://github.com/owner/repo",
            git_token_env_key=None,
        )

        with patch("app.services.project_service.ProjectRepository") as mock_repo:
            mock_repo.get_by_id.return_value = mock_project
            service = ProjectService()
            service.update_project(db, user_id, project_id, request)
            self.assertEqual(mock_project.git_token_env_key, "MY_TOKEN")
            db.commit.assert_called_once()


class TestProjectServiceDeleteProject(unittest.TestCase):
    """Test delete_project method."""

    def test_delete_project_not_found(self) -> None:
        db = MagicMock()
        user_id = "user-123"
        project_id = uuid.uuid4()

        with patch("app.services.project_service.ProjectRepository") as mock_repo:
            mock_repo.get_by_id.return_value = None
            service = ProjectService()
            with self.assertRaises(AppException) as ctx:
                service.delete_project(db, user_id, project_id)
            self.assertEqual(ctx.exception.error_code, ErrorCode.PROJECT_NOT_FOUND)

    def test_delete_project_wrong_user(self) -> None:
        db = MagicMock()
        user_id = "user-123"
        project_id = uuid.uuid4()
        mock_project = create_mock_project(user_id="other-user")

        with patch("app.services.project_service.ProjectRepository") as mock_repo:
            mock_repo.get_by_id.return_value = mock_project
            service = ProjectService()
            with self.assertRaises(AppException) as ctx:
                service.delete_project(db, user_id, project_id)
            self.assertEqual(ctx.exception.error_code, ErrorCode.PROJECT_NOT_FOUND)

    def test_delete_project_success(self) -> None:
        db = MagicMock()
        user_id = "user-123"
        project_id = uuid.uuid4()
        mock_project = create_mock_project(
            project_id=project_id, user_id=user_id, is_deleted=False
        )

        with patch("app.services.project_service.ProjectRepository") as mock_repo:
            with patch(
                "app.services.project_service.SessionRepository"
            ) as mock_session_repo:
                mock_repo.get_by_id.return_value = mock_project
                service = ProjectService()
                service.delete_project(db, user_id, project_id)
                self.assertTrue(mock_project.is_deleted)
                mock_session_repo.clear_project_id.assert_called_once_with(
                    db, project_id
                )
                db.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
