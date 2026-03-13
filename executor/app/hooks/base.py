from abc import ABC
from typing import Any

from app.schemas.state import AgentCurrentState


class ExecutionContext:
    def __init__(self, session_id: str, cwd: str, *, run_id: str | None = None):
        self.session_id = session_id
        self.cwd = cwd
        self.run_id = run_id
        self.current_state = AgentCurrentState()


class AgentHook(ABC):
    async def on_setup(self, context: ExecutionContext):
        pass

    async def on_agent_response(self, context: ExecutionContext, message: Any):
        pass

    async def on_teardown(self, context: ExecutionContext):
        pass

    async def on_error(self, context: ExecutionContext, error: Exception):
        pass
