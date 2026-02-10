from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Poco IM")
    app_version: str = Field(default="0.1.0")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str | None = Field(default=None, alias="LOG_LEVEL")
    uvicorn_access_log: bool = Field(default=False, alias="UVICORN_ACCESS_LOG")

    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8002, alias="PORT")

    database_url: str = Field(default="sqlite:///./im.db", alias="DATABASE_URL")

    backend_url: str = Field(default="http://localhost:8000", alias="BACKEND_URL")
    backend_user_id: str = Field(default="default", alias="BACKEND_USER_ID")
    frontend_public_url: str = Field(
        default="http://localhost:3000", alias="FRONTEND_PUBLIC_URL"
    )
    frontend_default_language: str = Field(default="zh", alias="FRONTEND_DEFAULT_LANG")

    # Polling intervals
    poll_user_input_interval_seconds: float = Field(
        default=2.0, alias="POLL_USER_INPUT_INTERVAL_SECONDS"
    )
    poll_sessions_recent_interval_seconds: float = Field(
        default=5.0, alias="POLL_SESSIONS_RECENT_INTERVAL_SECONDS"
    )
    poll_sessions_full_interval_seconds: float = Field(
        default=300.0, alias="POLL_SESSIONS_FULL_INTERVAL_SECONDS"
    )
    poll_http_timeout_seconds: float = Field(
        default=10.0, alias="POLL_HTTP_TIMEOUT_SECONDS"
    )

    # Telegram bot integration
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_webhook_secret_token: str | None = Field(
        default=None, alias="TELEGRAM_WEBHOOK_SECRET_TOKEN"
    )

    # Feishu bot integration
    feishu_enabled: bool = Field(default=True, alias="FEISHU_ENABLED")
    feishu_app_id: str = Field(default="", alias="FEISHU_APP_ID")
    feishu_app_secret: str = Field(default="", alias="FEISHU_APP_SECRET")
    feishu_verification_token: str | None = Field(
        default=None, alias="FEISHU_VERIFICATION_TOKEN"
    )
    feishu_open_base_url: str = Field(
        default="https://open.feishu.cn",
        alias="FEISHU_OPEN_BASE_URL",
    )

    # DingTalk bot integration
    dingtalk_enabled: bool = Field(default=True, alias="DINGTALK_ENABLED")
    dingtalk_webhook_token: str | None = Field(
        default=None, alias="DINGTALK_WEBHOOK_TOKEN"
    )
    dingtalk_stream_enabled: bool = Field(default=True, alias="DINGTALK_STREAM_ENABLED")
    dingtalk_stream_subscribe_events: bool = Field(
        default=False, alias="DINGTALK_STREAM_SUBSCRIBE_EVENTS"
    )
    # DingTalk OpenAPI (required for proactive messages via conversationId)
    dingtalk_app_key: str | None = Field(default=None, alias="DINGTALK_APP_KEY")
    dingtalk_app_secret: str | None = Field(default=None, alias="DINGTALK_APP_SECRET")
    dingtalk_robot_code: str | None = Field(default=None, alias="DINGTALK_ROBOT_CODE")
    dingtalk_open_base_url: str = Field(
        default="https://api.dingtalk.com",
        alias="DINGTALK_OPEN_BASE_URL",
    )

    # Optional outbound-only webhook integrations (notifications only)
    feishu_webhook_url: str | None = Field(default=None, alias="FEISHU_WEBHOOK_URL")
    dingtalk_webhook_url: str | None = Field(default=None, alias="DINGTALK_WEBHOOK_URL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
