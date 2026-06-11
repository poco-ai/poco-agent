import json
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

MEMORY_MCP_SERVER_KEY = "__poco_memory"


class MemoryClient:
    """Client for manager memory proxy APIs."""

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

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method=method,
                url=f"{self.base_url}{path}",
                params=params,
                json=json_body,
                headers=self._headers(),
            )
            response.raise_for_status()

        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("Invalid memory proxy response")
        if payload.get("code") != 0:
            raise RuntimeError(str(payload.get("message") or "Memory proxy error"))
        return payload.get("data")

    async def create_memories(
        self,
        *,
        messages: list[dict[str, Any]],
    ) -> Any:
        body: dict[str, Any] = {
            "session_id": self.session_id,
            "messages": messages,
        }
        return await self._request("POST", "/api/v1/memories", json_body=body)

    async def create_memory_text(
        self,
        *,
        text: str,
    ) -> Any:
        return await self.create_memories(
            messages=[{"role": "user", "content": text}],
        )

    async def list_memories(self) -> Any:
        return await self._request(
            "GET",
            "/api/v1/memories",
            params={"session_id": self.session_id},
        )

    async def search_memories(
        self,
        *,
        query: str,
    ) -> Any:
        body: dict[str, Any] = {
            "session_id": self.session_id,
            "query": query,
        }
        return await self._request("POST", "/api/v1/memories/search", json_body=body)

    async def get_memory(self, memory_id: str) -> Any:
        return await self._request(
            "GET",
            f"/api/v1/memories/{memory_id}",
            params={"session_id": self.session_id},
        )

    async def update_memory(self, *, memory_id: str, text: str) -> Any:
        return await self._request(
            "PUT",
            f"/api/v1/memories/{memory_id}",
            json_body={"session_id": self.session_id, "text": text},
        )

    async def get_memory_history(self, memory_id: str) -> Any:
        return await self._request(
            "GET",
            f"/api/v1/memories/{memory_id}/history",
            params={"session_id": self.session_id},
        )

    async def delete_memory(self, memory_id: str) -> Any:
        return await self._request(
            "DELETE",
            f"/api/v1/memories/{memory_id}",
            params={"session_id": self.session_id},
        )

    async def delete_all_memories(self) -> Any:
        return await self._request(
            "DELETE",
            "/api/v1/memories",
            params={"session_id": self.session_id},
        )


def _format_tool_result(title: str, data: Any) -> dict[str, Any]:
    body = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    return {"content": [{"type": "text", "text": f"{title}\n{body}"}]}


async def _run_tool(title: str, operation) -> dict[str, Any]:
    try:
        result = await operation
    except Exception as exc:
        return _format_tool_result(f"{title}_error", {"error": str(exc)})
    return _format_tool_result(title, result)


def _extract_messages(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    messages: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if not isinstance(role, str) or not isinstance(content, str):
            continue
        clean_role = role.strip()
        clean_content = content.strip()
        if not clean_role or not clean_content:
            continue
        messages.append({"role": clean_role, "content": clean_content})
    return messages


def create_memory_mcp_server(memory_client: MemoryClient) -> McpSdkServerConfig:
    """Create an in-process SDK MCP server for memory management."""

    @tool(
        "memory_create",
        "Create one user-level memory from plain text",
        {"text": str},
    )
    async def memory_create(args: dict[str, Any]) -> dict[str, Any]:
        raw_text = args.get("text")
        text = raw_text.strip() if isinstance(raw_text, str) else None
        if text:
            return await _run_tool(
                "memory_create",
                memory_client.create_memory_text(text=text),
            )

        # Backward-compatible fallback for old callers that still send `messages`.
        messages = _extract_messages(args.get("messages"))
        if messages:
            return await _run_tool(
                "memory_create",
                memory_client.create_memories(messages=messages),
            )

        return _format_tool_result(
            "memory_create_error",
            {
                "error": "text must be a non-empty string. Use memory_create_conversation for messages."
            },
        )

    @tool(
        "memory_create_conversation",
        "Create user-level memories from a conversation",
        {"messages": list},
    )
    async def memory_create_conversation(args: dict[str, Any]) -> dict[str, Any]:
        messages = _extract_messages(args.get("messages"))
        if not messages:
            return _format_tool_result(
                "memory_create_conversation_error",
                {"error": "messages must be a non-empty list of {role, content}"},
            )
        return await _run_tool(
            "memory_create_conversation",
            memory_client.create_memories(messages=messages),
        )

    @tool(
        "memory_search",
        "Search user-level memories",
        {"query": str},
    )
    async def memory_search(args: dict[str, Any]) -> dict[str, Any]:
        query = args.get("query")
        if not isinstance(query, str) or not query.strip():
            return _format_tool_result(
                "memory_search_error",
                {"error": "query must be a non-empty string"},
            )
        return await _run_tool(
            "memory_search",
            memory_client.search_memories(query=query.strip()),
        )

    @tool(
        "memory_list",
        "List user-level memories",
        {},
    )
    async def memory_list(args: dict[str, Any]) -> dict[str, Any]:
        _ = args
        return await _run_tool("memory_list", memory_client.list_memories())

    @tool(
        "memory_get",
        "Get one memory by id",
        {"memory_id": str},
    )
    async def memory_get(args: dict[str, Any]) -> dict[str, Any]:
        memory_id = args.get("memory_id")
        if not isinstance(memory_id, str) or not memory_id.strip():
            return _format_tool_result(
                "memory_get_error",
                {"error": "memory_id must be a non-empty string"},
            )
        return await _run_tool(
            "memory_get",
            memory_client.get_memory(memory_id.strip()),
        )

    @tool(
        "memory_update",
        "Update one memory by id",
        {"memory_id": str, "text": str},
    )
    async def memory_update(args: dict[str, Any]) -> dict[str, Any]:
        memory_id = args.get("memory_id")
        text = args.get("text")
        if not isinstance(memory_id, str) or not memory_id.strip():
            return _format_tool_result(
                "memory_update_error",
                {"error": "memory_id must be a non-empty string"},
            )
        if not isinstance(text, str) or not text.strip():
            return _format_tool_result(
                "memory_update_error",
                {"error": "text must be a non-empty string"},
            )
        return await _run_tool(
            "memory_update",
            memory_client.update_memory(
                memory_id=memory_id.strip(),
                text=text.strip(),
            ),
        )

    @tool(
        "memory_history",
        "Get memory history by id",
        {"memory_id": str},
    )
    async def memory_history(args: dict[str, Any]) -> dict[str, Any]:
        memory_id = args.get("memory_id")
        if not isinstance(memory_id, str) or not memory_id.strip():
            return _format_tool_result(
                "memory_history_error",
                {"error": "memory_id must be a non-empty string"},
            )
        return await _run_tool(
            "memory_history",
            memory_client.get_memory_history(memory_id.strip()),
        )

    @tool(
        "memory_delete",
        "Delete one memory by id",
        {"memory_id": str},
    )
    async def memory_delete(args: dict[str, Any]) -> dict[str, Any]:
        memory_id = args.get("memory_id")
        if not isinstance(memory_id, str) or not memory_id.strip():
            return _format_tool_result(
                "memory_delete_error",
                {"error": "memory_id must be a non-empty string"},
            )
        return await _run_tool(
            "memory_delete",
            memory_client.delete_memory(memory_id.strip()),
        )

    @tool(
        "memory_delete_all",
        "Delete all user-level memories",
        {},
    )
    async def memory_delete_all(args: dict[str, Any]) -> dict[str, Any]:
        _ = args
        return await _run_tool(
            "memory_delete_all",
            memory_client.delete_all_memories(),
        )

    return create_sdk_mcp_server(
        name=MEMORY_MCP_SERVER_KEY,
        version="1.0.0",
        tools=[
            memory_create,
            memory_create_conversation,
            memory_list,
            memory_search,
            memory_get,
            memory_update,
            memory_history,
            memory_delete,
            memory_delete_all,
        ],
    )
