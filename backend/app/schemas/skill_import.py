from pydantic import BaseModel, Field


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
