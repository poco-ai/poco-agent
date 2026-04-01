from typing import Any

from app.hooks.base import AgentHook, ExecutionContext


_HOOK_PHASE_ORDER = {
    "setup": 0,
    "pre_query": 1,
    "message": 2,
    "error": 3,
    "teardown": 4,
}


class HookManager:
    def __init__(self, hooks: list[AgentHook]):
        # Sort by phase first, then by order within each phase
        self.hooks = sorted(
            hooks,
            key=lambda hook: (
                _HOOK_PHASE_ORDER.get(
                    str(
                        getattr(hook, "hook_spec", {}).get("phase", "message")
                        if isinstance(getattr(hook, "hook_spec", {}), dict)
                        else "message"
                    ),
                    99,
                ),
                int(
                    getattr(hook, "hook_spec", {}).get("order", 100)
                    if isinstance(getattr(hook, "hook_spec", {}), dict)
                    else 100
                ),
            ),
        )

    async def run_on_setup(self, context: ExecutionContext):
        for hook in self.hooks:
            await hook.on_setup(context)

    async def run_on_response(self, context: ExecutionContext, message: Any):
        for hook in self.hooks:
            await hook.on_agent_response(context, message)

    async def run_on_teardown(self, context: ExecutionContext):
        for hook in reversed(self.hooks):
            await hook.on_teardown(context)

    async def run_on_error(self, context: ExecutionContext, error: Exception):
        for hook in self.hooks:
            await hook.on_error(context, error)
