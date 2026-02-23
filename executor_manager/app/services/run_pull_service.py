import asyncio
import logging
import os
import socket
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.settings import get_settings
from app.scheduler.task_dispatcher import TaskDispatcher
from app.services.backend_client import BackendClient
from app.services.executor_client import ExecutorClient
from app.services.config_resolver import ConfigResolver
from app.services.skill_stager import SkillStager
from app.services.plugin_stager import PluginStager
from app.services.attachment_stager import AttachmentStager
from app.services.claude_md_stager import ClaudeMdStager
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


class RunPullService:
    """Background service that pulls queued runs from Backend and dispatches them."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.backend_client = BackendClient()
        self.executor_client = ExecutorClient()
        self.container_pool = TaskDispatcher.get_container_pool()
        self.config_resolver = ConfigResolver(self.backend_client)
        self.skill_stager = SkillStager()
        self.plugin_stager = PluginStager()
        self.attachment_stager = AttachmentStager()
        self.claude_md_stager = ClaudeMdStager()
        self.slash_command_stager = SlashCommandStager()
        self.subagent_stager = SubAgentStager()

        self.worker_id = f"{socket.gethostname()}:{os.getpid()}"
        self._semaphore = asyncio.Semaphore(self.settings.max_concurrent_tasks)
        self._tasks: set[asyncio.Task[None]] = set()
        self._shutdown = False
        self._logged_started = False
        self._windows_until: dict[str, datetime] = {}
        self._window_locks: dict[str, asyncio.Lock] = {}

    def _get_window_lock(self, window_id: str) -> asyncio.Lock:
        lock = self._window_locks.get(window_id)
        if lock is None:
            lock = asyncio.Lock()
            self._window_locks[window_id] = lock
        return lock

    def set_window_until(self, window_id: str, until_utc: datetime) -> None:
        if not window_id.strip():
            return
        if until_utc.tzinfo is None:
            until_utc = until_utc.replace(tzinfo=timezone.utc)
        self._windows_until[window_id] = until_utc.astimezone(timezone.utc)

    async def open_window(
        self,
        window_id: str,
        schedule_modes: list[str] | None = None,
        window_minutes: int = 60,
    ) -> None:
        if self._shutdown:
            return
        window_id = window_id.strip()
        if not window_id:
            return

        if window_minutes <= 0:
            window_minutes = 60

        lock = self._get_window_lock(window_id)
        async with lock:
            now_utc = datetime.now(timezone.utc)
            until_utc = now_utc + timedelta(minutes=window_minutes)
            self._windows_until[window_id] = until_utc
            logger.info(
                f"Window opened (id={window_id}, until={until_utc.isoformat()}, schedule_modes={schedule_modes})"
            )

        await self.poll(schedule_modes=schedule_modes)

    async def poll_window(
        self,
        window_id: str,
        schedule_modes: list[str] | None = None,
    ) -> None:
        if self._shutdown:
            return
        window_id = window_id.strip()
        if not window_id:
            return

        until_utc = self._windows_until.get(window_id)
        if not until_utc:
            return

        now_utc = datetime.now(timezone.utc)
        if now_utc >= until_utc:
            self._windows_until.pop(window_id, None)
            return

        await self.poll(schedule_modes=schedule_modes)

    async def poll(self, schedule_modes: list[str] | None = None) -> None:
        """Poll backend run queue and dispatch as many as capacity allows."""
        if self._shutdown:
            return

        lease_seconds = max(5, int(self.settings.task_claim_lease_seconds))

        if not self._logged_started:
            logger.info(
                f"RunPullService started (worker_id={self.worker_id}, "
                f"lease={lease_seconds}s, max_concurrent={self.settings.max_concurrent_tasks})"
            )
            self._logged_started = True

        while not self._shutdown and not self._semaphore.locked():
            await self._semaphore.acquire()

            try:
                step_started = time.perf_counter()
                claim = await self.backend_client.claim_run(
                    worker_id=self.worker_id,
                    lease_seconds=lease_seconds,
                    schedule_modes=schedule_modes,
                )
                if claim:
                    logger.info(
                        "timing",
                        extra={
                            "step": "run_pull_claim_run",
                            "duration_ms": int(
                                (time.perf_counter() - step_started) * 1000
                            ),
                            "worker_id": self.worker_id,
                            "lease_seconds": lease_seconds,
                            "schedule_modes": schedule_modes,
                        },
                    )
            except Exception as e:
                logger.error(f"Failed to claim run from backend: {e}")
                self._semaphore.release()
                return

            if not claim:
                self._semaphore.release()
                return

            task = asyncio.create_task(self._handle_claim(claim))
            self._tasks.add(task)
            task.add_done_callback(self._on_task_done)

    async def shutdown(self) -> None:
        """Request shutdown and cancel inflight dispatch tasks."""
        self._shutdown = True
        await self._drain_tasks()

    def _on_task_done(self, task: asyncio.Task[None]) -> None:
        self._tasks.discard(task)
        self._semaphore.release()
        try:
            exc = task.exception()
        except asyncio.CancelledError:
            return
        if exc:
            logger.error(f"Run dispatch task failed: {exc}")

    async def _drain_tasks(self) -> None:
        if not self._tasks:
            return
        tasks = list(self._tasks)
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()

    async def _handle_claim(self, claim: dict[str, Any]) -> None:
        dispatch_started = time.perf_counter()
        run = claim.get("run") or {}
        run_id = run.get("run_id")
        session_id = run.get("session_id")
        scheduled_task_id = run.get("scheduled_task_id")
        user_id = claim.get("user_id") or ""
        prompt = claim.get("prompt") or ""
        config_snapshot = claim.get("config_snapshot") or {}
        sdk_session_id = None if scheduled_task_id else claim.get("sdk_session_id")
        permission_mode = str(run.get("permission_mode") or "default").strip()

        if not run_id or not session_id or not user_id or not prompt:
            logger.error(f"Invalid claim payload: {claim}")
            return

        container_mode = config_snapshot.get("container_mode", "ephemeral")
        container_id = config_snapshot.get("container_id")

        callback_url = f"{self.settings.callback_base_url}/api/v1/callback"
        ctx = {
            "run_id": str(run_id),
            "session_id": session_id,
            "user_id": user_id,
        }

        try:
            step_started = time.perf_counter()
            resolved_config = await self.config_resolver.resolve(
                user_id,
                config_snapshot,
                session_id=session_id,
                run_id=str(run_id),
            )
            logger.info(
                "timing",
                extra={
                    "step": "run_dispatch_resolve_config",
                    "duration_ms": int((time.perf_counter() - step_started) * 1000),
                    **ctx,
                },
            )

            step_started = time.perf_counter()
            staged_skills = self.skill_stager.stage_skills(
                user_id=user_id,
                session_id=session_id,
                skills=resolved_config.get("skill_files") or {},
            )
            resolved_config["skill_files"] = staged_skills
            logger.info(
                "timing",
                extra={
                    "step": "run_dispatch_stage_skills",
                    "duration_ms": int((time.perf_counter() - step_started) * 1000),
                    "skills_staged": len(staged_skills),
                    **ctx,
                },
            )

            step_started = time.perf_counter()
            staged_plugins = self.plugin_stager.stage_plugins(
                user_id=user_id,
                session_id=session_id,
                plugins=resolved_config.get("plugin_files") or {},
            )
            resolved_config["plugin_files"] = staged_plugins
            logger.info(
                "timing",
                extra={
                    "step": "run_dispatch_stage_plugins",
                    "duration_ms": int((time.perf_counter() - step_started) * 1000),
                    "plugins_staged": len(staged_plugins),
                    **ctx,
                },
            )

            step_started = time.perf_counter()
            staged_inputs = self.attachment_stager.stage_inputs(
                user_id=user_id,
                session_id=session_id,
                inputs=resolved_config.get("input_files") or [],
            )
            resolved_config["input_files"] = staged_inputs
            logger.info(
                "timing",
                extra={
                    "step": "run_dispatch_stage_inputs",
                    "duration_ms": int((time.perf_counter() - step_started) * 1000),
                    "inputs_staged": len(staged_inputs),
                    **ctx,
                },
            )

            step_started = time.perf_counter()
            skill_names = _extract_enabled_skill_names(staged_skills)
            resolved_commands = await self.backend_client.resolve_slash_commands(
                user_id=user_id,
                skill_names=skill_names,
            )
            staged_commands = self.slash_command_stager.stage_commands(
                user_id=user_id,
                session_id=session_id,
                commands=resolved_commands,
            )
            logger.info(
                "timing",
                extra={
                    "step": "run_dispatch_stage_slash_commands",
                    "duration_ms": int((time.perf_counter() - step_started) * 1000),
                    "commands_staged": len(staged_commands),
                    **ctx,
                },
            )

            # Stage user-level CLAUDE.md (persistent instructions) into ~/.claude.
            step_started = time.perf_counter()
            try:
                claude_md = await self.backend_client.get_claude_md(user_id=user_id)
                enabled = bool(claude_md.get("enabled"))
                content = (
                    claude_md.get("content")
                    if isinstance(claude_md.get("content"), str)
                    else ""
                )
                staged_md = self.claude_md_stager.stage(
                    user_id=user_id,
                    session_id=session_id,
                    enabled=enabled,
                    content=content,
                )
                bytes_val = staged_md.get("bytes", 0)
                logger.info(
                    "timing",
                    extra={
                        "step": "run_dispatch_stage_claude_md",
                        "duration_ms": int((time.perf_counter() - step_started) * 1000),
                        "enabled": bool(staged_md.get("enabled")),
                        "bytes": int(bytes_val) if isinstance(bytes_val, int) else 0,
                        **ctx,
                    },
                )
            except Exception as exc:
                # Best-effort: don't block execution if CLAUDE.md staging fails.
                logger.warning(
                    f"Failed to stage CLAUDE.md for session {session_id}: {exc}"
                )

            step_started = time.perf_counter()
            raw_agents_val = resolved_config.pop("subagent_raw_agents", None)
            raw_agents = raw_agents_val if isinstance(raw_agents_val, dict) else {}
            try:
                staged_agents = self.subagent_stager.stage_raw_agents(
                    user_id=user_id,
                    session_id=session_id,
                    raw_agents=raw_agents,
                )
                logger.info(
                    "timing",
                    extra={
                        "step": "run_dispatch_stage_subagents",
                        "duration_ms": int((time.perf_counter() - step_started) * 1000),
                        "subagents_requested": len(raw_agents),
                        "subagents_staged": len(staged_agents),
                        **ctx,
                    },
                )
            except Exception as exc:
                # Best-effort: keep tasks running even if staging fails.
                logger.warning(
                    f"Failed to stage subagents for session {session_id}: {exc}"
                )

            step_started = time.perf_counter()
            browser_enabled = bool(resolved_config.get("browser_enabled"))
            (
                executor_url,
                container_id,
            ) = await self.container_pool.get_or_create_container(
                session_id=session_id,
                user_id=user_id,
                browser_enabled=browser_enabled,
                container_mode=container_mode,
                container_id=container_id,
            )
            logger.info(
                "timing",
                extra={
                    "step": "run_dispatch_get_or_create_container",
                    "duration_ms": int((time.perf_counter() - step_started) * 1000),
                    "container_mode": container_mode,
                    "container_id": container_id,
                    "browser_enabled": browser_enabled,
                    **ctx,
                },
            )

            step_started = time.perf_counter()
            await self.executor_client.execute_task(
                executor_url=executor_url,
                session_id=session_id,
                run_id=str(run_id),
                prompt=prompt,
                callback_url=callback_url,
                callback_token=self.settings.callback_token,
                config=resolved_config,
                callback_base_url=self.settings.callback_base_url,
                sdk_session_id=sdk_session_id,
                permission_mode=permission_mode,
            )
            logger.info(
                "timing",
                extra={
                    "step": "run_dispatch_executor_execute_task",
                    "duration_ms": int((time.perf_counter() - step_started) * 1000),
                    "container_id": container_id,
                    **ctx,
                },
            )
            try:
                step_started = time.perf_counter()
                await self.backend_client.start_run(
                    run_id=run_id, worker_id=self.worker_id
                )
                logger.info(
                    "timing",
                    extra={
                        "step": "run_dispatch_backend_start_run",
                        "duration_ms": int((time.perf_counter() - step_started) * 1000),
                        "worker_id": self.worker_id,
                        **ctx,
                    },
                )
            except Exception as e:
                logger.error(f"Failed to mark run {run_id} as running: {e}")

            logger.info(f"Dispatched run {run_id} (session={session_id})")
            logger.info(
                "timing",
                extra={
                    "step": "run_dispatch_total",
                    "duration_ms": int((time.perf_counter() - dispatch_started) * 1000),
                    "container_mode": container_mode,
                    "container_id": container_id,
                    **ctx,
                },
            )

        except Exception as e:
            logger.error(
                f"Failed to dispatch run {run_id} (session={session_id}): "
                f"{type(e).__name__}: {e}",
                exc_info=True,
            )
            try:
                await self.backend_client.fail_run(
                    run_id=run_id, worker_id=self.worker_id, error_message=str(e)
                )
            except Exception as fail_err:
                logger.error(f"Failed to mark run {run_id} as failed: {fail_err}")

            try:
                await self.container_pool.cancel_task(session_id)
            except Exception as cancel_err:
                logger.error(
                    f"Failed to cancel task for session {session_id}: {cancel_err}"
                )
