import json
import tempfile
import unittest
import uuid
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from app.models.agent_identity import AgentIdentity
from app.models.agent_persistent_state import AgentPersistentState
from app.services.agent_state_bootstrap_service import ensure_agent_state_bootstrap


class AgentStateBootstrapServiceTests(unittest.TestCase):
    def _build_agent(self) -> tuple[AgentIdentity, AgentPersistentState]:
        agent_id = uuid.uuid4()
        server_id = uuid.uuid4()
        agent = AgentIdentity(
            id=agent_id,
            server_id=server_id,
            preset_id=7,
            handle="backend-specialist",
            display_name="Backend Specialist",
            description="Reviews backend changes.",
            visual_key="preset-visual-02",
            visibility="server",
            lifecycle_state="active",
            created_by="user-1",
            updated_by="user-1",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        persistent_state = AgentPersistentState(
            id=uuid.uuid4(),
            agent_identity_id=agent_id,
            state_root_path=f"agents/{agent_id}",
            profile_path=f"agents/{agent_id}/profile.json",
            memory_path=f"agents/{agent_id}/MEMORY.md",
            notes_dir_path=f"agents/{agent_id}/notes",
            state_dir_path=f"agents/{agent_id}/state",
            artifacts_dir_path=f"agents/{agent_id}/artifacts",
            state_version=1,
            runtime_status="idle",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        return agent, persistent_state

    def test_ensure_agent_state_bootstrap_writes_seeded_files(self) -> None:
        agent, persistent_state = self._build_agent()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = ensure_agent_state_bootstrap(
                agent_identity=agent,
                persistent_state=persistent_state,
                base_dir=Path(temp_dir),
            )

            profile_data = json.loads(
                (root / "profile.json").read_text(encoding="utf-8")
            )
            self.assertEqual(profile_data["schema_version"], 1)
            self.assertEqual(profile_data["agent"]["handle"], "backend-specialist")
            self.assertEqual(
                profile_data["agent"]["display_name"], "Backend Specialist"
            )
            self.assertEqual(profile_data["preset"]["preset_id"], 7)
            self.assertEqual(profile_data["runtime"]["mode"], "persistent")
            self.assertEqual(profile_data["paths"]["memory"], "/agent_state/MEMORY.md")

            memory_text = (root / "MEMORY.md").read_text(encoding="utf-8")
            self.assertIn("Backend Specialist", memory_text)
            self.assertIn("long-term memory", memory_text)

            notes_text = (root / "notes" / "active-context.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("working notes", notes_text)

            task_state = json.loads(
                (root / "state" / "task-state.json").read_text(encoding="utf-8")
            )
            self.assertEqual(task_state["schema_version"], 1)
            self.assertIsNone(task_state["active_task"])

    def test_ensure_agent_state_bootstrap_preserves_non_empty_files(self) -> None:
        agent, persistent_state = self._build_agent()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / persistent_state.state_root_path
            (root / "notes").mkdir(parents=True, exist_ok=True)
            (root / "state").mkdir(parents=True, exist_ok=True)
            (root / "artifacts").mkdir(parents=True, exist_ok=True)
            (root / "MEMORY.md").write_text("custom memory", encoding="utf-8")
            (root / "profile.json").write_text(
                json.dumps({"custom": True}), encoding="utf-8"
            )

            ensure_agent_state_bootstrap(
                agent_identity=agent,
                persistent_state=persistent_state,
                base_dir=Path(temp_dir),
            )

            self.assertEqual(
                (root / "MEMORY.md").read_text(encoding="utf-8"), "custom memory"
            )
            self.assertEqual(
                json.loads((root / "profile.json").read_text(encoding="utf-8")),
                {"custom": True},
            )

    def test_ensure_agent_state_bootstrap_uses_workspace_root_env(self) -> None:
        agent, persistent_state = self._build_agent()

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict("os.environ", {"WORKSPACE_ROOT": temp_dir}):
                root = ensure_agent_state_bootstrap(
                    agent_identity=agent,
                    persistent_state=persistent_state,
                )

            self.assertEqual(root, Path(temp_dir) / persistent_state.state_root_path)
            self.assertTrue((root / "profile.json").exists())


if __name__ == "__main__":
    unittest.main()
