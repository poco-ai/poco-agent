import asyncio
import logging
from datetime import datetime, timezone

from app.schemas.callback import AgentCallbackRequest, CallbackReceiveResponse
from app.services.backend_client import BackendClient
from app.services.workspace_export_service import (
    WorkspaceExportService,
    workspace_manager,
)

logger = logging.getLogger(__name__)


backend_client = BackendClient()
workspace_export_service = WorkspaceExportService()


class CallbackService:
    """Service layer for callback processing."""

    @staticmethod
    def _is_internal_mcp_server(name: str) -> bool:
        clean = (name or "").strip()
        return clean.startswith("__poco_")

    @staticmethod
    def _is_ignored_workspace_path(path: str) -> bool:
        """Check whether a workspace-relative path should be ignored.

        This keeps /sessions state_patch.workspace_state.file_changes consistent with the
        workspace export/list ignore policy in executor_manager WorkspaceManager.
        """
        clean = (path or "").replace("\\", "/").strip()
        if not clean:
            return True

        # Normalise common prefixes while keeping the path relative.
        while clean.startswith("./"):
            clean = clean[2:]
        clean = clean.lstrip("/")

        parts = [p for p in clean.split("/") if p]
        if not parts:
            return True
        # Defensive: never allow traversal-like paths to leak into state.
        if any(p in (".", "..") for p in parts):
            return True

        ignore_names = workspace_manager._ignore_names
        ignore_dot = workspace_manager.ignore_dot_files

        for part in parts:
            if part in ignore_names:
                return True
            if ignore_dot and part.startswith("."):
                return True
        return False

    @classmethod
    def _filter_state_patch(
        cls, callback: AgentCallbackRequest
    ) -> AgentCallbackRequest:
        state = callback.state_patch
        if not state:
            return callback

        updated_state = state

        # Hide built-in/internal MCP servers from the UI. End users should only see
        # explicitly configured MCP servers.
        if state.mcp_status:
            filtered_mcp = [
                m
                for m in state.mcp_status
                if not cls._is_internal_mcp_server(m.server_name)
            ]
            if len(filtered_mcp) != len(state.mcp_status):
                updated_state = updated_state.model_copy(
                    update={"mcp_status": filtered_mcp}
                )

        workspace_state = updated_state.workspace_state
        if not workspace_state or not workspace_state.file_changes:
            return (
                callback
                if updated_state is state
                else callback.model_copy(update={"state_patch": updated_state})
            )
        file_changes = workspace_state.file_changes

        filtered_changes = [
            fc for fc in file_changes if not cls._is_ignored_workspace_path(fc.path)
        ]
        if len(filtered_changes) == len(file_changes):
            return (
                callback
                if updated_state is state
                else callback.model_copy(update={"state_patch": updated_state})
            )

        total_added = sum(fc.added_lines for fc in filtered_changes)
        total_deleted = sum(fc.deleted_lines for fc in filtered_changes)

        new_workspace_state = workspace_state.model_copy(
            update={
                "file_changes": filtered_changes,
                "total_added_lines": total_added,
                "total_deleted_lines": total_deleted,
            }
        )
        updated_state = updated_state.model_copy(
            update={"workspace_state": new_workspace_state}
        )
        return callback.model_copy(update={"state_patch": updated_state})

    async def process_callback(
        self, callback: AgentCallbackRequest
    ) -> CallbackReceiveResponse:
        """Process agent execution callback from executor.

        Args:
            callback: Callback data from executor

        Returns:
            CallbackReceiveResponse with acknowledgment

        Raises:
            AppException: If callback forwarding to backend fails
        """
        from app.core.errors.error_codes import ErrorCode
        from app.core.errors.exceptions import AppException

        # Handle special message types (mcp_transition, permission_audit)
        new_message = callback.new_message
        if isinstance(new_message, dict):
            msg_type = new_message.get("type")
            if msg_type == "mcp_transition":
                await self._handle_mcp_transition(callback)
                return CallbackReceiveResponse(
                    status="received",
                    session_id=callback.session_id,
                    callback_status=callback.status,
                    progress=callback.progress,
                )
            if msg_type == "permission_audit":
                await self._handle_permission_audit(callback)
                return CallbackReceiveResponse(
                    status="received",
                    session_id=callback.session_id,
                    callback_status=callback.status,
                    progress=callback.progress,
                )

        # High-frequency callbacks: keep RUNNING as DEBUG; only completed/failed stay at INFO.
        summary_level = (
            logging.INFO
            if callback.status in ["completed", "failed"]
            else logging.DEBUG
        )
        logger.log(
            summary_level,
            "callback_received",
            extra={
                "session_id": callback.session_id,
                "status": callback.status,
                "progress": callback.progress,
                "sdk_session_id": callback.sdk_session_id,
                "run_id": callback.run_id,
            },
        )

        callback = self._filter_state_patch(callback)

        if callback.state_patch:
            state = callback.state_patch
            todo_count = len(state.todos) if state.todos else 0
            mcp_count = len(state.mcp_status) if state.mcp_status else 0
            file_count = (
                len(state.workspace_state.file_changes) if state.workspace_state else 0
            )
            logger.debug(
                "callback_state_patch_summary",
                extra={
                    "session_id": callback.session_id,
                    "todo_count": todo_count,
                    "mcp_count": mcp_count,
                    "file_change_count": file_count,
                },
            )

        try:
            payload_model = callback
            if callback.status in ["completed", "failed"]:
                payload_model = callback.model_copy(
                    update={"workspace_export_status": "pending"}
                )
            payload = payload_model.model_dump(mode="json")

            # Forward callback to backend
            backend_response = await backend_client.forward_callback(payload)

            if callback.status in ["completed", "failed"]:
                from app.scheduler.task_dispatcher import TaskDispatcher

                logger.info(
                    "task_terminal_callback_received",
                    extra={
                        "session_id": callback.session_id,
                        "status": callback.status,
                        "run_id": callback.run_id,
                        "session_status": backend_response.get("status"),
                    },
                )
                asyncio.create_task(self._export_and_forward(callback))
                session_status = str(backend_response.get("status") or "").strip()
                if session_status not in {"pending", "running"}:
                    await TaskDispatcher.on_task_complete(callback.session_id)
                else:
                    logger.info(
                        "task_cleanup_deferred",
                        extra={
                            "session_id": callback.session_id,
                            "status": callback.status,
                            "run_id": callback.run_id,
                            "session_status": session_status,
                        },
                    )

            return CallbackReceiveResponse(
                status="received",
                session_id=callback.session_id,
                callback_status=callback.status,
                progress=callback.progress,
            )

        except Exception:
            logger.exception(
                "callback_forward_failed",
                extra={"session_id": callback.session_id, "status": callback.status},
            )
            raise AppException(
                error_code=ErrorCode.CALLBACK_FORWARD_FAILED,
                message="Failed to forward callback to backend",
            )

    async def _handle_mcp_transition(self, callback: AgentCallbackRequest) -> None:
        """Forward MCP transition event to backend internal API."""
        new_message = callback.new_message
        if not isinstance(new_message, dict):
            return
        try:
            await backend_client.record_mcp_transition(
                run_id=callback.run_id or "",
                session_id=callback.session_id,
                server_name=str(new_message.get("server_name") or ""),
                to_state=str(new_message.get("to_state") or ""),
                event_source=str(new_message.get("event_source") or "executor"),
                error_message=new_message.get("error_message"),
                metadata=new_message.get("metadata"),
            )
        except Exception:
            logger.debug(
                "mcp_transition_forward_failed",
                extra={
                    "session_id": callback.session_id,
                    "run_id": callback.run_id,
                },
            )

    async def _handle_permission_audit(self, callback: AgentCallbackRequest) -> None:
        """Forward permission audit event to backend internal API."""
        new_message = callback.new_message
        if not isinstance(new_message, dict):
            return
        try:
            await backend_client.record_permission_audit(
                run_id=callback.run_id or "",
                session_id=callback.session_id,
                tool_name=str(new_message.get("tool_name") or ""),
                tool_input=new_message.get("tool_input"),
                policy_action=str(new_message.get("policy_action") or "allow"),
                policy_rule_id=new_message.get("policy_rule_id"),
                policy_reason=new_message.get("policy_reason"),
                audit_mode=bool(new_message.get("audit_mode", True)),
                context=new_message.get("context"),
            )
        except Exception:
            logger.debug(
                "permission_audit_forward_failed",
                extra={
                    "session_id": callback.session_id,
                    "run_id": callback.run_id,
                },
            )

    async def _export_and_forward(self, callback: AgentCallbackRequest) -> None:
        try:
            result = await asyncio.to_thread(
                workspace_export_service.export_workspace, callback.session_id
            )
        except Exception:
            logger.exception(
                "workspace_export_failed",
                extra={"session_id": callback.session_id},
            )
            result = None

        payload_model = AgentCallbackRequest(
            session_id=callback.session_id,
            run_id=callback.run_id,
            time=datetime.now(timezone.utc),
            status=callback.status,
            progress=100 if callback.status == "completed" else callback.progress,
            error_message=callback.error_message,
            sdk_session_id=callback.sdk_session_id,
            workspace_files_prefix=result.workspace_files_prefix if result else None,
            workspace_manifest_key=result.workspace_manifest_key if result else None,
            workspace_archive_key=result.workspace_archive_key if result else None,
            workspace_export_status=(
                result.workspace_export_status if result else "failed"
            ),
        )
        payload = payload_model.model_dump(mode="json")

        try:
            await backend_client.forward_callback(payload)
        except Exception:
            logger.exception(
                "workspace_export_callback_forward_failed",
                extra={"session_id": callback.session_id},
            )
