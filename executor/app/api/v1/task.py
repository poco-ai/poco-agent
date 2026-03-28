import logging
import json
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks
from fastapi import HTTPException
import httpx

from app.core.callback import CallbackClient
from app.core.callback import CallbackAuthenticationError
from app.core.computer import ComputerClient
from app.core.memory import MemoryClient
from app.core.user_input import UserInputClient
from app.core.engine import AgentExecutor
from app.hooks.base import AgentHook
from app.hooks.callback import CallbackHook
from app.hooks.computer import BrowserScreenshotHook
from app.hooks.run_snapshot import RunSnapshotHook
from app.hooks.todo import TodoHook
from app.hooks.workspace import WorkspaceHook
from app.core.observability.request_context import get_request_id, get_trace_id
from app.schemas.request import TaskRun

router = APIRouter(prefix="/v1/tasks")
logger = logging.getLogger(__name__)


def _build_task_context_env(
    *,
    session_id: str,
    callback_base_url: str,
    callback_token: str,
    task_context_path: Path,
) -> dict[str, str]:
    """Build runtime-only env vars for helper scripts running inside the task."""
    return {
        "POCO_SESSION_ID": session_id,
        "POCO_CALLBACK_BASE_URL": callback_base_url.rstrip("/"),
        "POCO_CALLBACK_TOKEN": callback_token,
        "POCO_TASK_CONTEXT_PATH": str(task_context_path),
    }


def _build_task_context_payload(
    *,
    session_id: str,
    callback_base_url: str,
) -> dict[str, str]:
    return {
        "session_id": session_id,
        "callback_base_url": callback_base_url.rstrip("/"),
    }


@router.post("/execute")
async def run_task(req: TaskRun, background_tasks: BackgroundTasks) -> dict:
    """Execute an agent task in the background.

    Args:
        req: Task execution request containing prompt, config, and callback URL.
        background_tasks: FastAPI background tasks manager.

    Returns:
        Accepted status with session ID.
    """
    callback_client = CallbackClient(
        callback_url=req.callback_url,
        callback_token=req.callback_token,
    )
    try:
        await callback_client.validate_auth()
    except (CallbackAuthenticationError, httpx.HTTPError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Callback authentication validation failed",
        ) from exc
    base_url = UserInputClient.resolve_base_url(
        callback_url=req.callback_url, callback_base_url=req.callback_base_url
    )
    user_input_client = UserInputClient(base_url=base_url)
    computer_client = ComputerClient(base_url=base_url)
    memory_client = (
        MemoryClient(base_url=base_url, session_id=req.session_id)
        if req.config.memory_enabled
        else None
    )
    hooks: list[AgentHook] = [
        WorkspaceHook(),
        TodoHook(),
        CallbackHook(client=callback_client),
    ]
    if req.config.browser_enabled:
        hooks.append(BrowserScreenshotHook(client=computer_client))
    hooks.append(RunSnapshotHook(run_id=req.run_id))
    executor = AgentExecutor(
        req.session_id,
        hooks,
        req.sdk_session_id,
        run_id=req.run_id,
        user_input_client=user_input_client,
        memory_client=memory_client,
        request_id=get_request_id(),
        trace_id=get_trace_id(),
    )

    cfg = req.config
    logger.info(
        "task_execute_accepted",
        extra={
            "session_id": req.session_id,
            "run_id": req.run_id,
            "resume": bool(req.sdk_session_id),
            "git_branch": cfg.git_branch,
            "has_repo_url": bool((cfg.repo_url or "").strip()),
            "memory_enabled": cfg.memory_enabled,
            "mcp_server_count": len(cfg.mcp_config or {}),
            "skill_count": len(cfg.skill_files or {}),
            "plugin_count": len(cfg.plugin_files or {}),
            "subagent_count": len(cfg.agents or {}),
            "input_count": len(cfg.input_files or []),
        },
    )

    async def execute_with_task_context() -> None:
        task_context_path = executor.workspace.root_path / ".poco-task-context.json"
        task_context_path.parent.mkdir(parents=True, exist_ok=True)
        callback_base_url = req.callback_base_url or base_url
        task_context_path.write_text(
            json.dumps(
                _build_task_context_payload(
                    session_id=req.session_id,
                    callback_base_url=callback_base_url,
                ),
                indent=2,
            ),
            encoding="utf-8",
        )
        try:
            config = req.config.model_copy(deep=True)
            config.env_overrides.update(
                _build_task_context_env(
                    session_id=req.session_id,
                    callback_base_url=callback_base_url,
                    callback_token=req.callback_token,
                    task_context_path=task_context_path,
                )
            )
            await executor.execute(
                prompt=req.prompt,
                config=config,
                permission_mode=req.permission_mode,
            )
        finally:
            task_context_path.unlink(missing_ok=True)

    background_tasks.add_task(
        execute_with_task_context,
    )

    return {"status": "accepted", "session_id": req.session_id}
