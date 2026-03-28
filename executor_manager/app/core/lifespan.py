import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from app.core.settings import get_settings
from app.scheduler.scheduler_config import scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    logger.info("Starting APScheduler...")
    scheduler.start()
    logger.info("APScheduler started")
    logger.info(
        "scheduler_runtime_model",
        extra={
            "user_task_dispatch_model": "backend_run_queue",
            "scheduler_role": "polling_and_maintenance_only",
        },
    )

    pull_service = None
    pull_job_ids: list[str] = []
    if settings.task_pull_enabled:
        from app.scheduler.pull_job_registry import (
            register_pull_jobs,
            unregister_pull_jobs,
        )
        from app.scheduler.pull_schedule_config import (
            default_pull_schedule_config_from_settings,
            load_pull_schedule_config,
        )
        from app.services.run_pull_service import RunPullService

        logger.info("Starting run pull service...")
        pull_service = RunPullService()
        schedule_config = load_pull_schedule_config(settings.schedule_config_path)
        if not schedule_config:
            schedule_config = default_pull_schedule_config_from_settings(settings)

        pull_job_ids = register_pull_jobs(scheduler, pull_service, schedule_config)
        logger.info(
            "run_pull_jobs_registered",
            extra={
                "job_ids": pull_job_ids,
                "dispatch_model": "queue_driven",
            },
        )

    if settings.workspace_cleanup_enabled:
        from app.services.cleanup_service import CleanupService

        logger.info("Initializing workspace cleanup service...")
        CleanupService(scheduler)
        logger.info("Workspace cleanup service initialized")

    if settings.scheduled_tasks_enabled:
        from app.services.scheduled_task_dispatch_service import (
            ScheduledTaskDispatchService,
        )

        interval = max(5, int(settings.scheduled_tasks_dispatch_interval_seconds))
        logger.info(
            "Initializing scheduled task dispatch service...",
            extra={"interval_seconds": interval},
        )
        scheduled_task_dispatch_service = ScheduledTaskDispatchService()
        scheduler.add_job(
            scheduled_task_dispatch_service.dispatch_due,
            trigger="interval",
            seconds=interval,
            id="dispatch-scheduled-tasks",
            replace_existing=True,
        )
        logger.info("Scheduled task dispatch service initialized")

    yield

    if pull_service:
        from app.scheduler.pull_job_registry import unregister_pull_jobs

        logger.info("Stopping run pull service...")
        with suppress(Exception):
            unregister_pull_jobs(scheduler, pull_job_ids)
        await pull_service.shutdown()
        logger.info("Run pull service stopped")

    logger.info("Shutting down APScheduler...")
    scheduler.shutdown()
    logger.info("APScheduler shut down")
