import logging
import time

from app.core.settings import get_settings
from app.core.observability.request_context import (
    generate_request_id,
    generate_trace_id,
    get_request_id,
    get_trace_id,
    reset_request_id,
    reset_trace_id,
    set_request_id,
    set_trace_id,
)
from app.services.backend_client import BackendClient
from app.services.container_pool import ContainerPool
from app.services.executor_client import ExecutorClient
from app.services.config_resolver import ConfigResolver
from app.services.skill_stager import SkillStager
from app.services.plugin_stager import PluginStager
from app.services.attachment_stager import AttachmentStager
from app.services.slash_command_stager import SlashCommandStager
from app.services.sub_agent_stager import SubAgentStager

logger = logging.getLogger(__name__)


def _extract_enabled_skill_names(skills: object) -> list[str]:
    if not isinstance(skills, dict):
        return []

    names: set[str] = set()
    for raw_name, spec in skills.items():
        if not isinstance(raw_name, str):
            continue
        name = raw_name.strip()
        if not name:
            continue
        if isinstance(spec, dict) and spec.get("enabled") is False:
            continue
        names.add(name)
    return sorted(names)


class TaskDispatcher:
    """Task dispatcher with container pool integration."""

    container_pool: ContainerPool | None = None

    @classmethod
    def get_container_pool(cls) -> ContainerPool:
        """Get container pool instance (lazy load)."""
        if cls.container_pool is None:
            cls.container_pool = ContainerPool()
        return cls.container_pool

    @staticmethod
    async def dispatch(
        task_id: str,
        session_id: str,
        prompt: str,
        config: dict,
        sdk_session_id: str | None = None,
        request_id: str | None = None,
        trace_id: str | None = None,
        enqueued_at: float | None = None,
    ) -> None:
        """Dispatch task to executor.

        Args:
            task_id: Task ID
            session_id: Session ID
            prompt: Task prompt
            config: Task configuration
            sdk_session_id: Claude SDK session ID for resuming conversations
            request_id: Request ID for correlating logs across async boundaries
            trace_id: Trace ID for correlating logs across async boundaries
            enqueued_at: perf_counter timestamp when the task was enqueued (for queue delay)
        """
        settings = get_settings()
        executor_client = ExecutorClient()
        backend_client = BackendClient()
        container_pool = TaskDispatcher.get_container_pool()
        config_resolver = ConfigResolver(backend_client)
        skill_stager = SkillStager()
        plugin_stager = PluginStager()
        attachment_stager = AttachmentStager()
        slash_command_stager = SlashCommandStager()
        subagent_stager = SubAgentStager()

        user_id = config.get("user_id", "")
        container_mode = config.get("container_mode", "ephemeral")
        container_id = config.get("container_id")

        callback_url = f"{settings.callback_base_url}/api/v1/callback"
        callback_token = settings.callback_token

        executor_url = None
        request_id_token = set_request_id(
            request_id or get_request_id() or generate_request_id()
        )
        trace_id_token = set_trace_id(trace_id or get_trace_id() or generate_trace_id())
        try:
            dispatch_started = time.perf_counter()
            if enqueued_at is not None:
                logger.info(
                    "timing",
                    extra={
                        "step": "task_dispatch_queue_delay",
                        "duration_ms": int((time.perf_counter() - enqueued_at) * 1000),
                        "task_id": task_id,
                        "session_id": session_id,
                        "user_id": user_id,
                    },
                )

            logger.info(
                f"Dispatching task {task_id} (session: {session_id}, mode: {container_mode})"
            )

            step_started = time.perf_counter()
            resolved_config = await config_resolver.resolve(
                user_id,
                config or {},
                session_id=session_id,
                task_id=task_id,
            )
            logger.info(
                "timing",
                extra={
                    "step": "task_dispatch_resolve_config",
                    "duration_ms": int((time.perf_counter() - step_started) * 1000),
                    "task_id": task_id,
                    "session_id": session_id,
                    "user_id": user_id,
                },
            )

            step_started = time.perf_counter()
            staged_skills = skill_stager.stage_skills(
                user_id=user_id,
                session_id=session_id,
                skills=resolved_config.get("skill_files") or {},
            )
            resolved_config["skill_files"] = staged_skills
            logger.info(
                "timing",
                extra={
                    "step": "task_dispatch_stage_skills",
                    "duration_ms": int((time.perf_counter() - step_started) * 1000),
                    "task_id": task_id,
                    "session_id": session_id,
                    "user_id": user_id,
                    "skills_staged": len(staged_skills),
                },
            )

            step_started = time.perf_counter()
            staged_plugins = plugin_stager.stage_plugins(
                user_id=user_id,
                session_id=session_id,
                plugins=resolved_config.get("plugin_files") or {},
            )
            resolved_config["plugin_files"] = staged_plugins
            logger.info(
                "timing",
                extra={
                    "step": "task_dispatch_stage_plugins",
                    "duration_ms": int((time.perf_counter() - step_started) * 1000),
                    "task_id": task_id,
                    "session_id": session_id,
                    "user_id": user_id,
                    "plugins_staged": len(staged_plugins),
                },
            )

            step_started = time.perf_counter()
            staged_inputs = attachment_stager.stage_inputs(
                user_id=user_id,
                session_id=session_id,
                inputs=resolved_config.get("input_files") or [],
            )
            resolved_config["input_files"] = staged_inputs
            logger.info(
                "timing",
                extra={
                    "step": "task_dispatch_stage_inputs",
                    "duration_ms": int((time.perf_counter() - step_started) * 1000),
                    "task_id": task_id,
                    "session_id": session_id,
                    "user_id": user_id,
                    "inputs_staged": len(staged_inputs),
                },
            )

            step_started = time.perf_counter()
            skill_names = _extract_enabled_skill_names(staged_skills)
            resolved_commands = await backend_client.resolve_slash_commands(
                user_id=user_id,
                skill_names=skill_names,
            )
            staged_commands = slash_command_stager.stage_commands(
                user_id=user_id,
                session_id=session_id,
                commands=resolved_commands,
            )
            logger.info(
                "timing",
                extra={
                    "step": "task_dispatch_stage_slash_commands",
                    "duration_ms": int((time.perf_counter() - step_started) * 1000),
                    "task_id": task_id,
                    "session_id": session_id,
                    "user_id": user_id,
                    "commands_staged": len(staged_commands),
                },
            )

            step_started = time.perf_counter()
            raw_agents_val = resolved_config.pop("subagent_raw_agents", None)
            raw_agents = raw_agents_val if isinstance(raw_agents_val, dict) else {}
            try:
                staged_agents = subagent_stager.stage_raw_agents(
                    user_id=user_id,
                    session_id=session_id,
                    raw_agents=raw_agents,
                )
                logger.info(
                    "timing",
                    extra={
                        "step": "task_dispatch_stage_subagents",
                        "duration_ms": int((time.perf_counter() - step_started) * 1000),
                        "task_id": task_id,
                        "session_id": session_id,
                        "user_id": user_id,
                        "subagents_requested": len(raw_agents),
                        "subagents_staged": len(staged_agents),
                    },
                )
            except Exception as exc:
                logger.warning(
                    f"Failed to stage subagents for session {session_id}: {exc}"
                )

            step_started = time.perf_counter()
            browser_enabled = bool(resolved_config.get("browser_enabled"))
            executor_url, container_id = await container_pool.get_or_create_container(
                session_id=session_id,
                user_id=user_id,
                browser_enabled=browser_enabled,
                container_mode=container_mode,
                container_id=container_id,
            )
            logger.info(
                "timing",
                extra={
                    "step": "task_dispatch_get_or_create_container",
                    "duration_ms": int((time.perf_counter() - step_started) * 1000),
                    "task_id": task_id,
                    "session_id": session_id,
                    "user_id": user_id,
                    "container_id": container_id,
                    "container_mode": container_mode,
                    "browser_enabled": browser_enabled,
                },
            )

            step_started = time.perf_counter()
            await backend_client.update_session_status(session_id, "running")
            logger.info(
                "timing",
                extra={
                    "step": "task_dispatch_backend_update_status_running",
                    "duration_ms": int((time.perf_counter() - step_started) * 1000),
                    "task_id": task_id,
                    "session_id": session_id,
                    "user_id": user_id,
                },
            )

            step_started = time.perf_counter()
            await executor_client.execute_task(
                executor_url=executor_url,
                session_id=session_id,
                run_id=None,
                prompt=prompt,
                callback_url=callback_url,
                callback_token=callback_token,
                config=resolved_config,
                callback_base_url=settings.callback_base_url,
                sdk_session_id=sdk_session_id,
            )
            logger.info(
                "timing",
                extra={
                    "step": "task_dispatch_executor_execute_task",
                    "duration_ms": int((time.perf_counter() - step_started) * 1000),
                    "task_id": task_id,
                    "session_id": session_id,
                    "user_id": user_id,
                    "container_id": container_id,
                },
            )

            logger.info(f"Task {task_id} dispatched successfully to executor")
            logger.info(
                "timing",
                extra={
                    "step": "task_dispatch_total",
                    "duration_ms": int((time.perf_counter() - dispatch_started) * 1000),
                    "task_id": task_id,
                    "session_id": session_id,
                    "user_id": user_id,
                    "container_id": container_id,
                    "container_mode": container_mode,
                },
            )

        except Exception as e:
            logger.error(f"Failed to dispatch task {task_id}: {e}")
            await backend_client.update_session_status(session_id, "failed")
            await container_pool.cancel_task(session_id)
            raise
        finally:
            reset_request_id(request_id_token)
            reset_trace_id(trace_id_token)

    @staticmethod
    async def on_task_complete(session_id: str) -> None:
        """Handle task completion.

        Args:
            session_id: Session ID
        """
        container_pool = TaskDispatcher.get_container_pool()
        await container_pool.on_task_complete(session_id)
