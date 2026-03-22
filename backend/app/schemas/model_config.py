from typing import Literal

from pydantic import BaseModel, Field


CredentialState = Literal["none", "system", "user"]
BaseUrlSource = Literal["default", "system", "user"]


class ModelDefinitionResponse(BaseModel):
    """A model option exposed to the UI."""

    model_id: str
    display_name: str
    provider_id: str
    requires_credentials: bool = True
    supports_custom_base_url: bool = True


class ModelProviderResponse(BaseModel):
    """Provider configuration metadata exposed to the UI."""

    provider_id: str
    display_name: str
    api_key_env_key: str
    base_url_env_key: str
    credential_state: CredentialState = "none"
    default_base_url: str
    effective_base_url: str
    base_url_source: BaseUrlSource = "default"
    known_models: list[tuple[str, str]] = Field(default_factory=list)
    models: list[ModelDefinitionResponse] = Field(default_factory=list)


class ModelConfigResponse(BaseModel):
    """Model configuration exposed to the UI."""

    default_model: str
    model_list: list[str] = Field(default_factory=list)
    mem0_enabled: bool = False
    models: list[ModelDefinitionResponse] = Field(default_factory=list)
    providers: list[ModelProviderResponse] = Field(default_factory=list)


class ProviderModelSettingsUpsertRequest(BaseModel):
    """Persist the provider-scoped model list for the current user."""

    model_ids: list[str] = Field(default_factory=list)
