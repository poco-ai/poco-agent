from datetime import datetime

from pydantic import BaseModel, Field


class SkillsMpSkillItem(BaseModel):
    external_id: str
    name: str
    description: str | None = None
    author: str | None = None
    author_avatar_url: str | None = None
    github_url: str | None = None
    branch: str | None = None
    relative_skill_path: str | None = None
    stars: int = 0
    forks: int = 0
    updated_at: datetime | None = None
    skillsmp_url: str
    tags: list[str] = Field(default_factory=list)


class SkillsMpSearchResponse(BaseModel):
    items: list[SkillsMpSkillItem] = Field(default_factory=list)
    page: int = 1
    page_size: int = 12
    total: int = 0
    total_pages: int = 0
    has_next: bool = False


class SkillsMpRecommendationSection(BaseModel):
    key: str
    title: str
    items: list[SkillsMpSkillItem] = Field(default_factory=list)


class SkillsMpRecommendationsResponse(BaseModel):
    sections: list[SkillsMpRecommendationSection] = Field(default_factory=list)


class SkillsMpMarketplaceStatusResponse(BaseModel):
    configured: bool = False


class SkillsMpImportDiscoverRequest(BaseModel):
    item: SkillsMpSkillItem
