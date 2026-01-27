import asyncio
import logging
import os
import socket
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.settings import get_settings
from app.scheduler.task_dispatcher import TaskDispatcher
from app.services.backend_client import BackendClient
from app.services.executor_client import ExecutorClient
from app.services.config_resolver import ConfigResolver
from app.services.skill_stager import SkillStager
from app.services.attachment_stager import AttachmentStager

logger = logging.getLogger(__name__)


class RunPullService:
    """Background service that pulls queued runs from Backend and dispatches them."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.backend_client = BackendClient()
        self.executor_client = ExecutorClient()
        self.container_pool = TaskDispatcher.get_container_pool()
        self.config_resolver = ConfigResolver(self.backend_client)
        self.skill_stager = SkillStager()
        self.attachment_stager = AttachmentStager()

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
                claim = await self.backend_client.claim_run(
                    worker_id=self.worker_id,
                    lease_seconds=lease_seconds,
                    schedule_modes=schedule_modes,
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
        run = claim.get("run") or {}
        run_id = run.get("run_id")
        session_id = run.get("session_id")
        user_id = claim.get("user_id") or ""
        prompt = claim.get("prompt") or ""
        config_snapshot = claim.get("config_snapshot") or {}
        sdk_session_id = claim.get("sdk_session_id")

        if not run_id or not session_id or not user_id or not prompt:
            logger.error(f"Invalid claim payload: {claim}")
            return

        container_mode = config_snapshot.get("container_mode", "ephemeral")
        container_id = config_snapshot.get("container_id")

        callback_url = f"{self.settings.callback_base_url}/api/v1/callback"

        try:
            resolved_config = await self.config_resolver.resolve(
                user_id,
                config_snapshot,
                session_id=session_id,
                run_id=str(run_id),
            )
            staged_skills = self.skill_stager.stage_skills(
                user_id=user_id,
                session_id=session_id,
                skills=resolved_config.get("skill_files") or {},
            )
            resolved_config["skill_files"] = staged_skills
            staged_inputs = self.attachment_stager.stage_inputs(
                user_id=user_id,
                session_id=session_id,
                inputs=resolved_config.get("input_files") or [],
            )
            resolved_config["input_files"] = staged_inputs

            executor_url, _ = await self.container_pool.get_or_create_container(
                session_id=session_id,
                user_id=user_id,
                container_mode=container_mode,
                container_id=container_id,
            )

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
            )
            try:
                await self.backend_client.start_run(
                    run_id=run_id, worker_id=self.worker_id
                )
            except Exception as e:
                logger.error(f"Failed to mark run {run_id} as running: {e}")

            logger.info(f"Dispatched run {run_id} (session={session_id})")

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
