from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class ToolExecutionResponse(BaseModel):
    """Tool execution response."""

    id: UUID
    message_id: int | None
    tool_use_id: str | None
    tool_name: str
    tool_input: dict[str, Any] | None
    tool_output: dict[str, Any] | None
    is_error: bool
    duration_ms: int | None
    policy_action: str | None = None
    policy_rule_id: str | None = None
    policy_reason: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("policy_action", "policy_rule_id", "policy_reason", mode="before")
    @classmethod
    def _normalize_optional_str(cls, value: object) -> str | None:
        return value if isinstance(value, str) else None


class ToolExecutionDeltaResponse(BaseModel):
    """Incremental tool execution response with composite cursor."""

    items: list[ToolExecutionResponse]
    next_after_created_at: datetime | None = None
    next_after_id: UUID | None = None
    has_more: bool = False
