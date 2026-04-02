import unittest
from unittest.mock import MagicMock

from app.models.project import Project
from app.repositories.preset_repository import PresetRepository


class PresetRepositoryTests(unittest.TestCase):
    def test_count_projects_using_as_default_ignores_soft_deleted_projects(
        self,
    ) -> None:
        session_db = MagicMock()
        query = session_db.query.return_value
        query.filter.return_value.count.return_value = 3

        result = PresetRepository.count_projects_using_as_default(session_db, 42)

        filter_args = query.filter.call_args.args
        self.assertEqual(len(filter_args), 2)
        self.assertEqual(filter_args[0].left.key, "default_preset_id")
        self.assertEqual(filter_args[0].right.value, 42)
        self.assertEqual(str(filter_args[1]), "projects.is_deleted IS false")
        self.assertEqual(result, 3)


if __name__ == "__main__":
    unittest.main()
