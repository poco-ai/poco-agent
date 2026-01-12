from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.schemas.enums import CallbackStatus
from app.schemas.state import AgentCurrentState


class AgentCallbackRequest(BaseModel):
    """Callback request sent during agent execution."""

    session_id: str
    time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: CallbackStatus
    progress: int
    new_message: Optional[Any] = None
    state_patch: Optional[AgentCurrentState] = None
