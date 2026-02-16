from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="OpenCoWork Backend")
    app_version: str = Field(default="0.1.0")
    debug: bool = Field(default=False)
    log_level: str | None = Field(default=None, alias="LOG_LEVEL")
    log_sql: bool = Field(default=False, alias="LOG_SQL")
    uvicorn_access_log: bool = Field(default=False, alias="UVICORN_ACCESS_LOG")

    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)

    database_url: str = Field(default="sqlite:///./opencowork.db")
    db_pool_size: int = Field(default=5)
    db_max_overflow: int = Field(default=10)
    db_pool_timeout_seconds: int = Field(default=30)

    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    secret_key: str = Field(default="change-this-secret-key-in-production")
    internal_api_token: str = Field(
        default="change-this-token-in-production", alias="INTERNAL_API_TOKEN"
    )

    # External services
    executor_manager_url: str = Field(
        default="http://localhost:8001", alias="EXECUTOR_MANAGER_URL"
    )
    s3_endpoint: str | None = Field(default=None, alias="S3_ENDPOINT")
    s3_public_endpoint: str | None = Field(default=None, alias="S3_PUBLIC_ENDPOINT")
    s3_access_key: str | None = Field(default=None, alias="S3_ACCESS_KEY")
    s3_secret_key: str | None = Field(default=None, alias="S3_SECRET_KEY")
    s3_region: str = Field(default="us-east-1", alias="S3_REGION")
    s3_bucket: str | None = Field(default=None, alias="S3_BUCKET")
    s3_force_path_style: bool = Field(default=True, alias="S3_FORCE_PATH_STYLE")
    s3_presign_expires: int = Field(default=300, alias="S3_PRESIGN_EXPIRES")
    s3_connect_timeout_seconds: int = Field(
        default=5, alias="S3_CONNECT_TIMEOUT_SECONDS"
    )
    s3_read_timeout_seconds: int = Field(default=60, alias="S3_READ_TIMEOUT_SECONDS")
    s3_max_attempts: int = Field(default=3, alias="S3_MAX_ATTEMPTS")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    anthropic_base_url: str = Field(
        default="https://api.anthropic.com", alias="ANTHROPIC_BASE_URL"
    )
    default_model: str = Field(
        default="claude-sonnet-4-20250514", alias="DEFAULT_MODEL"
    )
    model_list: list[str] = Field(default_factory=list, alias="MODEL_LIST")
    max_upload_size_mb: int = Field(default=100, alias="MAX_UPLOAD_SIZE_MB")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
