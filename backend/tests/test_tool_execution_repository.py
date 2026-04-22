import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from app.repositories.tool_execution_repository import ToolExecutionRepository


class ToolExecutionRepositoryTests(unittest.TestCase):
    def test_count_by_run_ids_returns_empty_for_empty_input(self) -> None:
        db = MagicMock()

        self.assertEqual(ToolExecutionRepository.count_by_run_ids(db, []), {})
        db.query.assert_not_called()

    def test_count_by_run_ids_returns_grouped_counts(self) -> None:
        db = MagicMock()
        run_id_1 = uuid4()
        run_id_2 = uuid4()

        query = db.query.return_value
        query.filter.return_value = query
        query.group_by.return_value = query
        query.all.return_value = [
            (run_id_1, 3),
            (run_id_2, 1),
            (None, 99),
        ]

        result = ToolExecutionRepository.count_by_run_ids(db, [run_id_1, run_id_2])

        self.assertEqual(result, {run_id_1: 3, run_id_2: 1})
        self.assertEqual(query.filter.call_count, 2)
        query.group_by.assert_called_once()

    def test_count_by_run_ids_applies_replayable_filter(self) -> None:
        db = MagicMock()
        run_id = uuid4()

        query = db.query.return_value
        query.filter.return_value = query
        query.group_by.return_value = query
        query.all.return_value = []

        ToolExecutionRepository.count_by_run_ids(db, [run_id])

        self.assertEqual(query.filter.call_count, 2)
        run_id_filter = query.filter.call_args_list[0].args[0]
        replayable_filter = query.filter.call_args_list[1].args[0]

        self.assertIsNotNone(run_id_filter)
        self.assertIsNotNone(replayable_filter)
        self.assertIn("tool_name", str(replayable_filter))
        self.assertIn("LIKE", str(replayable_filter))
        self.assertIn("IN", str(replayable_filter))


if __name__ == "__main__":
    unittest.main()
