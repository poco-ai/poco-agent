from typing import Any, Optional

from app.core.callback import CallbackClient
from app.hooks.base import AgentHook, ExecutionContext
from app.schemas.callback import AgentCallbackRequest
from app.schemas.enums import CallbackStatus, TodoStatus
from app.utils.serializer import serialize_message


class CallbackHook(AgentHook):
    def __init__(self, client: CallbackClient):
        self.client = client
        self.execution_error: Optional[Exception] = None

    def _build_report(
        self,
        context: ExecutionContext,
        status: str,
        progress: int,
        new_message: Optional[Any] = None,
    ) -> AgentCallbackRequest:
        return AgentCallbackRequest(
            session_id=context.session_id,
            status=status,
            progress=progress,
            new_message=serialize_message(new_message),
            state_patch=context.current_state,
        )

    def _calculate_progress(self, todos) -> int:
        if not todos:
            return 0
        completed = len([t for t in todos if t.status == TodoStatus.COMPLETED])
        return int((completed / len(todos)) * 100)

    async def on_agent_response(self, context: ExecutionContext, message: Any):
        await self.client.send(
            self._build_report(
                context=context,
                status=CallbackStatus.RUNNING,
                progress=self._calculate_progress(context.current_state.todos),
                new_message=message,
            )
        )

    async def on_teardown(self, context: ExecutionContext):
        status = (
            CallbackStatus.COMPLETED
            if self.execution_error is None
            else CallbackStatus.FAILED
        )
        progress = 100

        await self.client.send(
            self._build_report(
                context=context,
                status=status,
                progress=progress,
            )
        )

    async def on_error(self, context: ExecutionContext, error: Exception):
        self.execution_error = error
