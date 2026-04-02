import logging
from typing import Any, Optional

from claude_agent_sdk.types import ResultMessage, SystemMessage

from app.core.callback import CallbackClient
from app.hooks.base import AgentHook, ExecutionContext
from app.schemas.callback import AgentCallbackRequest
from app.schemas.enums import CallbackStatus, TodoStatus
from app.utils.serializer import serialize_message

logger = logging.getLogger(__name__)


class CallbackHook(AgentHook):
    def __init__(self, client: CallbackClient):
        self.client = client
        self.execution_error: Optional[Exception] = None
        self.sdk_session_id: Optional[str] = None

    def _build_report(
        self,
        context: ExecutionContext,
        status: str,
        progress: int,
        new_message: Optional[Any] = None,
        error_message: str | None = None,
    ) -> AgentCallbackRequest:
        return AgentCallbackRequest(
            session_id=context.session_id,
            run_id=context.run_id,
            status=status,
            progress=progress,
            error_message=error_message,
            new_message=serialize_message(new_message),
            state_patch=context.current_state,
            sdk_session_id=self.sdk_session_id,
        )

    def _calculate_progress(self, todos) -> int:
        if not todos:
            return 0
        completed = len([t for t in todos if t.status == TodoStatus.COMPLETED])
        return int((completed / len(todos)) * 100)

    async def on_agent_response(self, context: ExecutionContext, message: Any):
        if isinstance(message, SystemMessage) and message.subtype == "init":
            data = message.data.get("data", {})
            if isinstance(data, dict) and "session_id" in data:
                self.sdk_session_id = data["session_id"]
        elif isinstance(message, ResultMessage):
            self.sdk_session_id = message.session_id

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

        error_message: str | None = None
        if self.execution_error is not None:
            detail = f"{type(self.execution_error).__name__}: {self.execution_error}"
            if len(detail) > 2000:
                detail = detail[:2000] + "..."
            error_message = detail

        await self.client.send(
            self._build_report(
                context=context,
                status=status,
                progress=progress,
                error_message=error_message,
            )
        )

    async def on_error(self, context: ExecutionContext, error: Exception):
        self.execution_error = error

    async def record_permission_event(
        self,
        context: ExecutionContext,
        *,
        tool_name: str,
        tool_input: dict[str, Any] | None = None,
        policy_action: str = "allow",
        policy_rule_id: str = "",
        policy_reason: str = "",
        audit_mode: bool = True,
    ) -> None:
        """Fire-and-forget permission audit event to executor-manager callback."""
        payload = AgentCallbackRequest(
            session_id=context.session_id,
            run_id=context.run_id,
            status=CallbackStatus.RUNNING,
            progress=0,
            new_message={
                "type": "permission_audit",
                "tool_name": tool_name,
                "tool_input": tool_input,
                "policy_action": policy_action,
                "policy_rule_id": policy_rule_id,
                "policy_reason": policy_reason,
                "audit_mode": audit_mode,
            },
        )
        try:
            await self.client.send(payload)
        except Exception:
            logger.debug("Permission audit event send failed (fire-and-forget)")

    async def on_mcp_state_change(
        self,
        context: ExecutionContext,
        *,
        server_name: str,
        to_state: str,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Fire-and-forget MCP transition event to executor-manager callback."""
        payload = AgentCallbackRequest(
            session_id=context.session_id,
            run_id=context.run_id,
            status=CallbackStatus.RUNNING,
            progress=0,
            new_message={
                "type": "mcp_transition",
                "server_name": server_name,
                "to_state": to_state,
                "event_source": "executor",
                "error_message": error_message,
                "metadata": metadata,
            },
        )
        try:
            await self.client.send(payload)
        except Exception:
            logger.debug("MCP transition event send failed (fire-and-forget)")
