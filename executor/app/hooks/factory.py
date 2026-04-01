from dataclasses import dataclass

from app.core.callback import CallbackClient
from app.core.computer import ComputerClient
from app.hooks.base import AgentHook
from app.hooks.callback import CallbackHook
from app.hooks.computer import BrowserScreenshotHook
from app.hooks.run_snapshot import RunSnapshotHook
from app.hooks.todo import TodoHook
from app.hooks.workspace import WorkspaceHook


@dataclass(slots=True)
class HookDependencies:
    callback_client: CallbackClient | None
    computer_client: ComputerClient | None
    run_id: str | None


class HookFactory:
    @staticmethod
    def create(
        key: str,
        *,
        config: dict | None,
        dependencies: HookDependencies,
    ) -> AgentHook:
        _ = config or {}
        if key == "workspace":
            return WorkspaceHook()
        if key == "todo":
            return TodoHook()
        if key == "callback":
            if dependencies.callback_client is None:
                raise ValueError("callback_client is required for callback hook")
            return CallbackHook(client=dependencies.callback_client)
        if key == "browser_screenshot":
            if dependencies.computer_client is None:
                raise ValueError(
                    "computer_client is required for browser_screenshot hook"
                )
            return BrowserScreenshotHook(client=dependencies.computer_client)
        if key == "run_snapshot":
            return RunSnapshotHook(run_id=dependencies.run_id)
        raise ValueError(f"Unknown hook key: {key}")
