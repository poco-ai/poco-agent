from typing import Literal

from pydantic import BaseModel, Field


CapabilityRecommendationType = Literal["mcp", "skill"]


class CapabilityRecommendationRequest(BaseModel):
    query: str = Field(default="", max_length=1000)
    limit: int = Field(default=3, ge=1, le=10)


class CapabilityRecommendationItem(BaseModel):
    type: CapabilityRecommendationType
    id: int
    name: str
    description: str | None = None
    score: float
    default_enabled: bool


class CapabilityRecommendationResponse(BaseModel):
    query: str
    items: list[CapabilityRecommendationItem] = Field(default_factory=list)
