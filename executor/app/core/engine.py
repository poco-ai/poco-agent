import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone

from claude_agent_sdk import ClaudeAgentOptions
from claude_agent_sdk.client import ClaudeSDKClient
from claude_agent_sdk.types import (
    AgentDefinition as SdkAgentDefinition,
    HookContext,
    HookInput,
    HookMatcher,
    PermissionResultAllow,
    PermissionResultDeny,
    SyncHookJSONOutput,
)
from dotenv import load_dotenv

from app.core.workspace import WorkspaceManager
from app.core.user_input import UserInputClient
from app.hooks.base import ExecutionContext
from app.hooks.manager import HookManager
from app.core.observability.request_context import (
    generate_request_id,
    generate_trace_id,
    reset_request_id,
    reset_trace_id,
    set_request_id,
    set_trace_id,
)
from app.schemas.request import TaskConfig
from app.schemas.state import BrowserState
from app.utils.browser import format_viewport_size, parse_viewport_size

load_dotenv()

logger = logging.getLogger(__name__)
_SUBAGENT_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


class AgentExecutor:
    def __init__(
        self,
        session_id: str,
        hooks: list,
        sdk_session_id: str | None = None,
        user_input_client: UserInputClient | None = None,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
    ):
        self.session_id = session_id
        self.sdk_session_id = sdk_session_id
        self.hooks = HookManager(hooks)
        self.user_input_client = user_input_client
        self._request_id = request_id
        self._trace_id = trace_id
        self.workspace = WorkspaceManager(
            mount_path=os.environ.get("WORKSPACE_PATH", "/workspace")
        )

    async def execute(
        self, prompt: str, config: TaskConfig, *, permission_mode: str = "default"
    ):
        # Initialize context early so we can always report failures via callbacks,
        # even if workspace preparation (e.g. repo clone) fails.
        ctx = ExecutionContext(self.session_id, str(self.workspace.root_path))
        if config.browser_enabled:
            ctx.current_state.browser = BrowserState(enabled=True)

        request_id_token = set_request_id(self._request_id or generate_request_id())
        trace_id_token = set_trace_id(self._trace_id or generate_trace_id())

        started = time.perf_counter()
        status = "completed"
        logger.info(
            "task_started",
            extra={
                "session_id": self.session_id,
                "sdk_session_id": self.sdk_session_id,
            },
        )

        try:
            await self.workspace.prepare(config)
            ctx.cwd = str(self.workspace.work_path)
            await self.hooks.run_on_setup(ctx)

            # Slash commands must be sent as-is (no prefix text), otherwise the SDK may not
            # recognize them as commands.
            is_slash_command = prompt.lstrip().startswith("/")
            if not is_slash_command:
                input_hint = self._build_input_hint(config)
                if input_hint:
                    prompt = f"{input_hint}\n\n{prompt}"

                prompt = f"{prompt}\n\nCurrent working directory: {ctx.cwd}"

            async def dummy_hook(
                input_data: HookInput, tool_use_id: str | None, context: HookContext
            ) -> SyncHookJSONOutput:
                return {"continue_": True}

            normalized_permission_mode = (permission_mode or "default").strip()
            if normalized_permission_mode not in {
                "default",
                "acceptEdits",
                "plan",
                "bypassPermissions",
            }:
                normalized_permission_mode = "default"

            # Plan mode is a two-phase flow:
            # - Phase 1 (planning): deny execution tools (Write/Bash/...) until ExitPlanMode is approved.
            # - Phase 2 (execution): allow tools normally.
            plan_approved = normalized_permission_mode != "plan"

            async def can_use_tool(tool_name, input_data, context):
                nonlocal plan_approved

                if not self.user_input_client:
                    return PermissionResultDeny(
                        message="User input client not configured"
                    )

                # Enforce "plan" phase restrictions until the plan is approved.
                if normalized_permission_mode == "plan" and not plan_approved:
                    allowed_in_plan_phase = {
                        "Read",
                        "Grep",
                        "Glob",
                        "TodoWrite",
                        "Task",
                        "Skill",
                        "AskUserQuestion",
                        "ExitPlanMode",
                    }
                    if tool_name not in allowed_in_plan_phase:
                        return PermissionResultDeny(
                            message=f"Tool '{tool_name}' is not allowed in plan mode before approval",
                            interrupt=False,
                        )

                if tool_name == "AskUserQuestion":
                    try:
                        request_payload = {
                            "session_id": self.session_id,
                            "tool_name": tool_name,
                            "tool_input": input_data,
                        }
                        created = await self.user_input_client.create_request(
                            request_payload
                        )
                        request_id = created.get("id")
                        if not request_id:
                            return PermissionResultDeny(
                                message="Failed to create user input request"
                            )
                        result = await self.user_input_client.wait_for_answer(
                            request_id=request_id,
                            timeout_seconds=60,
                        )
                    except Exception:
                        return PermissionResultDeny(
                            message="User input handling failed"
                        )

                    if not result or result.get("answers") is None:
                        return PermissionResultDeny(message="User input timeout")

                    return PermissionResultAllow(
                        updated_input={
                            "questions": input_data.get("questions", []),
                            "answers": result.get("answers", {}),
                        }
                    )

                if tool_name == "ExitPlanMode":
                    # Ask the user to approve the plan (UX shows a dedicated card in the frontend).
                    try:
                        plan_expires_at = (
                            datetime.now(timezone.utc) + timedelta(minutes=10)
                        ).isoformat()
                        request_payload = {
                            "session_id": self.session_id,
                            "tool_name": tool_name,
                            "tool_input": input_data,
                            "expires_at": plan_expires_at,
                        }
                        created = await self.user_input_client.create_request(
                            request_payload
                        )
                        request_id = created.get("id")
                        if not request_id:
                            return PermissionResultDeny(
                                message="Failed to create plan approval request"
                            )
                        result = await self.user_input_client.wait_for_answer(
                            request_id=request_id,
                            timeout_seconds=600,
                        )
                    except Exception:
                        return PermissionResultDeny(
                            message="Plan approval handling failed"
                        )

                    if not result or result.get("answers") is None:
                        return PermissionResultDeny(
                            message="Plan approval timeout",
                            interrupt=True,
                        )

                    # Strict protocol: only treat answers["approved"] == "true" as approved.
                    answers = result.get("answers") or {}
                    approved_raw = answers.get("approved")
                    approved = (
                        isinstance(approved_raw, str)
                        and approved_raw.strip().lower() == "true"
                    )
                    if not approved:
                        return PermissionResultDeny(
                            message="Plan not approved",
                            interrupt=True,
                        )

                    plan_approved = True
                    return PermissionResultAllow(updated_input=input_data)

                return PermissionResultAllow(updated_input=input_data)

            mcp_servers = dict(config.mcp_config or {})
            if config.browser_enabled:
                mcp_servers = self._inject_playwright_mcp(mcp_servers)

            agents: dict[str, SdkAgentDefinition] | None = None
            if config.agents:
                resolved: dict[str, SdkAgentDefinition] = {}
                for name, definition in (config.agents or {}).items():
                    if not isinstance(name, str):
                        continue
                    clean_name = name.strip()
                    if (
                        not clean_name
                        or clean_name in {".", ".."}
                        or not _SUBAGENT_NAME_PATTERN.fullmatch(clean_name)
                    ):
                        continue
                    description = (definition.description or "").strip()
                    prompt_text = (definition.prompt or "").strip()
                    if not description or not prompt_text:
                        continue
                    resolved[clean_name] = SdkAgentDefinition(
                        description=description,
                        prompt=definition.prompt,
                        tools=definition.tools,
                        model=definition.model,
                    )
                agents = resolved or None

            options = ClaudeAgentOptions(
                cwd=ctx.cwd,
                resume=self.sdk_session_id,
                # Load both user-level (~/.claude) and project-level (.claude) settings.
                # Skills are staged into user-level ~/.claude/skills (symlinked to /workspace/.claude_data).
                setting_sources=["user", "project"],
                allowed_tools=[
                    "Skill",
                    "Read",
                    "Edit",
                    "Write",
                    "Bash",
                    "TodoWrite",
                    "Grep",
                    "Glob",
                    "Task",
                ],
                mcp_servers=mcp_servers,
                permission_mode=normalized_permission_mode,
                model=os.environ["DEFAULT_MODEL"],
                can_use_tool=can_use_tool,
                hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[dummy_hook])]},
                agents=agents,
            )

            async with ClaudeSDKClient(options=options) as client:
                await client.query(prompt)
                async for msg in client.receive_response():
                    await self.hooks.run_on_response(ctx, msg)

        except Exception as e:
            status = "failed"
            logger.exception(
                "task_failed",
                extra={
                    "session_id": self.session_id,
                    "sdk_session_id": self.sdk_session_id,
                },
            )
            await self.hooks.run_on_error(ctx, e)

        finally:
            await self.hooks.run_on_teardown(ctx)
            await self.workspace.cleanup()
            logger.info(
                "task_finished",
                extra={
                    "session_id": self.session_id,
                    "sdk_session_id": self.sdk_session_id,
                    "status": status,
                    "duration_ms": int((time.perf_counter() - started) * 1000),
                },
            )
            reset_request_id(request_id_token)
            reset_trace_id(trace_id_token)

    def _build_input_hint(self, config: TaskConfig) -> str | None:
        inputs = config.input_files or []
        if not inputs:
            return None

        lines = [
            "User-uploaded inputs are available under inputs/ (or /workspace/inputs):",
        ]
        for item in inputs:
            path = getattr(item, "path", None) or ""
            name = getattr(item, "name", None) or ""
            display = path.lstrip("/") if path else (f"inputs/{name}" if name else "")
            if display:
                lines.append(f"- {display}")
        lines.append("Do not modify files under inputs/ unless the user asks.")
        return "\n".join(lines)

    @staticmethod
    def _inject_playwright_mcp(mcp_servers: dict) -> dict:
        """Inject built-in Playwright MCP (CDP mode) for browser-enabled tasks.

        This keeps the Playwright MCP concept/config hidden from end users: they only toggle `browser_enabled`, and the executor wires the MCP server internally.
        """

        # TODO: 这里的实现不够优雅
        key = "__poco_playwright"
        if key in mcp_servers:
            return mcp_servers

        cdp_endpoint = (
            os.environ.get("POCO_BROWSER_CDP_ENDPOINT", "http://127.0.0.1:9222").strip()
            or "http://127.0.0.1:9222"
        )

        viewport_raw = (os.environ.get("POCO_BROWSER_VIEWPORT_SIZE") or "").strip()
        viewport = parse_viewport_size(viewport_raw) or (1366, 768)
        viewport_size = format_viewport_size(*viewport)

        # Wait for Chrome's CDP endpoint before starting the MCP server to avoid flakiness on startup.
        wait_then_start = f"""
python3 - <<'PY'
import time
import urllib.request

url = {cdp_endpoint!r} + "/json/version"
deadline = time.time() + 15
while time.time() < deadline:
    try:
        with urllib.request.urlopen(url, timeout=0.5) as resp:
            resp.read()
        break
    except Exception:
        time.sleep(0.1)
else:
    raise SystemExit("CDP endpoint not ready: " + url)
PY
exec npx -y @playwright/mcp@latest --cdp-endpoint {cdp_endpoint!r} --caps vision --viewport-size {viewport_size!r}
""".strip()

        injected = dict(mcp_servers)
        injected[key] = {"command": "bash", "args": ["-lc", wait_then_start]}
        return injected
