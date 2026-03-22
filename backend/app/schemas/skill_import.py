import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.skill_marketplace import SkillsMpSkillItem


class SkillImportCandidate(BaseModel):
    """A discovered SKILL.md candidate inside an uploaded archive."""

    relative_path: str
    skill_name: str | None = None
    requires_name: bool = False
    will_overwrite: bool = False


class SkillImportDiscoverResponse(BaseModel):
    """Response for skill import discovery."""

    archive_key: str
    candidates: list[SkillImportCandidate] = Field(default_factory=list)
    preselected_relative_path: str | None = None
    skillsmp_item: SkillsMpSkillItem | None = None


class SkillImportSelection(BaseModel):
    """User selection for importing a skill candidate."""

    relative_path: str
    name_override: str | None = None


class SkillImportCommitRequest(BaseModel):
    """Request to import selected skills from a previously discovered archive."""

    archive_key: str
    selections: list[SkillImportSelection] = Field(default_factory=list)


class SkillImportResultItem(BaseModel):
    """Per-skill import result."""

    relative_path: str
    skill_name: str | None = None
    skill_id: int | None = None
    overwritten: bool = False
    status: str
    error: str | None = None


class SkillImportCommitResponse(BaseModel):
    """Response for skill import commit."""

    items: list[SkillImportResultItem] = Field(default_factory=list)


class SkillImportCommitEnqueueResponse(BaseModel):
    """Response for enqueueing a skill import commit job."""

    job_id: uuid.UUID
    status: str


class SkillImportJobResponse(BaseModel):
    """Status response for a skill import commit job."""

    job_id: uuid.UUID
    status: str
    progress: int = 0
    result: SkillImportCommitResponse | None = None
    error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
