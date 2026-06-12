import hashlib
import json
import logging
import os
import re
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal, cast

from claude_agent_sdk import ClaudeAgentOptions
from claude_agent_sdk.types import (
    AgentDefinition as SdkAgentDefinition,
)
from claude_agent_sdk.types import (
    HookContext,
    HookInput,
    HookMatcher,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    SdkPluginConfig,
    SyncHookJSONOutput,
)
from dotenv import load_dotenv

from app.core.client_pool import ToolPermissionController, get_claude_sdk_client_pool
from app.core.channel_runtime import (
    CHANNEL_RUNTIME_MCP_SERVER_KEY,
    ChannelRuntimeClient,
    create_channel_runtime_mcp_server,
)
from app.core.memory import (
    MEMORY_MCP_SERVER_KEY,
    MemoryClient,
    create_memory_mcp_server,
)
from app.core.observability.request_context import (
    generate_request_id,
    generate_trace_id,
    reset_request_id,
    reset_trace_id,
    set_request_id,
    set_trace_id,
)
from app.core.user_input import UserInputClient
from app.core.workspace import WorkspaceManager
from app.hooks.base import ExecutionContext
from app.hooks.manager import HookManager
from app.prompts import build_prompt_appendix
from app.schemas.request import TaskConfig
from app.schemas.state import BrowserState
from app.utils.browser import format_viewport_size, parse_viewport_size

load_dotenv()

logger = logging.getLogger(__name__)
_SUBAGENT_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
_LOCAL_MOUNT_ROOT = "/workspace/.poco-local"


@contextmanager
def _temporary_env_overrides(overrides: dict[str, str]):
    previous: dict[str, str | None] = {}
    try:
        for key, value in overrides.items():
            previous[key] = os.environ.get(key)
            os.environ[key] = value
        yield
    finally:
        for key, old_value in previous.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value


class AgentExecutor:
    def __init__(
        self,
        session_id: str,
        hooks: list,
        sdk_session_id: str | None = None,
        *,
        run_id: str | None = None,
        user_input_client: UserInputClient | None = None,
        memory_client: MemoryClient | None = None,
        channel_runtime_client: ChannelRuntimeClient | None = None,
        request_id: str | None = None,
        trace_id: str | None = None,
    ):
        self.session_id = session_id
        self.sdk_session_id = sdk_session_id
        self.run_id = run_id
        self.hooks = HookManager(hooks)
        self.user_input_client = user_input_client
        self.memory_client = memory_client
        self.workspace = WorkspaceManager(
            mount_path=os.environ.get("WORKSPACE_PATH", "/workspace")
        )
        self.memory_mcp_server = (
            create_memory_mcp_server(memory_client) if memory_client else None
        )
        self.channel_runtime_client = channel_runtime_client
        self.channel_runtime_mcp_server = (
            create_channel_runtime_mcp_server(
                channel_runtime_client,
                workspace_root=str(self.workspace.root_path),
            )
            if channel_runtime_client
            else None
        )
        self._request_id = request_id
        self._trace_id = trace_id

    def _build_tool_permission_handler(self, permission_mode: str):
        executor = self

        class ToolPermissionHandler:
            def __init__(self) -> None:
                self.plan_approved = permission_mode != "plan"

            async def can_use_tool(self, tool_name, input_data, context):
                if not executor.user_input_client:
                    return PermissionResultDeny(
                        message="User input client not configured"
                    )

                if permission_mode == "plan" and not self.plan_approved:
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
                            "session_id": executor.session_id,
                            "tool_name": tool_name,
                            "tool_input": input_data,
                        }
                        created = await executor.user_input_client.create_request(
                            request_payload
                        )
                        request_id = created.get("id")
                        if not request_id:
                            return PermissionResultDeny(
                                message="Failed to create user input request"
                            )
                        result = await executor.user_input_client.wait_for_answer(
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
                    try:
                        plan_expires_at = (
                            datetime.now(timezone.utc) + timedelta(minutes=10)
                        ).isoformat()
                        request_payload = {
                            "session_id": executor.session_id,
                            "tool_name": tool_name,
                            "tool_input": input_data,
                            "expires_at": plan_expires_at,
                        }
                        created = await executor.user_input_client.create_request(
                            request_payload
                        )
                        request_id = created.get("id")
                        if not request_id:
                            return PermissionResultDeny(
                                message="Failed to create plan approval request"
                            )
                        result = await executor.user_input_client.wait_for_answer(
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

                    self.plan_approved = True
                    return PermissionResultAllow(updated_input=input_data)

                return PermissionResultAllow(updated_input=input_data)

        return ToolPermissionHandler()

    async def execute(
        self, prompt: str, config: TaskConfig, *, permission_mode: str = "default"
    ):
        # Initialize context early so we can always report failures via callbacks,
        # even if workspace preparation (e.g. repo clone) fails.
        ctx = ExecutionContext(
            self.session_id,
            str(self.workspace.root_path),
            run_id=self.run_id,
        )
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
                prompt = self._compose_user_prompt(prompt, config, cwd=ctx.cwd)

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
            sdk_permission_mode = cast(
                Literal["default", "acceptEdits", "plan", "bypassPermissions"],
                normalized_permission_mode,
            )

            permission_handler = self._build_tool_permission_handler(
                sdk_permission_mode
            )

            mcp_servers = dict(config.mcp_config or {})
            mcp_servers = self._inject_memory_mcp(mcp_servers)
            mcp_servers = self._inject_channel_runtime_mcp(mcp_servers)
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
                        # Subagent model overrides are intentionally unsupported.
                        model=None,
                    )
                agents = resolved or None

            plugins = self._discover_plugins()
            env_overrides = {
                key: value
                for key, value in (config.env_overrides or {}).items()
                if isinstance(key, str) and key.strip() and isinstance(value, str)
            }
            with _temporary_env_overrides(env_overrides):
                selected_model = (config.model or "").strip()
                if not selected_model:
                    selected_model = os.environ["DEFAULT_MODEL"]

                extra_allowed_dirs = sorted(
                    {
                        mount.container_path
                        for mount in (config.resolved_local_mounts or [])
                        if mount.container_path
                    }
                )

                def build_options(
                    controller: ToolPermissionController,
                ) -> ClaudeAgentOptions:
                    return ClaudeAgentOptions(
                        cwd=ctx.cwd,
                        add_dirs=[str(d) for d in extra_allowed_dirs],
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
                        permission_mode=sdk_permission_mode,
                        model=selected_model,
                        can_use_tool=controller.can_use_tool,
                        hooks={
                            "PreToolUse": [
                                HookMatcher(matcher=None, hooks=[dummy_hook])
                            ]
                        },
                        agents=agents,
                        plugins=plugins,
                    )

                cache_key = self._build_client_cache_key(config)
                fingerprint = self._build_client_cache_fingerprint(
                    config=config,
                    cwd=ctx.cwd,
                    selected_model=selected_model,
                    permission_mode=sdk_permission_mode,
                    extra_allowed_dirs=extra_allowed_dirs,
                    mcp_servers=mcp_servers,
                    agents=agents,
                    plugins=plugins,
                )
                pool = get_claude_sdk_client_pool()
                async with await pool.acquire(
                    key=cache_key,
                    fingerprint=fingerprint,
                    options_factory=build_options,
                    delegate=permission_handler,
                ) as lease:
                    query_session_id = self.sdk_session_id or self.session_id
                    logger.info(
                        "sdk_client_lease_acquired",
                        extra={
                            "session_id": self.session_id,
                            "run_id": self.run_id,
                            "sdk_session_id": self.sdk_session_id,
                            "cache_key": cache_key,
                            "cache_hit": lease.cache_hit,
                            "disconnect_on_release": lease.disconnect_on_release,
                        },
                    )
                    step_started = time.perf_counter()
                    await lease.client.query(prompt, session_id=query_session_id)
                    logger.info(
                        "timing",
                        extra={
                            "step": "executor_first_query_issued",
                            "duration_ms": int(
                                (time.perf_counter() - step_started) * 1000
                            ),
                            "session_id": self.session_id,
                            "run_id": self.run_id,
                            "sdk_session_id": self.sdk_session_id,
                            "cache_key": cache_key,
                            "cache_hit": lease.cache_hit,
                        },
                    )
                    async for msg in lease.client.receive_response():
                        await self.hooks.run_on_response(ctx, msg)
                        if self._is_terminal_response_message(msg):
                            break

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

    def _build_client_cache_key(self, config: TaskConfig) -> str | None:
        if config.agent_runtime_mode != "persistent" or not config.agent_identity_id:
            return None
        return f"agent:{config.agent_identity_id}:session:{self.session_id}"

    @staticmethod
    def _is_terminal_response_message(message: object) -> bool:
        return isinstance(message, ResultMessage) or (
            type(message).__name__ == "ResultMessage"
        )

    @staticmethod
    def _build_client_cache_fingerprint(
        *,
        config: TaskConfig,
        cwd: str,
        selected_model: str,
        permission_mode: str,
        extra_allowed_dirs: list[str],
        mcp_servers: dict,
        agents: dict[str, SdkAgentDefinition] | None,
        plugins: list[SdkPluginConfig],
    ) -> str:
        payload = {
            "cwd": cwd,
            "model": selected_model,
            "permission_mode": permission_mode,
            "add_dirs": sorted(extra_allowed_dirs),
            "mcp_servers": sorted(mcp_servers.keys()),
            "mcp_server_ids": list(config.mcp_server_ids or []),
            "skill_ids": list(config.skill_ids or []),
            "plugin_ids": list(config.plugin_ids or []),
            "agents": sorted((agents or {}).keys()),
            "plugins": [
                plugin_path
                for plugin in plugins
                if (plugin_path := getattr(plugin, "path", None))
            ],
            "browser_enabled": bool(config.browser_enabled),
            "memory_enabled": bool(config.memory_enabled),
            "channel_tools_enabled": bool(
                config.server_id and config.channel_id and config.agent_identity_id
            ),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    @staticmethod
    def _input_hint_display_path(input_file: object) -> str | None:
        path = getattr(input_file, "path", None) or ""
        name = getattr(input_file, "name", None) or ""
        if path:
            return str(path).lstrip("/")
        if name:
            return f"inputs/{name}"
        return None

    @staticmethod
    def _input_hint_relative_path(input_file: object) -> str | None:
        display = AgentExecutor._input_hint_display_path(input_file)
        if not display:
            return None
        return display.removeprefix("inputs/").lstrip("/")

    @staticmethod
    def _normalized_workspace_reference_path(reference: dict[str, Any]) -> str:
        raw_path = str(reference.get("path") or "").replace("\\", "/").strip()
        return raw_path.lstrip("/")

    @classmethod
    def _build_file_reference_hint_lines(
        cls,
        references: list[dict[str, Any]],
        inputs: list[object],
    ) -> list[str]:
        if not references or not inputs:
            return []

        inputs_by_source: dict[str, object] = {}
        inputs_by_relative_path: dict[str, object] = {}
        for input_file in inputs:
            source = str(getattr(input_file, "source", "") or "").strip()
            if source:
                inputs_by_source.setdefault(source, input_file)
            relative_path = cls._input_hint_relative_path(input_file)
            if relative_path:
                inputs_by_relative_path.setdefault(relative_path, input_file)

        lines: list[str] = []
        for reference in references:
            if not isinstance(reference, dict):
                continue

            kind = str(reference.get("kind") or "").strip()
            input_file = None
            if kind == "input_file":
                source = str(reference.get("source") or "").strip()
                input_file = inputs_by_source.get(source)
            elif kind == "workspace_file":
                path = cls._normalized_workspace_reference_path(reference)
                input_file = inputs_by_relative_path.get(path)

            display_path = (
                cls._input_hint_display_path(input_file) if input_file else None
            )
            inserted_text = str(
                reference.get("insertedText")
                or reference.get("inserted_text")
                or reference.get("displayName")
                or reference.get("display_name")
                or ""
            ).strip()
            if display_path and inserted_text:
                lines.append(f"- {inserted_text} -> {display_path}")

        return lines

    def _build_input_hint(self, config: TaskConfig) -> str | None:
        lines: list[str] = []
        inputs = config.input_files or []
        if inputs:
            lines.append(
                "Input files for this run are available under inputs/ (or /workspace/inputs):"
            )
            for item in inputs:
                display = self._input_hint_display_path(item)
                if display:
                    lines.append(f"- {display}")
            reference_lines = self._build_file_reference_hint_lines(
                config.file_references or config.input_file_references or [],
                list(inputs),
            )
            if reference_lines:
                lines.append("Referenced files in the user prompt resolve to:")
                lines.extend(reference_lines)
            lines.append("Do not modify files under inputs/ unless the user asks.")

        mounts = config.resolved_local_mounts or []
        if mounts:
            if lines:
                lines.append("")
            lines.append("Filesystem layout for this task:")
            lines.append("- /workspace is the Poco sandbox workspace.")
            lines.append(
                f"- Authorized user local directories are mounted under {_LOCAL_MOUNT_ROOT}/."
            )
            lines.append(
                f"- Changes under {_LOCAL_MOUNT_ROOT}/... affect the user's real local files directly."
            )
            lines.append(
                f"- Do not treat {_LOCAL_MOUNT_ROOT}/... as part of the sandbox workspace snapshot or git history."
            )
            configured_mounts = {
                mount.id: mount for mount in (config.local_mounts or [])
            }
            for mount in mounts:
                requested_host_path = None
                configured_mount = configured_mounts.get(mount.id)
                if configured_mount:
                    requested_host_path = configured_mount.host_path
                lines.append(
                    f"- {mount.container_path} ({mount.access_mode}, name: {mount.name})"
                )
                if requested_host_path:
                    lines.append(
                        "- User path "
                        f"{requested_host_path} is exposed inside the container as "
                        f"{mount.container_path}."
                    )
            # Build an explicit resolution table so the agent can match
            # user-referenced paths without reasoning.
            resolution_lines = [
                "Path resolution table — MUST consult before ANY file I/O:",
            ]
            for mount in mounts:
                host_path = None
                cfg = configured_mounts.get(mount.id)
                if cfg:
                    host_path = cfg.host_path
                dir_name = Path(host_path).name if host_path else mount.name
                resolution_lines.append(
                    f'  "{dir_name}" or "{mount.name}"'
                    + (f' or "{host_path}"' if host_path else "")
                    + f" => {mount.container_path}"
                )
            resolution_lines.append(
                "If the user's mentioned path matches a key above, use the "
                "mapped container path. NEVER create a duplicate under /workspace."
            )
            lines.append("")
            lines.extend(resolution_lines)
            lines.append("")
            lines.append(
                "- Respect read-only local mounts and never write to ro paths."
            )

        return "\n".join(lines) if lines else None

    @staticmethod
    def _build_persistent_state_hint(config: TaskConfig) -> str | None:
        if config.agent_runtime_mode != "persistent":
            return None

        return "\n".join(
            [
                "Persistent state contract:",
                "- /agent_state is your private long-term state directory.",
                "- Use /agent_state/MEMORY.md for durable facts, preferences, and collaboration constraints that should survive future sessions.",
                "- Use /agent_state/state/*.json for structured runtime state such as active task bookkeeping.",
                "- Use /agent_state/notes/ for working notes that may evolve during ongoing tasks.",
                "- Do not overwrite system-owned fields in /agent_state/profile.json.",
                "- Do not store short-lived task chatter or noisy scratch notes in long-term memory.",
                "- Private state is not the same as published artifacts; share deliverables through workspace export or published artifacts instead.",
            ]
        )

    @staticmethod
    def _build_channel_task_hint(config: TaskConfig) -> str | None:
        if not (config.server_id and config.channel_id and config.agent_identity_id):
            return None

        return "\n".join(
            [
                "Channel task collaboration contract:",
                "- Session todos are internal execution planning only; they do not automatically create or update channel tasks.",
                "- Use list_channel_tasks to inspect current channel tasks and read_channel_task when you need one task's full details before acting.",
                "- When this work should become a team-visible task, prefer the structured tools create_channel_task, update_channel_task_status, claim_channel_task, and comment_on_channel_task.",
                "- Use create_channel_task for durable collaborative work, not for temporary scratch todos.",
                "- Use update_channel_task_status when the team-facing task changes stage, and use comment_on_channel_task when progress should be visible in the task thread.",
                "- These task tools are scoped to the current server and channel context. Do not claim that you listed, read, created, or updated a task unless the structured tool call succeeded.",
            ]
        )

    @staticmethod
    def _build_channel_artifact_hint(config: TaskConfig) -> str | None:
        if not (config.server_id and config.channel_id and config.agent_identity_id):
            return None

        return "\n".join(
            [
                "Channel artifact access contract:",
                "- Published channel artifacts are shared read-only resources for this channel.",
                "- Artifact logical_path values are controlled identifiers, not "
                "/workspace filesystem paths.",
                "- When you need shared files, first use list_channel_artifacts "
                "or search_channel_artifacts, then read_channel_artifact by artifact_id. "
                "Use logical_path only when you pass the exact logical_path returned by "
                "the artifact tools; display_name is not a stable read identifier.",
                "- Use read_channel_artifact_text when you need extracted text from "
                "supported binary documents such as PDFs without staging the original file.",
                "- Use stage_channel_artifact_to_workspace when you need the original "
                "artifact written into /workspace/inputs for local processing.",
                "- Do not guess that a published artifact exists under "
                "/workspace, /agent_state, or a local mount path.",
                "- These artifact tools are scoped to the current server and "
                "channel context and never provide write access.",
            ]
        )

    @staticmethod
    def _build_channel_reaction_hint(config: TaskConfig) -> str | None:
        if not (config.server_id and config.channel_id and config.agent_identity_id):
            return None

        return "\n".join(
            [
                "Channel message reaction contract:",
                "- Reactions are lightweight message feedback, not reply messages.",
                "- Use add_channel_message_reaction or remove_channel_message_reaction only for messages visible in the current channel.",
                "- These tools are scoped to the current server, channel, and agent identity; do not pass or invent actor identity.",
                "- Do not claim you reacted to a message unless the structured tool call succeeded.",
            ]
        )

    @staticmethod
    def _build_channel_runtime_hint(config: TaskConfig) -> str | None:
        if not (config.server_id and config.channel_id and config.agent_identity_id):
            return None

        return "\n".join(
            [
                "Channel runtime tools contract:",
                "- Use read_channel_messages with message_ids for exact messages, thread_root_message_id for a thread, anchor_message_id plus direction before/after for channel timeline paging, no selector for recent channel messages, or read_all=true only when you truly need the full channel timeline.",
                "- Use list_channel_agents before requesting another agent's help when you need to discover available collaborators.",
                "- Use request_agent_collaboration for explicit agent-to-agent collaboration; include the smallest useful request_text and references.",
                "- Agent output that mentions @handle is visible text only and does not trigger another agent.",
                "- Do not claim that you read messages or requested collaboration unless the structured tool call succeeded.",
            ]
        )

    @staticmethod
    def _build_channel_trigger_context_hint(config: TaskConfig) -> str | None:
        context = config.trigger_context
        if not isinstance(context, dict):
            return None
        if not (config.server_id and config.channel_id and config.agent_identity_id):
            return None

        source_actor = context.get("source_actor")
        source_actor_label = ""
        if isinstance(source_actor, dict):
            actor_type = source_actor.get("actor_type") or "unknown"
            display_name = source_actor.get("display_name")
            user_id = source_actor.get("user_id")
            agent_id = source_actor.get("agent_identity_id")
            identity = user_id or agent_id
            if display_name and identity:
                source_actor_label = f"{actor_type} {display_name} ({identity})"
            elif display_name:
                source_actor_label = f"{actor_type} {display_name}"
            elif identity:
                source_actor_label = f"{actor_type} ({identity})"
            else:
                source_actor_label = str(actor_type)

        lines = [
            "Channel trigger context:",
            "This is a channel collaboration run. You are responding as the target agent in a shared server/channel conversation, not as an isolated one-off chat session.",
            "People and agents mentioned by name or @handle in the user request are likely channel collaborators. Do not assume you know every collaborator from this prompt alone; use list_channel_agents to discover channel agents when identity matters.",
            "The identifiers below are routing and lookup handles. Use them with channel runtime tools instead of treating them as user-facing content.",
            "",
            "Field meanings:",
            "- source_actor: the human, agent, or system actor whose message caused this run.",
            "- trigger_type: how this run was started, such as channel_mention, agent_dm, or agent_collaboration.",
            "- server_id: the long-lived collaboration workspace containing the channel.",
            "- channel_id: the conversation scope whose messages, tasks, artifacts, reactions, and agents are available through channel tools.",
            "- trigger_message_id: the message that directly triggered this run; read it when the visible prompt is ambiguous or truncated.",
            "- thread_root_message_id: the root message of the current thread; use it to read thread context when the user is replying in a thread.",
            "- target_agent_identity_id: your stable agent identity in this server.",
            "- target_agent_handle is your channel handle in this run.",
            "- reference_message_ids: messages selected or implied as context for this trigger.",
            "- reference_artifact_ids: published channel artifacts selected as context; pass these artifact_id values to read_channel_artifact before relying on their content.",
            "- reference_task_ids: channel tasks selected as context.",
            "- handoff_dedupe_key: an internal loop/deduplication key; do not show it to users unless explicitly asked.",
            "",
            "Raw trigger values:",
            f"- version: {context.get('version', 1)}",
            f"- trigger_type: {context.get('trigger_type') or config.trigger_type or 'unknown'}",
            f"- server_id: {context.get('server_id') or config.server_id}",
            f"- channel_id: {context.get('channel_id') or config.channel_id}",
            f"- trigger_message_id: {context.get('trigger_message_id') or config.trigger_message_id}",
            f"- thread_root_message_id: {context.get('thread_root_message_id') or config.thread_root_message_id}",
            f"- target_agent_identity_id: {context.get('target_agent_identity_id') or config.agent_identity_id}",
        ]
        target_handle = context.get("target_agent_handle")
        if target_handle:
            lines.append(f"- target_agent_handle: {target_handle}")
        if source_actor_label:
            lines.append(f"- source_actor: {source_actor_label}")

        references = context.get("references")
        if isinstance(references, dict):
            message_ids = references.get("message_ids") or []
            artifact_ids = references.get("artifact_ids") or []
            task_ids = references.get("task_ids") or []
            lines.append(f"- reference_message_ids: {', '.join(message_ids) or 'none'}")
            lines.append(
                f"- reference_artifact_ids: {', '.join(artifact_ids) or 'none'}"
            )
            lines.append(f"- reference_task_ids: {', '.join(task_ids) or 'none'}")

        handoff = context.get("handoff")
        if isinstance(handoff, dict):
            depth = handoff.get("depth")
            dedupe_key = handoff.get("dedupe_key")
            if depth is not None:
                lines.append(f"- handoff_depth: {depth}")
            if dedupe_key:
                lines.append(f"- handoff_dedupe_key: {dedupe_key}")

        lines.extend(
            [
                "",
                "Channel context access contract:",
                "- Treat the visible user prompt as the trigger body.",
                "- Other named people or agents in the user request may refer to channel members or channel agents. Use list_channel_agents when you need to resolve who they are or what handles are available.",
                "- Use read_channel_messages with trigger_message_id, thread_root_message_id, reference_message_ids, anchor_message_id plus direction before/after, no selector, or read_all=true when you need channel history beyond the visible prompt.",
                "- Use list_channel_artifacts, search_channel_artifacts, and read_channel_artifact when you need shared files.",
                "- For referenced artifacts, use the reference_artifact_ids above as read_channel_artifact artifact_id values.",
                "- Do not assume recent channel conversation or artifact content is fully inlined in this prompt.",
            ]
        )
        return "\n".join(lines)

    def _compose_user_prompt(self, prompt: str, config: TaskConfig, *, cwd: str) -> str:
        sections = [prompt]

        input_hint = self._build_input_hint(config)
        if input_hint:
            sections.insert(0, input_hint)

        channel_trigger_hint = self._build_channel_trigger_context_hint(config)
        if channel_trigger_hint:
            sections.insert(0, channel_trigger_hint)

        persistent_state_hint = self._build_persistent_state_hint(config)
        if persistent_state_hint:
            sections.append(persistent_state_hint)

        channel_task_hint = self._build_channel_task_hint(config)
        if channel_task_hint:
            sections.append(channel_task_hint)

        channel_artifact_hint = self._build_channel_artifact_hint(config)
        if channel_artifact_hint:
            sections.append(channel_artifact_hint)

        channel_runtime_hint = self._build_channel_runtime_hint(config)
        if channel_runtime_hint:
            sections.append(channel_runtime_hint)

        channel_reaction_hint = self._build_channel_reaction_hint(config)
        if channel_reaction_hint:
            sections.append(channel_reaction_hint)

        prompt_appendix = build_prompt_appendix(
            browser_enabled=config.browser_enabled,
            memory_enabled=bool(getattr(self, "memory_mcp_server", None)),
        )
        if prompt_appendix:
            sections.append(prompt_appendix)

        sections.append(
            "Please reply in the same language as the user's input unless explicitly requested otherwise."
        )
        sections.append(self._build_workspace_scope_hint(cwd, config))
        return "\n\n".join(section for section in sections if section)

    @staticmethod
    def _build_workspace_scope_hint(cwd: str, config: TaskConfig) -> str:
        mounts = config.resolved_local_mounts or []
        if not mounts:
            return (
                f"Current working directory: {cwd}. "
                "Keep normal work inside this workspace unless the user explicitly asks otherwise."
            )

        mount_paths = ", ".join(
            mount.container_path for mount in sorted(mounts, key=lambda item: item.id)
        )
        return (
            f"Current working directory: {cwd}. "
            f"The following authorized local mount paths are available: {mount_paths}. "
            "Before creating or writing any file, check the path resolution table above. "
            "If the path matches a local mount, use the container mount path instead of /workspace. "
            "Do not mix local mount changes into workspace git operations unless the user asks."
        )

    def _discover_plugins(self) -> list[SdkPluginConfig]:
        """Discover staged plugins under /workspace/.claude_data/plugins.

        Plugins are staged by Executor Manager into the workspace. The SDK expects the plugin
        root directory (containing `.claude-plugin/plugin.json`).
        """
        root = Path(self.workspace.root_path) / ".claude_data" / "plugins"
        if not root.exists() or not root.is_dir():
            return []

        configs: list[SdkPluginConfig] = []
        try:
            for entry in sorted(root.iterdir(), key=lambda p: p.name.lower()):
                if not entry.is_dir() or entry.is_symlink():
                    continue
                manifest = entry / ".claude-plugin" / "plugin.json"
                if not manifest.exists() or not manifest.is_file():
                    continue
                configs.append(SdkPluginConfig(type="local", path=str(entry)))
        except Exception:
            return []

        return configs

    def _inject_playwright_mcp(self, mcp_servers: dict) -> dict:
        """Inject built-in Playwright MCP (CDP mode) for browser-enabled tasks.

        This keeps the Playwright MCP concept/config hidden from end users: they only toggle `browser_enabled`, and the executor wires the MCP server internally.
        """

        # TODO: Refactor this injection path to use a structured MCP config builder.
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
        output_mode = (
            (os.environ.get("PLAYWRIGHT_MCP_OUTPUT_MODE") or "").strip().lower()
        )
        if output_mode not in {"file", "stdout"}:
            output_mode = "file"
        image_responses = (
            (os.environ.get("PLAYWRIGHT_MCP_IMAGE_RESPONSES") or "").strip().lower()
        )
        if image_responses not in {"allow", "omit"}:
            image_responses = "omit"
        playwright_launch_command = (
            "exec npx -y @playwright/mcp@latest "
            f"--cdp-endpoint {cdp_endpoint!r} "
            "--caps vision "
            f"--viewport-size {viewport_size!r} "
            f"--output-mode {output_mode!r} "
            f"--image-responses {image_responses!r}"
        )

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
{playwright_launch_command}
""".strip()

        injected = dict(mcp_servers)
        injected[key] = {"command": "bash", "args": ["-lc", wait_then_start]}
        return injected

    def _inject_memory_mcp(self, mcp_servers: dict) -> dict:
        """Inject built-in memory MCP server for user-level memory tools."""
        if not self.memory_mcp_server:
            return mcp_servers
        if MEMORY_MCP_SERVER_KEY in mcp_servers:
            return mcp_servers

        injected = dict(mcp_servers)
        injected[MEMORY_MCP_SERVER_KEY] = self.memory_mcp_server
        return injected

    def _inject_channel_runtime_mcp(self, mcp_servers: dict) -> dict:
        """Inject built-in channel runtime MCP server for channel-scoped agent runs."""
        if not self.channel_runtime_mcp_server:
            return mcp_servers
        if CHANNEL_RUNTIME_MCP_SERVER_KEY in mcp_servers:
            return mcp_servers

        injected = dict(mcp_servers)
        injected[CHANNEL_RUNTIME_MCP_SERVER_KEY] = self.channel_runtime_mcp_server
        return injected
