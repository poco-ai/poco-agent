from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.core.deps import require_internal_token
from app.core.settings import get_settings
from app.schemas.response import Response, ResponseSchema
from app.schemas.schedule import (
    ScheduleJobInfo,
    ScheduleRuleInfo,
    SchedulesResponse,
)
from app.scheduler.pull_schedule_config import (
    IntervalPullRule,
    WindowPullRule,
    default_pull_schedule_config_from_settings,
    load_pull_schedule_config,
)
from app.scheduler.pull_schedule_state import get_current_pull_schedule_config
from app.scheduler.scheduler_config import scheduler

router = APIRouter(
    prefix="/schedules",
    tags=["schedules"],
    dependencies=[Depends(require_internal_token)],
)


def _build_job_info(job_id: str) -> ScheduleJobInfo | None:
    job = scheduler.get_job(job_id)
    if not job:
        return None
    return ScheduleJobInfo(
        job_id=job_id,
        trigger=str(job.trigger),
        next_run_time=job.next_run_time,
    )


@router.get("", response_model=ResponseSchema[SchedulesResponse])
async def get_schedules() -> JSONResponse:
    """Get effective scheduling rules from Executor Manager (source of truth)."""
    settings = get_settings()

    config = get_current_pull_schedule_config()
    if not config:
        config = load_pull_schedule_config(settings.schedule_config_path)
    if not config:
        config = default_pull_schedule_config_from_settings(settings)

    rules: list[ScheduleRuleInfo] = []

    for rule in config.rules:
        effective_enabled = bool(config.enabled and rule.enabled)

        if isinstance(rule, IntervalPullRule):
            job_id = f"pull-{rule.id}"
            jobs = [j for j in [_build_job_info(job_id)] if j]
            rules.append(
                ScheduleRuleInfo(
                    id=rule.id,
                    kind="interval",
                    enabled=effective_enabled,
                    schedule_modes=rule.schedule_modes,
                    seconds=rule.seconds,
                    start_immediately=rule.start_immediately,
                    jobs=jobs,
                )
            )
            continue

        if isinstance(rule, WindowPullRule):
            open_job_id = f"pull-{rule.id}-open"
            poll_job_id = f"pull-{rule.id}-poll"
            jobs = [
                j
                for j in [_build_job_info(open_job_id), _build_job_info(poll_job_id)]
                if j
            ]
            rules.append(
                ScheduleRuleInfo(
                    id=rule.id,
                    kind="window",
                    enabled=effective_enabled,
                    schedule_modes=rule.schedule_modes,
                    cron=rule.cron,
                    timezone=rule.timezone,
                    window_minutes=rule.window_minutes,
                    poll_interval_seconds=rule.poll_interval_seconds,
                    bootstrap_lookback_hours=rule.bootstrap_lookback_hours,
                    bootstrap_max_iterations=rule.bootstrap_max_iterations,
                    jobs=jobs,
                )
            )
            continue

    result = SchedulesResponse(rules=rules)
    return Response.success(data=result.model_dump(), message="Schedules retrieved")
