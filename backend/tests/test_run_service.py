import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.schemas.callback import AgentCurrentState, FileChange, WorkspaceState
from app.schemas.run import RunResponse
from app.schemas.usage import UsageResponse
from app.services.run_service import RunService


class RunServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = RunService()

    def _build_run_response(
        self,
        *,
        file_change_count: int = 0,
        file_changes: list[FileChange] | None = None,
    ) -> RunResponse:
        return RunResponse(
            id=uuid4(),
            session_id=uuid4(),
            user_message_id=1,
            status="completed",
            permission_mode="default",
            progress=100,
            schedule_mode="immediate",
            scheduled_at="2026-04-22T00:00:00Z",
            state_patch=AgentCurrentState(
                workspace_state=WorkspaceState(
                    file_change_count=file_change_count,
                    file_changes=file_changes or [],
                    last_change="2026-04-22T00:00:00Z",
                )
            ),
            claimed_by=None,
            lease_expires_at=None,
            attempts=1,
            last_error=None,
            started_at=None,
            finished_at=None,
            created_at="2026-04-22T00:00:00Z",
            updated_at="2026-04-22T00:00:00Z",
        )

    def test_resolve_file_change_count_prefers_explicit_workspace_count(self) -> None:
        run = self._build_run_response(
            file_change_count=7,
            file_changes=[
                FileChange(path="a.py", status="modified"),
                FileChange(path="a.py", status="modified"),
            ],
        )

        self.assertEqual(self.service._resolve_file_change_count(run), 7)

    def test_resolve_file_change_count_falls_back_to_unique_paths(self) -> None:
        run = self._build_run_response(
            file_change_count=0,
            file_changes=[
                FileChange(path="a.py", status="modified"),
                FileChange(path="a.py", status="modified"),
                FileChange(path="b.py", status="deleted"),
                FileChange(path="", status="modified"),
            ],
        )

        self.assertEqual(self.service._resolve_file_change_count(run), 2)

    def test_resolve_file_change_count_returns_zero_without_workspace_state(
        self,
    ) -> None:
        run = RunResponse(
            id=uuid4(),
            session_id=uuid4(),
            user_message_id=1,
            status="completed",
            permission_mode="default",
            progress=100,
            schedule_mode="immediate",
            scheduled_at="2026-04-22T00:00:00Z",
            state_patch=AgentCurrentState(),
            claimed_by=None,
            lease_expires_at=None,
            attempts=1,
            last_error=None,
            started_at=None,
            finished_at=None,
            created_at="2026-04-22T00:00:00Z",
            updated_at="2026-04-22T00:00:00Z",
        )

        self.assertEqual(self.service._resolve_file_change_count(run), 0)

    def _build_run_record(
        self,
        *,
        run_id=None,
        state_patch: dict | None = None,
    ) -> SimpleNamespace:
        now = "2026-04-22T00:00:00Z"
        return SimpleNamespace(
            id=run_id or uuid4(),
            session_id=uuid4(),
            user_message_id=1,
            status="completed",
            permission_mode="default",
            progress=100,
            schedule_mode="immediate",
            scheduled_task_id=None,
            scheduled_at=now,
            config_snapshot=None,
            state_patch=state_patch,
            workspace_archive_url=None,
            workspace_files_prefix=None,
            workspace_manifest_key=None,
            workspace_archive_key=None,
            workspace_export_status=None,
            claimed_by=None,
            lease_expires_at=None,
            attempts=1,
            last_error=None,
            started_at=None,
            finished_at=None,
            created_at=now,
            updated_at=now,
        )

    @patch("app.services.run_service.ToolExecutionRepository.count_by_run_ids")
    @patch("app.services.run_service.usage_service.get_usage_summary_by_run")
    @patch("app.services.run_service.RunRepository.get_by_id")
    def test_get_run_populates_replay_and_file_change_counts(
        self,
        get_by_id,
        get_usage_summary_by_run,
        count_by_run_ids,
    ) -> None:
        db = MagicMock()
        run_id = uuid4()
        db_run = self._build_run_record(
            run_id=run_id,
            state_patch={
                "workspace_state": {
                    "file_changes": [
                        {"path": "src/a.ts", "status": "modified"},
                        {"path": "src/a.ts", "status": "modified"},
                        {"path": "src/b.ts", "status": "deleted"},
                    ],
                    "last_change": "2026-04-22T00:00:00Z",
                }
            },
        )
        usage = UsageResponse(total_duration_ms=1234, usage_json={"tokens": 10})
        get_by_id.return_value = db_run
        get_usage_summary_by_run.return_value = usage
        count_by_run_ids.return_value = {run_id: 3}

        result = self.service.get_run(db, run_id)

        self.assertEqual(result.run_id, run_id)
        self.assertEqual(result.replay_step_count, 3)
        self.assertEqual(result.file_change_count, 2)
        self.assertEqual(result.usage, usage)
        get_by_id.assert_called_once_with(db, run_id)
        get_usage_summary_by_run.assert_called_once_with(db, run_id)
        count_by_run_ids.assert_called_once_with(db, [run_id])

    @patch("app.services.run_service.ToolExecutionRepository.count_by_run_ids")
    @patch("app.services.run_service.usage_service.get_usage_summaries_by_run_ids")
    @patch("app.services.run_service.RunRepository.list_by_session")
    def test_list_runs_populates_batched_summaries(
        self,
        list_by_session,
        get_usage_summaries_by_run_ids,
        count_by_run_ids,
    ) -> None:
        db = MagicMock()
        session_id = uuid4()
        run_id_1 = uuid4()
        run_id_2 = uuid4()
        run_1 = self._build_run_record(
            run_id=run_id_1,
            state_patch={
                "workspace_state": {
                    "file_change_count": 5,
                    "file_changes": [
                        {"path": "src/a.ts", "status": "modified"},
                    ],
                    "last_change": "2026-04-22T00:00:00Z",
                }
            },
        )
        run_2 = self._build_run_record(
            run_id=run_id_2,
            state_patch={
                "workspace_state": {
                    "file_changes": [
                        {"path": "src/b.ts", "status": "added"},
                        {"path": "src/c.ts", "status": "modified"},
                    ],
                    "last_change": "2026-04-22T00:00:00Z",
                }
            },
        )
        usage = UsageResponse(total_duration_ms=888, usage_json={"tokens": 5})
        list_by_session.return_value = [run_1, run_2]
        get_usage_summaries_by_run_ids.return_value = {run_id_2: usage}
        count_by_run_ids.return_value = {run_id_1: 4}

        results = self.service.list_runs(db, session_id, limit=20, offset=5)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].run_id, run_id_1)
        self.assertEqual(results[0].replay_step_count, 4)
        self.assertEqual(results[0].file_change_count, 5)
        self.assertIsNone(results[0].usage)
        self.assertEqual(results[1].run_id, run_id_2)
        self.assertEqual(results[1].replay_step_count, 0)
        self.assertEqual(results[1].file_change_count, 2)
        self.assertEqual(results[1].usage, usage)
        list_by_session.assert_called_once_with(db, session_id, limit=20, offset=5)
        get_usage_summaries_by_run_ids.assert_called_once_with(db, [run_id_1, run_id_2])
        count_by_run_ids.assert_called_once_with(db, [run_id_1, run_id_2])


if __name__ == "__main__":
    unittest.main()
