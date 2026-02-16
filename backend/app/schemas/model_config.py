from pydantic import BaseModel, Field


class ModelConfigResponse(BaseModel):
    """Model configuration exposed to the UI."""

    default_model: str
    model_list: list[str] = Field(default_factory=list)
