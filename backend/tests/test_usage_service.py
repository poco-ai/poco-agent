import unittest
import uuid
from unittest.mock import MagicMock, patch

from app.services.usage_service import UsageService


def create_mock_usage_log(
    total_cost_usd: float | None = None,
    duration_ms: int | None = None,
    usage_json: dict | None = None,
    run_id: uuid.UUID | None = None,
) -> MagicMock:
    """Create a mock usage log with all required fields."""
    mock = MagicMock()
    mock.total_cost_usd = total_cost_usd
    mock.duration_ms = duration_ms
    mock.usage_json = usage_json
    mock.run_id = run_id
    return mock


class TestUsageServiceAggregateLogs(unittest.TestCase):
    """Test _aggregate_logs static method."""

    def test_aggregate_empty_logs(self) -> None:
        result = UsageService._aggregate_logs([])

        self.assertIsNone(result.total_cost_usd)
        self.assertIsNone(result.total_duration_ms)
        self.assertIsNone(result.usage_json)

    def test_aggregate_single_log(self) -> None:
        log = create_mock_usage_log(
            total_cost_usd=1.5,
            duration_ms=1000,
            usage_json={"tokens": 100, "requests": 1},
        )

        result = UsageService._aggregate_logs([log])

        self.assertEqual(result.total_cost_usd, 1.5)
        self.assertEqual(result.total_duration_ms, 1000)
        self.assertEqual(result.usage_json, {"tokens": 100, "requests": 1})

    def test_aggregate_multiple_logs(self) -> None:
        logs = [
            create_mock_usage_log(
                total_cost_usd=1.5,
                duration_ms=1000,
                usage_json={"tokens": 100, "requests": 1},
            ),
            create_mock_usage_log(
                total_cost_usd=2.5,
                duration_ms=2000,
                usage_json={"tokens": 200, "requests": 2},
            ),
        ]

        result = UsageService._aggregate_logs(logs)

        self.assertEqual(result.total_cost_usd, 4.0)
        self.assertEqual(result.total_duration_ms, 3000)
        self.assertEqual(result.usage_json, {"tokens": 300, "requests": 3})

    def test_aggregate_logs_with_none_values(self) -> None:
        logs = [
            create_mock_usage_log(total_cost_usd=None, duration_ms=None),
            create_mock_usage_log(total_cost_usd=1.0, duration_ms=500),
        ]

        result = UsageService._aggregate_logs(logs)

        self.assertEqual(result.total_cost_usd, 1.0)
        self.assertEqual(result.total_duration_ms, 500)

    def test_aggregate_logs_with_non_numeric_usage(self) -> None:
        logs = [
            create_mock_usage_log(usage_json={"model": "gpt-4", "tokens": 100}),
            create_mock_usage_log(usage_json={"model": "gpt-3.5", "tokens": 200}),
        ]

        result = UsageService._aggregate_logs(logs)

        self.assertEqual(result.usage_json["tokens"], 300)
        # Non-numeric fields should keep the last value
        self.assertEqual(result.usage_json["model"], "gpt-3.5")

    def test_aggregate_logs_without_usage_json(self) -> None:
        logs = [
            create_mock_usage_log(total_cost_usd=1.0, duration_ms=500),
        ]

        result = UsageService._aggregate_logs(logs)

        self.assertIsNone(result.usage_json)


class TestUsageServiceGetUsageSummary(unittest.TestCase):
    """Test get_usage_summary method."""

    def test_get_usage_summary_empty(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()

        with patch("app.services.usage_service.UsageLogRepository") as mock_repo:
            mock_repo.list_by_session.return_value = []
            service = UsageService()
            result = service.get_usage_summary(db, session_id)

            self.assertIsNone(result.total_cost_usd)
            self.assertIsNone(result.total_duration_ms)
            mock_repo.list_by_session.assert_called_once_with(db, session_id)

    def test_get_usage_summary_with_data(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        logs = [
            create_mock_usage_log(total_cost_usd=1.0, duration_ms=500),
        ]

        with patch("app.services.usage_service.UsageLogRepository") as mock_repo:
            mock_repo.list_by_session.return_value = logs
            service = UsageService()
            result = service.get_usage_summary(db, session_id)

            self.assertEqual(result.total_cost_usd, 1.0)
            self.assertEqual(result.total_duration_ms, 500)


class TestUsageServiceGetUsageSummaryByRun(unittest.TestCase):
    """Test get_usage_summary_by_run method."""

    def test_get_usage_summary_by_run_not_found(self) -> None:
        db = MagicMock()
        run_id = uuid.uuid4()

        with patch("app.services.usage_service.UsageLogRepository") as mock_repo:
            mock_repo.list_by_run.return_value = []
            service = UsageService()
            result = service.get_usage_summary_by_run(db, run_id)

            self.assertIsNone(result)
            mock_repo.list_by_run.assert_called_once_with(db, run_id)

    def test_get_usage_summary_by_run_with_data(self) -> None:
        db = MagicMock()
        run_id = uuid.uuid4()
        logs = [
            create_mock_usage_log(total_cost_usd=2.0, duration_ms=1000, run_id=run_id),
        ]

        with patch("app.services.usage_service.UsageLogRepository") as mock_repo:
            mock_repo.list_by_run.return_value = logs
            service = UsageService()
            result = service.get_usage_summary_by_run(db, run_id)

            self.assertIsNotNone(result)
            self.assertEqual(result.total_cost_usd, 2.0)


class TestUsageServiceGetUsageSummariesByRunIds(unittest.TestCase):
    """Test get_usage_summaries_by_run_ids method."""

    def test_get_usage_summaries_empty_ids(self) -> None:
        db = MagicMock()

        with patch("app.services.usage_service.UsageLogRepository") as mock_repo:
            mock_repo.list_by_run_ids.return_value = []
            service = UsageService()
            result = service.get_usage_summaries_by_run_ids(db, [])

            self.assertEqual(result, {})

    def test_get_usage_summaries_no_logs(self) -> None:
        db = MagicMock()
        run_ids = [uuid.uuid4(), uuid.uuid4()]

        with patch("app.services.usage_service.UsageLogRepository") as mock_repo:
            mock_repo.list_by_run_ids.return_value = []
            service = UsageService()
            result = service.get_usage_summaries_by_run_ids(db, run_ids)

            self.assertEqual(result, {})

    def test_get_usage_summaries_with_logs(self) -> None:
        db = MagicMock()
        run_id1 = uuid.uuid4()
        run_id2 = uuid.uuid4()
        run_ids = [run_id1, run_id2]

        logs = [
            create_mock_usage_log(total_cost_usd=1.0, duration_ms=500, run_id=run_id1),
            create_mock_usage_log(total_cost_usd=2.0, duration_ms=1000, run_id=run_id1),
            create_mock_usage_log(total_cost_usd=3.0, duration_ms=1500, run_id=run_id2),
        ]

        with patch("app.services.usage_service.UsageLogRepository") as mock_repo:
            mock_repo.list_by_run_ids.return_value = logs
            service = UsageService()
            result = service.get_usage_summaries_by_run_ids(db, run_ids)

            self.assertIn(run_id1, result)
            self.assertIn(run_id2, result)
            self.assertEqual(result[run_id1].total_cost_usd, 3.0)
            self.assertEqual(result[run_id2].total_cost_usd, 3.0)

    def test_get_usage_summaries_logs_without_run_id(self) -> None:
        db = MagicMock()
        run_id = uuid.uuid4()

        logs = [
            create_mock_usage_log(total_cost_usd=1.0, duration_ms=500, run_id=None),
            create_mock_usage_log(total_cost_usd=2.0, duration_ms=1000, run_id=run_id),
        ]

        with patch("app.services.usage_service.UsageLogRepository") as mock_repo:
            mock_repo.list_by_run_ids.return_value = logs
            service = UsageService()
            result = service.get_usage_summaries_by_run_ids(db, [run_id])

            # Only the log with run_id should be included
            self.assertIn(run_id, result)
            self.assertEqual(result[run_id].total_cost_usd, 2.0)


if __name__ == "__main__":
    unittest.main()
