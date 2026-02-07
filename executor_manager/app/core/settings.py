from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Service configuration
    app_name: str = Field(default="Executor Manager")
    app_version: str = Field(default="0.1.0")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8001)
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str | None = Field(default=None, alias="LOG_LEVEL")
    uvicorn_access_log: bool = Field(default=False, alias="UVICORN_ACCESS_LOG")
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
    internal_api_token: str = Field(
        default="change-this-token-in-production", alias="INTERNAL_API_TOKEN"
    )
    task_pull_enabled: bool = Field(default=True, alias="TASK_PULL_ENABLED")
    # Backward compatible default pull interval (used when per-queue intervals are unset)
    task_pull_interval_seconds: int = Field(
        default=2, alias="TASK_PULL_INTERVAL_SECONDS"
    )
    # NOTE: This lease must cover "claim -> start_run" time on the manager side. That path can
    # include staging skills/attachments + spawning the executor container, which may take
    # longer than 30s on slow networks or large repos.
    task_claim_lease_seconds: int = Field(default=180, alias="TASK_CLAIM_LEASE_SECONDS")

    # Optional schedule config file (TOML/JSON). When provided, it becomes the source of truth.
    schedule_config_path: str | None = Field(default=None, alias="SCHEDULE_CONFIG_PATH")

    # Scheduled tasks (cron) dispatch
    scheduled_tasks_enabled: bool = Field(default=True, alias="SCHEDULED_TASKS_ENABLED")
    scheduled_tasks_dispatch_interval_seconds: int = Field(
        default=30, alias="SCHEDULED_TASKS_DISPATCH_INTERVAL_SECONDS"
    )
    scheduled_tasks_dispatch_batch_size: int = Field(
        default=50, alias="SCHEDULED_TASKS_DISPATCH_BATCH_SIZE"
    )

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

    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    anthropic_token: str = Field(default="", alias="ANTHROPIC_AUTH_TOKEN")
    anthropic_base_url: str = Field(
        default="https://api.anthropic.com", alias="ANTHROPIC_BASE_URL"
    )
    default_model: str = Field(
        default="claude-sonnet-4-20250514", alias="DEFAULT_MODEL"
    )
    max_executor_containers: int = Field(default=10, alias="MAX_EXECUTOR_CONTAINERS")
    executor_image: str = Field(
        default="ghcr.io/poco-ai/poco-executor:lite", alias="EXECUTOR_IMAGE"
    )
    # Optional: dedicated executor image with desktop/browser stack enabled.
    # When set, tasks with browser_enabled=true will use this image instead of EXECUTOR_IMAGE.
    executor_browser_image: str | None = Field(
        default="ghcr.io/poco-ai/poco-executor:full", alias="EXECUTOR_BROWSER_IMAGE"
    )
    # Default desktop viewport used by the Playwright MCP inside executor containers.
    poco_browser_viewport_size: str = Field(
        default="1366x768", alias="POCO_BROWSER_VIEWPORT_SIZE"
    )
    # When the manager spawns executor containers via the Docker daemon, it maps the executor
    # service to a host port and then calls back into it. This host must be reachable from the
    # manager process itself (e.g. "localhost" on bare-metal, or "host.docker.internal" when
    # the manager runs inside a container with docker.sock mounted).
    executor_published_host: str = Field(
        default="localhost", alias="EXECUTOR_PUBLISHED_HOST"
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
    s3_endpoint: str | None = Field(default=None, alias="S3_ENDPOINT")
    s3_access_key: str | None = Field(default=None, alias="S3_ACCESS_KEY")
    s3_secret_key: str | None = Field(default=None, alias="S3_SECRET_KEY")
    s3_region: str = Field(default="us-east-1", alias="S3_REGION")
    s3_bucket: str | None = Field(default=None, alias="S3_BUCKET")
    s3_force_path_style: bool = Field(default=True, alias="S3_FORCE_PATH_STYLE")
    s3_connect_timeout_seconds: int = Field(
        default=5, alias="S3_CONNECT_TIMEOUT_SECONDS"
    )
    s3_read_timeout_seconds: int = Field(default=60, alias="S3_READ_TIMEOUT_SECONDS")
    s3_max_attempts: int = Field(default=3, alias="S3_MAX_ATTEMPTS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_anthropic_credentials(self) -> "Settings":
        """Ensure exactly one Anthropic credential is configured."""
        has_api_key = bool((self.anthropic_api_key or "").strip())
        has_auth_token = bool((self.anthropic_token or "").strip())

        if has_api_key and has_auth_token:
            raise ValueError(
                "ANTHROPIC_API_KEY and ANTHROPIC_AUTH_TOKEN are mutually exclusive; "
                "set only one."
            )
        if not has_api_key and not has_auth_token:
            raise ValueError(
                "Missing Anthropic credential; set either ANTHROPIC_API_KEY "
                "or ANTHROPIC_AUTH_TOKEN."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
