from pydantic import BaseModel, Field


class SkillConfigResolveRequest(BaseModel):
    """Request to resolve skills for execution."""

    skill_ids: list[int] = Field(default_factory=list)
