import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import httpx
from claude_agent_sdk import create_sdk_mcp_server, tool
from claude_agent_sdk.types import McpSdkServerConfig

from app.core.observability.request_context import (
    generate_request_id,
    generate_trace_id,
    get_request_id,
    get_trace_id,
)

CHANNEL_RUNTIME_MCP_SERVER_KEY = "__poco_channel_runtime"
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f-\x9f]+")


@dataclass
class DownloadedArtifact:
    artifact_id: str | None
    logical_path: str | None
    display_name: str
    mime_type: str | None
    size_bytes: int | None
    content: bytes


@dataclass
class StagedArtifact:
    artifact_id: str | None
    logical_path: str | None
    display_name: str
    local_path: str
    mime_type: str | None
    size_bytes: int | None


def _sanitize_stage_name(raw_name: str | None) -> str:
    clean = (raw_name or "").strip().replace("\\", "/")
    clean = clean.split("/")[-1].strip()
    clean = _CONTROL_CHARS.sub("", clean)
    return clean or "artifact.bin"


def _stage_directory_name(downloaded: DownloadedArtifact) -> str:
    if downloaded.artifact_id:
        return downloaded.artifact_id
    seed = downloaded.logical_path or downloaded.display_name or "artifact"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def stage_downloaded_artifact(
    downloaded: DownloadedArtifact,
    *,
    workspace_root: Path,
) -> StagedArtifact:
    inputs_root = workspace_root / "inputs" / "channel-artifacts"
    target_dir = inputs_root / _stage_directory_name(downloaded)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / _sanitize_stage_name(downloaded.display_name)
    target_path.write_bytes(downloaded.content)
    return StagedArtifact(
        artifact_id=downloaded.artifact_id,
        logical_path=downloaded.logical_path,
        display_name=downloaded.display_name,
        local_path=str(target_path),
        mime_type=downloaded.mime_type,
        size_bytes=downloaded.size_bytes,
    )


class ChannelRuntimeClient:
    def __init__(
        self,
        base_url: str,
        session_id: str,
        callback_token: str = "",
        timeout: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.session_id = session_id
        self.callback_token = callback_token
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {
            "X-Request-ID": get_request_id() or generate_request_id(),
            "X-Trace-ID": get_trace_id() or generate_trace_id(),
        }
        if self.callback_token:
            headers["Authorization"] = f"Bearer {self.callback_token}"
        return headers

    async def _request(self, path: str, payload: dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}{path}",
                json={"session_id": self.session_id, **payload},
                headers=self._headers(),
            )

        body = response.json()
        if not isinstance(body, dict):
            raise RuntimeError("Invalid channel runtime response")
        if response.is_error:
            raise RuntimeError(str(body.get("message") or response.reason_phrase))
        if body.get("code") != 0:
            raise RuntimeError(str(body.get("message") or "Channel runtime error"))
        return body.get("data")

    async def read_messages(
        self,
        *,
        message_ids: list[str] | None = None,
        thread_root_message_id: str | None = None,
        anchor_message_id: str | None = None,
        direction: str | None = None,
        include_anchor: bool = True,
        read_all: bool = False,
        limit: int | None = None,
    ) -> Any:
        return await self._request(
            "/api/v1/agent-channel-runtime/messages/read",
            {
                "message_ids": message_ids or [],
                "thread_root_message_id": thread_root_message_id,
                "anchor_message_id": anchor_message_id,
                "direction": direction,
                "include_anchor": include_anchor,
                "read_all": read_all,
                "limit": limit,
            },
        )

    async def list_agents(self) -> Any:
        return await self._request("/api/v1/agent-channel-runtime/agents/list", {})

    async def request_collaboration(
        self,
        *,
        agent_handle: str,
        request_text: str,
        reason: str | None,
        mode: str,
        thread_root_message_id: str | None,
        reference_message_ids: list[str],
        reference_artifact_ids: list[str],
    ) -> Any:
        return await self._request(
            "/api/v1/agent-channel-runtime/collaboration/request",
            {
                "agent_handle": agent_handle,
                "request_text": request_text,
                "reason": reason,
                "mode": mode,
                "thread_root_message_id": thread_root_message_id,
                "reference_message_ids": reference_message_ids,
                "reference_artifact_ids": reference_artifact_ids,
            },
        )

    async def list_artifacts(self) -> Any:
        return await self._request("/api/v1/agent-channel-artifacts/list", {})

    async def read_artifact(
        self,
        *,
        artifact_id: str | None,
        logical_path: str | None,
        max_bytes: int | None,
    ) -> Any:
        return await self._request(
            "/api/v1/agent-channel-artifacts/read",
            {
                "artifact_id": artifact_id,
                "logical_path": logical_path,
                "max_bytes": max_bytes,
            },
        )

    async def search_artifacts(
        self,
        *,
        query: str,
        limit: int | None,
        include_content: bool,
    ) -> Any:
        return await self._request(
            "/api/v1/agent-channel-artifacts/search",
            {
                "query": query,
                "limit": limit,
                "include_content": include_content,
            },
        )

    async def read_artifact_text(
        self,
        *,
        artifact_id: str | None,
        logical_path: str | None,
        start_char: int,
        max_chars: int,
    ) -> Any:
        return await self._request(
            "/api/v1/agent-channel-artifacts/text",
            {
                "artifact_id": artifact_id,
                "logical_path": logical_path,
                "start_char": start_char,
                "max_chars": max_chars,
            },
        )

    async def download_artifact(
        self,
        *,
        artifact_id: str | None,
        logical_path: str | None,
    ) -> DownloadedArtifact:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/agent-channel-artifacts/download",
                json={
                    "session_id": self.session_id,
                    "artifact_id": artifact_id,
                    "logical_path": logical_path,
                },
                headers=self._headers(),
            )

        if response.is_error:
            message = response.text or response.reason_phrase
            try:
                body = response.json()
            except ValueError:
                body = None
            if isinstance(body, dict):
                message = str(body.get("message") or message)
            raise RuntimeError(message)

        size_header = response.headers.get("x-artifact-size-bytes")
        size_bytes = int(size_header) if size_header and size_header.isdigit() else None
        return DownloadedArtifact(
            artifact_id=response.headers.get("x-artifact-id"),
            logical_path=response.headers.get("x-artifact-logical-path"),
            display_name=response.headers.get("x-artifact-display-name")
            or "artifact.bin",
            mime_type=response.headers.get("x-artifact-mime-type")
            or response.headers.get("content-type"),
            size_bytes=size_bytes,
            content=response.content,
        )

    async def create_task(
        self,
        *,
        title: str,
        description: str | None,
        priority: str | None,
    ) -> Any:
        return await self._request(
            "/api/v1/agent-channel-tasks/create",
            {"title": title, "description": description, "priority": priority},
        )

    async def list_tasks(
        self,
        *,
        status: str | None,
        limit: int | None,
    ) -> Any:
        return await self._request(
            "/api/v1/agent-channel-tasks/list",
            {"status": status, "limit": limit},
        )

    async def read_task(self, *, task_id: str) -> Any:
        return await self._request(
            "/api/v1/agent-channel-tasks/read",
            {"task_id": task_id},
        )

    async def update_task_status(
        self,
        *,
        task_id: str,
        status: str,
        position: int,
    ) -> Any:
        return await self._request(
            "/api/v1/agent-channel-tasks/status",
            {"task_id": task_id, "status": status, "position": position},
        )

    async def claim_task(self, *, task_id: str) -> Any:
        return await self._request(
            "/api/v1/agent-channel-tasks/claim",
            {"task_id": task_id},
        )

    async def comment_on_task(self, *, task_id: str, text: str) -> Any:
        return await self._request(
            "/api/v1/agent-channel-tasks/comment",
            {"task_id": task_id, "text": text},
        )

    async def add_message_reaction(self, *, message_id: str, emoji: str) -> Any:
        return await self._request(
            "/api/v1/agent-channel-runtime/reactions/add",
            {"message_id": message_id, "emoji": emoji},
        )

    async def remove_message_reaction(self, *, message_id: str, emoji: str) -> Any:
        return await self._request(
            "/api/v1/agent-channel-runtime/reactions/remove",
            {"message_id": message_id, "emoji": emoji},
        )


def _format_tool_result(title: str, data: Any) -> dict[str, Any]:
    body = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    return {"content": [{"type": "text", "text": f"{title}\n{body}"}]}


def _format_tool_error(title: str, error: str, *, code: str) -> dict[str, Any]:
    return _format_tool_result(f"{title}_error", {"error": error, "code": code})


async def _run_tool(title: str, operation) -> dict[str, Any]:
    try:
        result = await operation
    except Exception as exc:
        return _format_tool_error(title, str(exc), code="runtime_error")
    return _format_tool_result(title, result)


def create_channel_runtime_mcp_server(
    runtime_client: ChannelRuntimeClient,
    *,
    workspace_root: str = "/workspace",
) -> McpSdkServerConfig:
    @tool(
        "list_channel_artifacts",
        "List read-only published artifacts available in the current channel",
        {},
    )
    async def list_channel_artifacts(args: dict[str, Any]) -> dict[str, Any]:
        _ = args
        return await _run_tool(
            "list_channel_artifacts",
            runtime_client.list_artifacts(),
        )

    @tool(
        "read_channel_artifact",
        "Read one published channel artifact by artifact_id or logical_path",
        {"artifact_id": str, "logical_path": str, "max_bytes": int},
    )
    async def read_channel_artifact(args: dict[str, Any]) -> dict[str, Any]:
        artifact_id = args.get("artifact_id")
        logical_path = args.get("logical_path")
        if (not isinstance(artifact_id, str) or not artifact_id.strip()) and (
            not isinstance(logical_path, str) or not logical_path.strip()
        ):
            return _format_tool_error(
                "read_channel_artifact",
                "artifact_id or logical_path must be provided",
                code="invalid_arguments",
            )
        if isinstance(logical_path, str) and logical_path.strip().startswith(
            "/workspace"
        ):
            return _format_tool_error(
                "read_channel_artifact",
                "logical_path is a published artifact identifier, not a /workspace path",
                code="invalid_arguments",
            )
        max_bytes = args.get("max_bytes")
        return await _run_tool(
            "read_channel_artifact",
            runtime_client.read_artifact(
                artifact_id=artifact_id.strip()
                if isinstance(artifact_id, str)
                else None,
                logical_path=(
                    logical_path.strip() if isinstance(logical_path, str) else None
                ),
                max_bytes=max_bytes if isinstance(max_bytes, int) else None,
            ),
        )

    @tool(
        "search_channel_artifacts",
        "Search current channel artifacts by name, logical path, source, or text",
        {"query": str, "limit": int, "include_content": bool},
    )
    async def search_channel_artifacts(args: dict[str, Any]) -> dict[str, Any]:
        query = args.get("query")
        if not isinstance(query, str) or not query.strip():
            return _format_tool_error(
                "search_channel_artifacts",
                "query must be a non-empty string",
                code="invalid_arguments",
            )
        limit = args.get("limit")
        include_content = args.get("include_content")
        return await _run_tool(
            "search_channel_artifacts",
            runtime_client.search_artifacts(
                query=query.strip(),
                limit=limit if isinstance(limit, int) else None,
                include_content=(
                    include_content if isinstance(include_content, bool) else False
                ),
            ),
        )

    @tool(
        "read_channel_artifact_text",
        "Read extracted text from a published channel artifact without staging the original file",
        {"artifact_id": str, "logical_path": str, "start_char": int, "max_chars": int},
    )
    async def read_channel_artifact_text(args: dict[str, Any]) -> dict[str, Any]:
        artifact_id = args.get("artifact_id")
        logical_path = args.get("logical_path")
        if (not isinstance(artifact_id, str) or not artifact_id.strip()) and (
            not isinstance(logical_path, str) or not logical_path.strip()
        ):
            return _format_tool_error(
                "read_channel_artifact_text",
                "artifact_id or logical_path must be provided",
                code="invalid_arguments",
            )
        start_char = args.get("start_char")
        max_chars = args.get("max_chars")
        return await _run_tool(
            "read_channel_artifact_text",
            runtime_client.read_artifact_text(
                artifact_id=artifact_id.strip()
                if isinstance(artifact_id, str)
                else None,
                logical_path=(
                    logical_path.strip() if isinstance(logical_path, str) else None
                ),
                start_char=start_char if isinstance(start_char, int) else 0,
                max_chars=max_chars if isinstance(max_chars, int) else 12000,
            ),
        )

    @tool(
        "stage_channel_artifact_to_workspace",
        "Download a published channel artifact into the current workspace for local processing and return the local path",
        {"artifact_id": str, "logical_path": str},
    )
    async def stage_channel_artifact_to_workspace(
        args: dict[str, Any],
    ) -> dict[str, Any]:
        artifact_id = args.get("artifact_id")
        logical_path = args.get("logical_path")
        if (not isinstance(artifact_id, str) or not artifact_id.strip()) and (
            not isinstance(logical_path, str) or not logical_path.strip()
        ):
            return _format_tool_error(
                "stage_channel_artifact_to_workspace",
                "artifact_id or logical_path must be provided",
                code="invalid_arguments",
            )
        try:
            downloaded = await runtime_client.download_artifact(
                artifact_id=artifact_id.strip()
                if isinstance(artifact_id, str)
                else None,
                logical_path=(
                    logical_path.strip() if isinstance(logical_path, str) else None
                ),
            )
            staged = stage_downloaded_artifact(
                downloaded,
                workspace_root=Path(workspace_root),
            )
        except Exception as exc:
            return _format_tool_error(
                "stage_channel_artifact_to_workspace",
                str(exc),
                code="runtime_error",
            )
        return _format_tool_result(
            "stage_channel_artifact_to_workspace",
            asdict(staged),
        )

    @tool(
        "read_channel_messages",
        "Read full messages or thread replies from the current channel",
        {
            "message_ids": list,
            "thread_root_message_id": str,
            "anchor_message_id": str,
            "direction": str,
            "include_anchor": bool,
            "read_all": bool,
            "limit": int,
        },
    )
    async def read_channel_messages(args: dict[str, Any]) -> dict[str, Any]:
        raw_message_ids = args.get("message_ids")
        if isinstance(raw_message_ids, list):
            message_ids = [
                item.strip()
                for item in raw_message_ids
                if isinstance(item, str) and item.strip()
            ]
        elif isinstance(raw_message_ids, str) and raw_message_ids.strip():
            message_ids = [raw_message_ids.strip()]
        else:
            message_ids = []
        thread_root_message_id = args.get("thread_root_message_id")
        thread_root_message_id = (
            thread_root_message_id.strip()
            if isinstance(thread_root_message_id, str)
            and thread_root_message_id.strip()
            else None
        )
        anchor_message_id = args.get("anchor_message_id")
        anchor_message_id = (
            anchor_message_id.strip()
            if isinstance(anchor_message_id, str) and anchor_message_id.strip()
            else None
        )
        direction = args.get("direction")
        direction = (
            direction.strip().lower()
            if isinstance(direction, str) and direction.strip()
            else None
        )
        if direction is not None and direction not in {"before", "after"}:
            return _format_tool_error(
                "read_channel_messages",
                "direction must be 'before' or 'after'",
                code="invalid_arguments",
            )
        include_anchor = args.get("include_anchor")
        read_all = args.get("read_all")
        limit = args.get("limit")
        return await _run_tool(
            "read_channel_messages",
            runtime_client.read_messages(
                message_ids=message_ids,
                thread_root_message_id=thread_root_message_id,
                anchor_message_id=anchor_message_id,
                direction=direction,
                include_anchor=include_anchor
                if isinstance(include_anchor, bool)
                else True,
                read_all=read_all if isinstance(read_all, bool) else False,
                limit=limit if isinstance(limit, int) else None,
            ),
        )

    @tool(
        "list_channel_agents",
        "List active agents available for collaboration in the current channel",
        {},
    )
    async def list_channel_agents(args: dict[str, Any]) -> dict[str, Any]:
        _ = args
        return await _run_tool("list_channel_agents", runtime_client.list_agents())

    @tool(
        "request_agent_collaboration",
        "Explicitly request collaboration from another active agent in this channel",
        {
            "agent_handle": str,
            "request_text": str,
            "reason": str,
            "mode": str,
            "thread_root_message_id": str,
            "reference_message_ids": list,
            "reference_artifact_ids": list,
        },
    )
    async def request_agent_collaboration(args: dict[str, Any]) -> dict[str, Any]:
        agent_handle = args.get("agent_handle")
        request_text = args.get("request_text")
        if not isinstance(agent_handle, str) or not agent_handle.strip():
            return _format_tool_error(
                "request_agent_collaboration",
                "agent_handle must be a non-empty string",
                code="invalid_arguments",
            )
        if not isinstance(request_text, str) or not request_text.strip():
            return _format_tool_error(
                "request_agent_collaboration",
                "request_text must be a non-empty string",
                code="invalid_arguments",
            )
        mode = args.get("mode")
        mode = mode.strip() if isinstance(mode, str) and mode.strip() else "consult"
        if mode not in {"consult", "handoff"}:
            return _format_tool_error(
                "request_agent_collaboration",
                "mode must be consult or handoff",
                code="invalid_arguments",
            )
        reason = args.get("reason")
        thread_root_message_id = args.get("thread_root_message_id")
        reference_message_ids = args.get("reference_message_ids")
        reference_artifact_ids = args.get("reference_artifact_ids")
        return await _run_tool(
            "request_agent_collaboration",
            runtime_client.request_collaboration(
                agent_handle=agent_handle.strip(),
                request_text=request_text.strip(),
                reason=reason.strip()
                if isinstance(reason, str) and reason.strip()
                else None,
                mode=mode,
                thread_root_message_id=(
                    thread_root_message_id.strip()
                    if isinstance(thread_root_message_id, str)
                    and thread_root_message_id.strip()
                    else None
                ),
                reference_message_ids=[
                    item.strip()
                    for item in reference_message_ids
                    if isinstance(item, str) and item.strip()
                ]
                if isinstance(reference_message_ids, list)
                else [],
                reference_artifact_ids=[
                    item.strip()
                    for item in reference_artifact_ids
                    if isinstance(item, str) and item.strip()
                ]
                if isinstance(reference_artifact_ids, list)
                else [],
            ),
        )

    @tool(
        "list_channel_tasks",
        "List structured tasks in the current server channel",
        {"status": str, "limit": int},
    )
    async def list_channel_tasks(args: dict[str, Any]) -> dict[str, Any]:
        status = args.get("status")
        status = status.strip() if isinstance(status, str) and status.strip() else None
        if status is not None and status not in {
            "todo",
            "in_progress",
            "in_review",
            "done",
        }:
            return _format_tool_error(
                "list_channel_tasks",
                "status must be todo, in_progress, in_review, or done",
                code="invalid_arguments",
            )
        limit = args.get("limit")
        return await _run_tool(
            "list_channel_tasks",
            runtime_client.list_tasks(
                status=status,
                limit=limit if isinstance(limit, int) else None,
            ),
        )

    @tool(
        "read_channel_task",
        "Read one structured task in the current server channel",
        {"task_id": str},
    )
    async def read_channel_task(args: dict[str, Any]) -> dict[str, Any]:
        task_id = args.get("task_id")
        if not isinstance(task_id, str) or not task_id.strip():
            return _format_tool_error(
                "read_channel_task",
                "task_id must be a non-empty string",
                code="invalid_arguments",
            )
        return await _run_tool(
            "read_channel_task",
            runtime_client.read_task(task_id=task_id.strip()),
        )

    @tool(
        "create_channel_task",
        "Create a structured channel task in the current server channel",
        {"title": str, "description": str, "priority": str},
    )
    async def create_channel_task(args: dict[str, Any]) -> dict[str, Any]:
        title = args.get("title")
        if not isinstance(title, str) or not title.strip():
            return _format_tool_error(
                "create_channel_task",
                "title must be a non-empty string",
                code="invalid_arguments",
            )
        description = args.get("description")
        priority = args.get("priority")
        return await _run_tool(
            "create_channel_task",
            runtime_client.create_task(
                title=title.strip(),
                description=description.strip()
                if isinstance(description, str)
                else None,
                priority=priority.strip() if isinstance(priority, str) else None,
            ),
        )

    @tool(
        "update_channel_task_status",
        "Update a structured channel task status in the current server channel",
        {"task_id": str, "status": str, "position": int},
    )
    async def update_channel_task_status(args: dict[str, Any]) -> dict[str, Any]:
        task_id = args.get("task_id")
        status = args.get("status")
        if not isinstance(task_id, str) or not task_id.strip():
            return _format_tool_error(
                "update_channel_task_status",
                "task_id must be a non-empty string",
                code="invalid_arguments",
            )
        if not isinstance(status, str) or not status.strip():
            return _format_tool_error(
                "update_channel_task_status",
                "status must be a non-empty string",
                code="invalid_arguments",
            )
        position = args.get("position")
        return await _run_tool(
            "update_channel_task_status",
            runtime_client.update_task_status(
                task_id=task_id.strip(),
                status=status.strip(),
                position=position if isinstance(position, int) else 0,
            ),
        )

    @tool(
        "claim_channel_task",
        "Claim a structured channel task as the current agent",
        {"task_id": str},
    )
    async def claim_channel_task(args: dict[str, Any]) -> dict[str, Any]:
        task_id = args.get("task_id")
        if not isinstance(task_id, str) or not task_id.strip():
            return _format_tool_error(
                "claim_channel_task",
                "task_id must be a non-empty string",
                code="invalid_arguments",
            )
        return await _run_tool(
            "claim_channel_task",
            runtime_client.claim_task(task_id=task_id.strip()),
        )

    @tool(
        "comment_on_channel_task",
        "Post a structured comment to a channel task thread",
        {"task_id": str, "text": str},
    )
    async def comment_on_channel_task(args: dict[str, Any]) -> dict[str, Any]:
        task_id = args.get("task_id")
        text = args.get("text")
        if not isinstance(task_id, str) or not task_id.strip():
            return _format_tool_error(
                "comment_on_channel_task",
                "task_id must be a non-empty string",
                code="invalid_arguments",
            )
        if not isinstance(text, str) or not text.strip():
            return _format_tool_error(
                "comment_on_channel_task",
                "text must be a non-empty string",
                code="invalid_arguments",
            )
        return await _run_tool(
            "comment_on_channel_task",
            runtime_client.comment_on_task(task_id=task_id.strip(), text=text.strip()),
        )

    @tool(
        "add_channel_message_reaction",
        "Add an emoji reaction to a message in the current channel",
        {"message_id": str, "emoji": str},
    )
    async def add_channel_message_reaction(args: dict[str, Any]) -> dict[str, Any]:
        message_id = args.get("message_id")
        emoji = args.get("emoji")
        if not isinstance(message_id, str) or not message_id.strip():
            return _format_tool_error(
                "add_channel_message_reaction",
                "message_id must be a non-empty string",
                code="invalid_arguments",
            )
        if not isinstance(emoji, str) or not emoji.strip():
            return _format_tool_error(
                "add_channel_message_reaction",
                "emoji must be a non-empty string",
                code="invalid_arguments",
            )
        return await _run_tool(
            "add_channel_message_reaction",
            runtime_client.add_message_reaction(
                message_id=message_id.strip(),
                emoji=emoji.strip(),
            ),
        )

    @tool(
        "remove_channel_message_reaction",
        "Remove this agent's emoji reaction from a message in the current channel",
        {"message_id": str, "emoji": str},
    )
    async def remove_channel_message_reaction(args: dict[str, Any]) -> dict[str, Any]:
        message_id = args.get("message_id")
        emoji = args.get("emoji")
        if not isinstance(message_id, str) or not message_id.strip():
            return _format_tool_error(
                "remove_channel_message_reaction",
                "message_id must be a non-empty string",
                code="invalid_arguments",
            )
        if not isinstance(emoji, str) or not emoji.strip():
            return _format_tool_error(
                "remove_channel_message_reaction",
                "emoji must be a non-empty string",
                code="invalid_arguments",
            )
        return await _run_tool(
            "remove_channel_message_reaction",
            runtime_client.remove_message_reaction(
                message_id=message_id.strip(),
                emoji=emoji.strip(),
            ),
        )

    return create_sdk_mcp_server(
        name="poco-channel-runtime",
        version="0.1.0",
        tools=[
            list_channel_artifacts,
            read_channel_artifact,
            search_channel_artifacts,
            read_channel_artifact_text,
            stage_channel_artifact_to_workspace,
            read_channel_messages,
            list_channel_agents,
            request_agent_collaboration,
            list_channel_tasks,
            read_channel_task,
            create_channel_task,
            update_channel_task_status,
            claim_channel_task,
            comment_on_channel_task,
            add_channel_message_reaction,
            remove_channel_message_reaction,
        ],
    )
