from pathlib import Path

from app.api.v1.task import _build_task_context_env, _build_task_context_payload


def test_build_task_context_payload_omits_callback_token() -> None:
    payload = _build_task_context_payload(
        session_id="session-123",
        callback_base_url="http://executor-manager:8080",
    )

    assert payload["session_id"] == "session-123"
    assert payload["callback_base_url"] == "http://executor-manager:8080"
    assert "callback_token" not in payload


def test_build_task_context_env_keeps_runtime_token() -> None:
    env = _build_task_context_env(
        session_id="session-123",
        callback_base_url="http://executor-manager:8080",
        callback_token="secret-token",
        task_context_path=Path("/workspace/.poco-task-context.json"),
    )

    assert env["POCO_CALLBACK_TOKEN"] == "secret-token"
