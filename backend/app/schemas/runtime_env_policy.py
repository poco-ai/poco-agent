from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


RuntimeEnvPolicyMode = Literal["disabled", "opt_in"]


class RuntimeEnvPolicyResponse(BaseModel):
    mode: RuntimeEnvPolicyMode
    allowlist_patterns: list[str] = Field(default_factory=list)
    denylist_patterns: list[str] = Field(default_factory=list)
    protected_keys: list[str] = Field(default_factory=list)
    protected_prefixes: list[str] = Field(default_factory=list)
    updated_at: datetime | None = None


class RuntimeEnvPolicyUpdateRequest(BaseModel):
    mode: RuntimeEnvPolicyMode
    allowlist_patterns: list[str] = Field(default_factory=list)
    denylist_patterns: list[str] = Field(default_factory=list)
