from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Service configuration
    app_name: str = Field(default="Executor Manager")
    app_version: str = Field(default="0.1.0")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8001)
    debug: bool = Field(default=False, alias="DEBUG")
    cors_origins: list[str] = Field(default=["http://localhost:3000"])

    # External service URLs
    backend_url: str = Field(default="http://localhost:8000")
    executor_url: str = Field(default="http://localhost:8080")
    callback_base_url: str = Field(default="http://localhost:8001")

    # Scheduler configuration
    max_concurrent_tasks: int = Field(default=5)
    task_timeout_seconds: int = Field(default=3600)
    retry_attempts: int = Field(default=3)
    retry_delay_seconds: int = Field(default=60)
    callback_token: str = Field(default="change-this-token-in-production")
    task_pull_enabled: bool = Field(default=True, alias="TASK_PULL_ENABLED")
    # Backward compatible default pull interval (used when per-queue intervals are unset)
    task_pull_interval_seconds: int = Field(
        default=2, alias="TASK_PULL_INTERVAL_SECONDS"
    )
    task_claim_lease_seconds: int = Field(default=30, alias="TASK_CLAIM_LEASE_SECONDS")

    # Optional schedule config file (TOML/JSON). When provided, it becomes the source of truth.
    schedule_config_path: str | None = Field(default=None, alias="SCHEDULE_CONFIG_PATH")

    # Queue-based scheduling (AgentRun.schedule_mode)
    task_pull_immediate_enabled: bool = Field(
        default=True, alias="TASK_PULL_IMMEDIATE_ENABLED"
    )
    task_pull_immediate_interval_seconds: int | None = Field(
        default=None, alias="TASK_PULL_IMMEDIATE_INTERVAL_SECONDS"
    )

    task_pull_scheduled_enabled: bool = Field(
        default=True, alias="TASK_PULL_SCHEDULED_ENABLED"
    )
    task_pull_scheduled_interval_seconds: int | None = Field(
        default=None, alias="TASK_PULL_SCHEDULED_INTERVAL_SECONDS"
    )

    task_pull_nightly_enabled: bool = Field(
        default=True, alias="TASK_PULL_NIGHTLY_ENABLED"
    )
    task_pull_nightly_poll_interval_seconds: int = Field(
        default=2, alias="TASK_PULL_NIGHTLY_POLL_INTERVAL_SECONDS"
    )
    task_pull_nightly_timezone: str = Field(
        default="UTC", alias="TASK_PULL_NIGHTLY_TIMEZONE"
    )
    task_pull_nightly_start_hour: int = Field(
        default=2, alias="TASK_PULL_NIGHTLY_START_HOUR"
    )
    task_pull_nightly_start_minute: int = Field(
        default=0, alias="TASK_PULL_NIGHTLY_START_MINUTE"
    )
    task_pull_nightly_window_minutes: int = Field(
        default=360, alias="TASK_PULL_NIGHTLY_WINDOW_MINUTES"
    )

    anthropic_token: str = Field(default="", alias="ANTHROPIC_AUTH_TOKEN")
    anthropic_base_url: str = Field(
        default="https://api.anthropic.com", alias="ANTHROPIC_BASE_URL"
    )
    default_model: str = Field(
        default="claude-sonnet-4-20250514", alias="DEFAULT_MODEL"
    )
    max_executor_containers: int = Field(default=10, alias="MAX_EXECUTOR_CONTAINERS")
    executor_image: str = Field(
        default="opencowork/executor:latest", alias="EXECUTOR_IMAGE"
    )

    workspace_root: str = Field(
        default="/var/lib/opencowork/workspaces", alias="WORKSPACE_ROOT"
    )
    workspace_cleanup_enabled: bool = Field(
        default=False, alias="WORKSPACE_CLEANUP_ENABLED"
    )
    workspace_cleanup_interval_hours: int = Field(
        default=24, alias="WORKSPACE_CLEANUP_INTERVAL_HOURS"
    )
    workspace_max_age_hours: int = Field(default=24, alias="WORKSPACE_MAX_AGE_HOURS")
    workspace_archive_enabled: bool = Field(
        default=True, alias="WORKSPACE_ARCHIVE_ENABLED"
    )
    workspace_archive_days: int = Field(default=7, alias="WORKSPACE_ARCHIVE_DAYS")
    workspace_ignore_dot_files: bool = Field(
        default=True, alias="WORKSPACE_IGNORE_DOT_FILES"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
