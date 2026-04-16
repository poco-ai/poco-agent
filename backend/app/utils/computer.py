import re


_SAFE_TOKEN = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_storage_token(value: str) -> str:
    """Return a storage-safe token for object keys (keeps ASCII, replaces others)."""

    token = (value or "").strip()
    token = _SAFE_TOKEN.sub("_", token)
    token = token.strip("._-")
    return token or "unknown"


def build_browser_screenshot_key(
    *, user_id: str, session_id: str, tool_use_id: str, run_id: str | None = None
) -> str:
    safe_session_id = sanitize_storage_token(session_id)
    safe_tool_use_id = sanitize_storage_token(tool_use_id)
    if run_id:
        safe_run_id = sanitize_storage_token(run_id)
        return (
            f"replays/{user_id}/{safe_session_id}/runs/{safe_run_id}"
            f"/browser/{safe_tool_use_id}.png"
        )
    return f"replays/{user_id}/{safe_session_id}/browser/{safe_tool_use_id}.png"
