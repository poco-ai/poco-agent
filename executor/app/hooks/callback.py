from typing import Any, Optional

from app.core.callback import CallbackClient
from app.hooks.base import AgentHook, ExecutionContext
from app.schemas.callback import AgentReportCallback
from app.schemas.enums import CallbackStatus, TodoStatus
from app.utils.serializer import serialize_message


class CallbackHook(AgentHook):
    def __init__(self, client: CallbackClient):
        self.client = client

    def _build_report(
        self,
        context: ExecutionContext,
        status: str,
        progress: int,
        new_message: Optional[Any] = None,
    ) -> AgentReportCallback:
        return AgentReportCallback(
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
