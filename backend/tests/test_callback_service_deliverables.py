import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from app.schemas.callback import AgentCallbackRequest, CallbackStatus
from app.services.callback_service import CallbackService


class CallbackServiceDeliverableTriggerTests(unittest.TestCase):
    def test_completed_export_ready_callback_triggers_detection(self) -> None:
        service = CallbackService()
        service._deliverable_detection = MagicMock()

        db_session = SimpleNamespace(
            id=uuid4(),
            status="completed",
            workspace_manifest_key="workspaces/user/session/manifest.json",
        )
        db_run = SimpleNamespace(id=uuid4(), user_message_id=123)
        callback = AgentCallbackRequest(
            session_id="session-123",
            run_id=str(db_run.id),
            time="2026-03-23T00:00:00+00:00",
            status=CallbackStatus.COMPLETED,
            progress=100,
            workspace_manifest_key=db_session.workspace_manifest_key,
            workspace_export_status="ready",
        )

        service._detect_deliverables_if_ready(
            db=object(),
            db_session=db_session,
            db_run=db_run,
            callback=callback,
        )

        service._deliverable_detection.detect_for_completed_run.assert_called_once()

    def test_pending_export_does_not_trigger_detection(self) -> None:
        service = CallbackService()
        service._deliverable_detection = MagicMock()
        callback = AgentCallbackRequest(
            session_id="session-123",
            run_id=str(uuid4()),
            time="2026-03-23T00:00:00+00:00",
            status=CallbackStatus.COMPLETED,
            progress=100,
            workspace_export_status="pending",
        )

        service._detect_deliverables_if_ready(
            db=object(),
            db_session=SimpleNamespace(
                id=uuid4(),
                status="completed",
                workspace_manifest_key=None,
            ),
            db_run=SimpleNamespace(id=uuid4(), user_message_id=123),
            callback=callback,
        )

        service._deliverable_detection.detect_for_completed_run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
