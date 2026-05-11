import json
import os
from pathlib import Path

from app.models.agent_identity import AgentIdentity
from app.models.agent_persistent_state import AgentPersistentState

DEFAULT_AGENT_STATE_BASE_DIR = Path(__file__).resolve().parents[3] / "tmp_workspace"
BOOTSTRAP_SCHEMA_VERSION = 1


def resolve_agent_state_base_dir() -> Path:
    configured_root = os.getenv("WORKSPACE_ROOT")
    if configured_root:
        return Path(configured_root)
    return DEFAULT_AGENT_STATE_BASE_DIR


def _write_if_missing_or_empty(path: Path, content: str) -> None:
    if path.exists() and path.is_file() and path.read_text(encoding="utf-8").strip():
        return
    path.write_text(content, encoding="utf-8")


def _build_profile_seed(
    agent_identity: AgentIdentity,
    persistent_state: AgentPersistentState,
) -> dict[str, object]:
    return {
        "schema_version": BOOTSTRAP_SCHEMA_VERSION,
        "kind": "poco_agent_private_state",
        "agent": {
            "id": str(agent_identity.id),
            "server_id": str(agent_identity.server_id),
            "handle": agent_identity.handle,
            "display_name": agent_identity.display_name,
            "description": agent_identity.description,
            "visibility": agent_identity.visibility,
            "lifecycle_state": agent_identity.lifecycle_state,
        },
        "preset": {
            "preset_id": agent_identity.preset_id,
            "visual_key": agent_identity.visual_key,
        },
        "runtime": {
            "mode": "persistent",
            "status": persistent_state.runtime_status,
            "state_version": persistent_state.state_version,
        },
        "paths": {
            "root": "/agent_state",
            "memory": "/agent_state/MEMORY.md",
            "notes": "/agent_state/notes",
            "state": "/agent_state/state",
            "artifacts": "/agent_state/artifacts",
        },
        "system_contract": {
            "profile_system_fields_locked": True,
            "temporary_runtime_can_write": False,
            "published_artifacts_are_private_by_default": True,
        },
        "agent_profile": {
            "summary": "",
            "working_preferences": [],
            "collaboration_notes": [],
        },
    }


def _build_memory_seed(agent_identity: AgentIdentity) -> str:
    return (
        f"# {agent_identity.display_name} long-term memory\n\n"
        "<!-- bootstrap: managed by Poco persistent state -->\n\n"
        "Use this file for durable facts, working preferences, and collaboration "
        "constraints that will still matter in later sessions.\n\n"
        "Do not store short-lived task chatter here. Put ephemeral execution state "
        "under `state/` or temporary notes under `notes/`.\n"
    )


def ensure_agent_state_bootstrap(
    *,
    agent_identity: AgentIdentity,
    persistent_state: AgentPersistentState,
    base_dir: Path | None = None,
) -> Path:
    base_dir = base_dir or resolve_agent_state_base_dir()
    root = base_dir / persistent_state.state_root_path
    notes_dir = root / "notes"
    state_dir = root / "state"
    artifacts_dir = root / "artifacts"

    notes_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    _write_if_missing_or_empty(
        root / "profile.json",
        json.dumps(
            _build_profile_seed(agent_identity, persistent_state),
            indent=2,
            ensure_ascii=True,
        )
        + "\n",
    )
    _write_if_missing_or_empty(root / "MEMORY.md", _build_memory_seed(agent_identity))
    _write_if_missing_or_empty(
        notes_dir / "active-context.md",
        "# Active context\n\nUse this file for working notes that may change during ongoing tasks.\n",
    )
    _write_if_missing_or_empty(
        state_dir / "task-state.json",
        json.dumps(
            {
                "schema_version": BOOTSTRAP_SCHEMA_VERSION,
                "active_task": None,
                "updated_at": None,
            },
            indent=2,
            ensure_ascii=True,
        )
        + "\n",
    )
    return root
