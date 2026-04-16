import asyncio
import base64
import json
import logging
import os
from typing import Any

import httpx  # pyrefly: ignore[missing-import]
import websockets  # pyrefly: ignore[missing-import]

from app.core.computer import ComputerClient
from app.hooks.base import AgentHook, ExecutionContext
from app.utils.browser import parse_viewport_size
from app.utils.serializer import serialize_message

POCO_PLAYWRIGHT_MCP_PREFIX = "mcp____poco_playwright__"
logger = logging.getLogger(__name__)


class BrowserScreenshotHook(AgentHook):
    """Capture a screenshot after each browser tool call and upload it to the manager.

    This hook is intentionally best-effort: failures should never block the agent execution.
    """

    def __init__(
        self,
        *,
        client: ComputerClient,
        cdp_endpoint: str | None = None,
        viewport_size: str | None = None,
    ) -> None:
        self._client = client
        self._cdp_endpoint = (
            (cdp_endpoint or os.environ.get("POCO_BROWSER_CDP_ENDPOINT", "")).strip()
            or "http://127.0.0.1:9222"
        ).rstrip("/")
        viewport_raw = (
            viewport_size or os.environ.get("POCO_BROWSER_VIEWPORT_SIZE") or ""
        ).strip()
        self._viewport = parse_viewport_size(viewport_raw) or (1366, 768)
        self._viewport_applied: set[str] = set()
        self._tool_name_by_use_id: dict[str, str] = {}
        self._scheduled: set[str] = set()
        self._tasks: set[asyncio.Task[None]] = set()

    async def on_teardown(self, context: ExecutionContext) -> None:
        # Best-effort flush pending screenshot tasks.
        if not self._tasks:
            return

        pending = list(self._tasks)
        self._tasks.clear()
        try:
            done, still_pending = await asyncio.wait(pending, timeout=15.0)
            # Avoid leaking tasks beyond teardown; cancellation is best-effort.
            for task in still_pending:
                task.cancel()
            _ = done
        except Exception:
            return

    async def on_agent_response(self, context: ExecutionContext, message: Any) -> None:
        payload = serialize_message(message)
        if not isinstance(payload, dict):
            return

        content = payload.get("content", [])
        if not isinstance(content, list):
            return

        for block in content:
            if not isinstance(block, dict):
                continue

            block_type = str(block.get("_type", "") or "")

            if "ToolUseBlock" in block_type:
                tool_use_id = block.get("id")
                tool_name = block.get("name")
                if isinstance(tool_use_id, str) and isinstance(tool_name, str):
                    self._tool_name_by_use_id[tool_use_id] = tool_name
                continue

            if "ToolResultBlock" not in block_type:
                continue

            tool_use_id = block.get("tool_use_id")
            if not isinstance(tool_use_id, str) or not tool_use_id:
                continue

            tool_name = self._tool_name_by_use_id.get(tool_use_id)
            if not tool_name or not tool_name.startswith(POCO_PLAYWRIGHT_MCP_PREFIX):
                continue

            if tool_use_id in self._scheduled:
                continue
            self._scheduled.add(tool_use_id)

            task = asyncio.create_task(
                self._capture_and_upload_best_effort(
                    session_id=context.session_id,
                    run_id=context.run_id,
                    tool_use_id=tool_use_id,
                    tool_name=tool_name,
                    tool_result_content=block.get("content"),
                )
            )
            self._tasks.add(task)
            task.add_done_callback(lambda t: self._tasks.discard(t))

    async def _capture_and_upload_best_effort(
        self,
        *,
        session_id: str,
        run_id: str | None,
        tool_use_id: str,
        tool_name: str,
        tool_result_content: Any,
    ) -> None:
        try:
            png_bytes = self._extract_png_from_tool_result(tool_result_content)
            if not png_bytes:
                png_bytes = await self._capture_png_with_retry()
            if not png_bytes:
                logger.debug(
                    "browser_screenshot_capture_skipped",
                    extra={
                        "session_id": session_id,
                        "tool_use_id": tool_use_id,
                        "tool_name": tool_name,
                    },
                )
                return

            ok = await self._client.upload_browser_screenshot(
                session_id=session_id,
                run_id=run_id,
                tool_use_id=tool_use_id,
                png_bytes=png_bytes,
            )
            if not ok:
                logger.warning(
                    "browser_screenshot_upload_failed",
                    extra={
                        "session_id": session_id,
                        "tool_use_id": tool_use_id,
                        "tool_name": tool_name,
                    },
                )
        except Exception:
            return

    @staticmethod
    def _extract_png_from_tool_result(tool_result_content: Any) -> bytes | None:
        """Try to extract PNG bytes from a tool result payload (Playwright MCP screenshot tools)."""

        if not tool_result_content:
            return None

        # Common shape: [{type: "image", source: {data: "...", media_type: "image/png"}}]
        content = tool_result_content
        if isinstance(content, dict):
            # Some tools may wrap under {"content": [...]}
            content = content.get("content")

        if not isinstance(content, list):
            return None

        for item in content:
            if not isinstance(item, dict):
                continue
            if str(item.get("type") or "").lower() != "image":
                continue
            source = item.get("source")
            if not isinstance(source, dict):
                continue
            data = source.get("data")
            if not isinstance(data, str) or not data:
                continue

            try:
                return base64.b64decode(data, validate=True)
            except Exception:
                return None

        return None

    async def _capture_png_with_retry(self) -> bytes | None:
        # CDP calls can be flaky on cold starts; retry once with a small delay.
        for attempt in range(2):
            png = await self._capture_png()
            if png:
                return png
            if attempt == 0:
                try:
                    await asyncio.sleep(0.2)
                except Exception:
                    return None
        return None

    async def _capture_png(self) -> bytes | None:
        target = await self._resolve_page_ws_url()
        if not target:
            return None
        ws_url, target_id = target

        payload = await self._cdp_capture_screenshot(ws_url, target_id)
        if not payload:
            return None

        try:
            return base64.b64decode(payload, validate=True)
        except Exception:
            return None

    async def _resolve_page_ws_url(self) -> tuple[str, str | None] | None:
        # Prefer /json/list to get a page target (Page.captureScreenshot works on page sessions).
        url = f"{self._cdp_endpoint}/json/list"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                targets = resp.json()
        except Exception:
            return None

        if not isinstance(targets, list):
            return None

        pages: list[dict[str, Any]] = []
        for item in targets:
            if not isinstance(item, dict):
                continue
            if item.get("type") != "page":
                continue
            ws_url = item.get("webSocketDebuggerUrl")
            if isinstance(ws_url, str) and ws_url.strip():
                pages.append(item)

        if not pages:
            return None

        def _score(page: dict[str, Any]) -> int:
            raw_url = str(page.get("url") or "").strip()
            if not raw_url:
                return 0
            if raw_url in {"about:blank", "chrome://newtab/"}:
                return 0
            return 1

        pages.sort(key=_score, reverse=True)
        picked = pages[0]
        ws_url = picked.get("webSocketDebuggerUrl")
        target_id = picked.get("id")
        ws_url = ws_url.strip() if isinstance(ws_url, str) and ws_url.strip() else None
        target_id = (
            target_id.strip()
            if isinstance(target_id, str) and target_id.strip()
            else None
        )
        if not ws_url:
            return None
        return ws_url, target_id

    async def _cdp_call(
        self,
        ws: Any,
        *,
        call_id: int,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        payload: dict[str, Any] = {"id": call_id, "method": method}
        if params is not None:
            payload["params"] = params
        await ws.send(json.dumps(payload))

        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=8.0)
            message = json.loads(raw)
            if not isinstance(message, dict):
                continue
            if message.get("id") != call_id:
                continue
            if message.get("error"):
                return None
            result = message.get("result")
            if result is None:
                return {}
            return result if isinstance(result, dict) else {}

    async def _cdp_capture_screenshot(
        self, ws_url: str, target_id: str | None
    ) -> str | None:
        try:
            async with websockets.connect(ws_url, max_size=50 * 1024 * 1024) as ws:
                # Ensure Page domain is enabled for consistent screenshots.
                await self._cdp_call(ws, call_id=1, method="Page.enable")

                # Best-effort: lock viewport to a desktop size so responsive pages don't render
                # as mobile when the underlying display/window is small.
                apply_key = target_id or ws_url
                if apply_key not in self._viewport_applied:
                    width, height = self._viewport
                    _ = await self._cdp_call(
                        ws,
                        call_id=2,
                        method="Emulation.setDeviceMetricsOverride",
                        params={
                            "width": width,
                            "height": height,
                            "deviceScaleFactor": 1,
                            "mobile": False,
                        },
                    )

                    # If the browser is headful, also try to resize the window for noVNC.
                    if target_id:
                        win = await self._cdp_call(
                            ws,
                            call_id=3,
                            method="Browser.getWindowForTarget",
                            params={"targetId": target_id},
                        )
                        window_id = (
                            int(win["windowId"])
                            if isinstance(win, dict)
                            and isinstance(win.get("windowId"), int)
                            else None
                        )
                        if window_id is not None:
                            _ = await self._cdp_call(
                                ws,
                                call_id=4,
                                method="Browser.setWindowBounds",
                                params={
                                    "windowId": window_id,
                                    "bounds": {
                                        "width": width,
                                        "height": height,
                                    },
                                },
                            )

                    self._viewport_applied.add(apply_key)

                result = await self._cdp_call(
                    ws,
                    call_id=5,
                    method="Page.captureScreenshot",
                    params={"format": "png"},
                )
                if not isinstance(result, dict):
                    return None
                data = result.get("data")
                return data if isinstance(data, str) and data else None
        except Exception:
            return None
