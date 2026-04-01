from datetime import datetime

from pydantic import BaseModel, field_validator

from app.schemas.source import SourceInfo


class SkillCreateRequest(BaseModel):
    name: str
    entry: dict
    description: str | None = None
    scope: str | None = None


class SkillUpdateRequest(BaseModel):
    name: str | None = None
    entry: dict | None = None
    description: str | None = None
    scope: str | None = None


class SkillResponse(BaseModel):
    id: int
    name: str
    description: str | None
    entry: dict
    manifest_version: str | None = None
    manifest: dict | None = None
    entry_checksum: str | None = None
    lifecycle_state: str = "active"
    source: SourceInfo
    scope: str
    owner_user_id: str | None
    created_at: datetime
    updated_at: datetime

    @field_validator("manifest_version", "entry_checksum", mode="before")
    @classmethod
    def _normalize_optional_str(cls, value: object) -> str | None:
        return value if isinstance(value, str) else None

    @field_validator("lifecycle_state", mode="before")
    @classmethod
    def _normalize_lifecycle_state(cls, value: object) -> str:
        return value if isinstance(value, str) and value.strip() else "active"

    @field_validator("manifest", mode="before")
    @classmethod
    def _normalize_optional_manifest(cls, value: object) -> dict | None:
        return value if isinstance(value, dict) else None
