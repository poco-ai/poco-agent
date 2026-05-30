import unittest
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models.agent_identity import AgentIdentity
from app.models.agent_persistent_state import AgentPersistentState
from app.models.persistent_runtime import PersistentRuntime
from app.services.persistent_runtime_service import PersistentRuntimeService


class PersistentRuntimeServiceTests(unittest.TestCase):
    def _build_agent(self) -> AgentIdentity:
        agent_identity = AgentIdentity(
            id=uuid.uuid4(),
            server_id=uuid.uuid4(),
            preset_id=7,
            handle="backend-specialist",
            display_name="Backend Specialist",
            description=None,
            visual_key="preset-visual-02",
            visibility="server",
            lifecycle_state="active",
            created_by="user-1",
            updated_by="user-1",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        agent_identity.persistent_state = AgentPersistentState(
            id=uuid.uuid4(),
            agent_identity_id=agent_identity.id,
            state_root_path="agents/state",
            profile_path="agents/state/profile.json",
            memory_path="agents/state/MEMORY.md",
            notes_dir_path="agents/state/notes",
            state_dir_path="agents/state/state",
            artifacts_dir_path="agents/state/artifacts",
            state_version=1,
            runtime_status="idle",
            active_session_id=None,
            active_task_id=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        return agent_identity

    def test_ensure_server_agent_runtime_creates_sleeping_runtime(self) -> None:
        db = MagicMock()
        agent_identity = self._build_agent()
        service = PersistentRuntimeService()

        with (
            patch(
                "app.services.persistent_runtime_service.PersistentRuntimeRepository.get_by_runtime_key",
                return_value=None,
            ),
            patch(
                "app.services.persistent_runtime_service.PersistentRuntimeRepository.create"
            ) as create_runtime,
        ):
            create_runtime.side_effect = lambda _db, runtime: runtime
            runtime = service.ensure_server_agent_runtime(
                db,
                agent_identity=agent_identity,
            )

        self.assertEqual(runtime.runtime_key, f"server_agent:{agent_identity.id}")
        self.assertEqual(runtime.owner_type, "server_agent")
        self.assertEqual(runtime.owner_id, agent_identity.id)
        self.assertEqual(runtime.agent_identity_id, agent_identity.id)
        self.assertEqual(runtime.lifecycle_state, "sleeping")
        self.assertEqual(
            runtime.idle_timeout_seconds,
            service.DEFAULT_SERVER_AGENT_IDLE_TIMEOUT_SECONDS,
        )
        self.assertEqual(
            runtime.warm_retention_seconds,
            service.DEFAULT_SERVER_AGENT_WARM_RETENTION_SECONDS,
        )

    def test_reserve_runtime_marks_running_and_keeps_resume_session(self) -> None:
        db = MagicMock()
        service = PersistentRuntimeService()
        agent_identity = self._build_agent()
        session_id = uuid.uuid4()
        channel_task_id = uuid.uuid4()
        runtime = PersistentRuntime(
            id=uuid.uuid4(),
            runtime_key=f"server_agent:{agent_identity.id}",
            owner_type="server_agent",
            owner_id=agent_identity.id,
            agent_identity_id=agent_identity.id,
            assignment_id=None,
            session_id=None,
            container_id=None,
            lifecycle_state="sleeping",
            auto_resume=True,
            idle_timeout_seconds=900,
            warm_retention_seconds=120,
            keepalive_until=None,
            last_activity_at=None,
            last_started_at=None,
            last_stopped_at=None,
            last_stop_reason=None,
            worker_id=None,
            browser_enabled=False,
            filesystem_fingerprint=None,
            metadata_json=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with patch.object(
            service,
            "get_by_runtime_key",
            return_value=runtime,
        ):
            result = service.reserve_runtime(
                db,
                runtime_key=runtime.runtime_key,
                session_id=session_id,
                channel_task_id=channel_task_id,
            )

        self.assertIs(result, runtime)
        self.assertEqual(runtime.lifecycle_state, "running")
        self.assertEqual(runtime.session_id, session_id)

    def test_release_runtime_for_session_moves_to_warm_idle(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        runtime = PersistentRuntime(
            id=uuid.uuid4(),
            runtime_key=f"server_agent:{uuid.uuid4()}",
            owner_type="server_agent",
            owner_id=uuid.uuid4(),
            agent_identity_id=uuid.uuid4(),
            assignment_id=None,
            session_id=session_id,
            container_id="runtime-1",
            lifecycle_state="running",
            auto_resume=True,
            idle_timeout_seconds=900,
            warm_retention_seconds=120,
            keepalive_until=None,
            last_activity_at=datetime.now(UTC) - timedelta(minutes=5),
            last_started_at=datetime.now(UTC) - timedelta(minutes=10),
            last_stopped_at=None,
            last_stop_reason=None,
            worker_id="worker-1",
            browser_enabled=False,
            filesystem_fingerprint=None,
            metadata_json=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.query.return_value.filter.return_value.first.return_value = runtime

        with (
            patch(
                "app.services.persistent_runtime_service.RunRepository.get_blocking_by_session",
                return_value=None,
            ),
            patch(
                "app.services.persistent_runtime_service.SessionQueueItemRepository.has_active_items",
                return_value=False,
            ),
            patch(
                "app.services.persistent_runtime_service.SessionRepository.get_by_id",
                return_value=SimpleNamespace(id=session_id, status="completed"),
            ),
        ):
            result = PersistentRuntimeService().release_runtime_for_session(
                db,
                session_id=session_id,
                callback_status="completed",
            )

        self.assertIs(result, runtime)
        self.assertEqual(runtime.lifecycle_state, "warm_idle")
        self.assertEqual(runtime.session_id, session_id)
        self.assertEqual(runtime.container_id, "runtime-1")

    def test_extend_keepalive_caps_duration_and_updates_timestamp(self) -> None:
        db = MagicMock()
        service = PersistentRuntimeService()
        runtime = PersistentRuntime(
            id=uuid.uuid4(),
            runtime_key=f"server_agent:{uuid.uuid4()}",
            owner_type="server_agent",
            owner_id=uuid.uuid4(),
            agent_identity_id=uuid.uuid4(),
            assignment_id=None,
            session_id=None,
            container_id=None,
            lifecycle_state="sleeping",
            auto_resume=True,
            idle_timeout_seconds=900,
            warm_retention_seconds=120,
            keepalive_until=None,
            last_activity_at=None,
            last_started_at=None,
            last_stopped_at=None,
            last_stop_reason=None,
            worker_id=None,
            browser_enabled=False,
            filesystem_fingerprint=None,
            metadata_json=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with patch.object(service, "get_by_runtime_key", return_value=runtime):
            result = service.extend_keepalive(
                db,
                runtime_key=runtime.runtime_key,
                duration_seconds=service.MAX_KEEPALIVE_SECONDS * 2,
            )

        self.assertIs(result, runtime)
        self.assertIsNotNone(runtime.keepalive_until)
        assert runtime.keepalive_until is not None
        remaining = runtime.keepalive_until - datetime.now(UTC)
        self.assertLessEqual(
            remaining.total_seconds(),
            service.MAX_KEEPALIVE_SECONDS + 5,
        )


if __name__ == "__main__":
    unittest.main()
