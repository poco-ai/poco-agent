import logging

from fastapi import APIRouter, BackgroundTasks

from app.core.callback import CallbackClient
from app.core.computer import ComputerClient
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
        callback_url=req.callback_url, callback_token=req.callback_token
    )
    base_url = UserInputClient.resolve_base_url(
        callback_url=req.callback_url, callback_base_url=req.callback_base_url
    )
    user_input_client = UserInputClient(base_url=base_url)
    computer_client = ComputerClient(base_url=base_url)
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
        user_input_client=user_input_client,
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
            "mcp_server_count": len(cfg.mcp_config or {}),
            "skill_count": len(cfg.skill_files or {}),
            "plugin_count": len(cfg.plugin_files or {}),
            "subagent_count": len(cfg.agents or {}),
            "input_count": len(cfg.input_files or []),
        },
    )

    background_tasks.add_task(
        executor.execute,
        prompt=req.prompt,
        config=req.config,
        permission_mode=req.permission_mode,
    )

    return {"status": "accepted", "session_id": req.session_id}
