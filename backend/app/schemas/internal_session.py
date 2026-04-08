from pydantic import BaseModel, Field


class InternalSessionStatusUpdateRequest(BaseModel):
    status: str = Field(min_length=1, max_length=50)
