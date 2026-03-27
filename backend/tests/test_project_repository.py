import unittest
import uuid
from unittest.mock import MagicMock

from app.models.project import Project
from app.repositories.project_repository import ProjectRepository


class TestProjectRepositoryCreate(unittest.TestCase):
    """Test ProjectRepository.create method."""

    def test_create(self) -> None:
        db = MagicMock()
        project = MagicMock(spec=Project)
        project.id = uuid.uuid4()

        result = ProjectRepository.create(db, project)

        self.assertEqual(result, project)
        db.add.assert_called_once_with(project)


class TestProjectRepositoryGetById(unittest.TestCase):
    """Test ProjectRepository.get_by_id method."""

    def test_get_by_id_found(self) -> None:
        db = MagicMock()
        project_id = uuid.uuid4()
        mock_project = MagicMock()
        mock_query = MagicMock()
        mock_filter = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_project

        result = ProjectRepository.get_by_id(db, project_id)

        self.assertEqual(result, mock_project)
        db.query.assert_called_once_with(Project)

    def test_get_by_id_not_found(self) -> None:
        db = MagicMock()
        project_id = uuid.uuid4()
        mock_query = MagicMock()
        mock_filter = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.filter.return_value = mock_filter
        mock_filter.first.return_value = None

        result = ProjectRepository.get_by_id(db, project_id)

        self.assertIsNone(result)

    def test_get_by_id_include_deleted(self) -> None:
        db = MagicMock()
        project_id = uuid.uuid4()
        mock_project = MagicMock()
        mock_query = MagicMock()
        mock_filter = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_project

        result = ProjectRepository.get_by_id(db, project_id, include_deleted=True)

        self.assertEqual(result, mock_project)
        # Should not apply is_deleted filter
        mock_filter.filter.assert_not_called()

    def test_get_by_id_exclude_deleted(self) -> None:
        db = MagicMock()
        project_id = uuid.uuid4()
        mock_project = MagicMock()
        mock_query = MagicMock()
        mock_filter = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_project

        result = ProjectRepository.get_by_id(db, project_id, include_deleted=False)

        self.assertEqual(result, mock_project)
        # Should apply is_deleted filter
        mock_filter.filter.assert_called_once()


class TestProjectRepositoryListByUser(unittest.TestCase):
    """Test ProjectRepository.list_by_user method."""

    def test_list_by_user(self) -> None:
        db = MagicMock()
        user_id = "user-123"
        mock_projects = [MagicMock(), MagicMock()]
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.all.return_value = mock_projects

        result = ProjectRepository.list_by_user(db, user_id)

        self.assertEqual(result, mock_projects)

    def test_list_by_user_include_deleted(self) -> None:
        db = MagicMock()
        user_id = "user-123"
        mock_projects = [MagicMock()]
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.all.return_value = mock_projects

        result = ProjectRepository.list_by_user(db, user_id, include_deleted=True)

        self.assertEqual(result, mock_projects)
        # Should not apply is_deleted filter
        mock_filter.filter.assert_not_called()

    def test_list_by_user_exclude_deleted(self) -> None:
        db = MagicMock()
        user_id = "user-123"
        mock_projects = [MagicMock()]
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.all.return_value = mock_projects

        result = ProjectRepository.list_by_user(db, user_id, include_deleted=False)

        self.assertEqual(result, mock_projects)
        # Should apply is_deleted filter
        mock_filter.filter.assert_called_once()

    def test_list_by_user_empty(self) -> None:
        db = MagicMock()
        user_id = "user-123"
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.all.return_value = []

        result = ProjectRepository.list_by_user(db, user_id)

        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
