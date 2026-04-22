from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.settings import Settings, get_settings
from app.schemas.model_config import (
    ModelConfigResponse,
    ModelDefinitionResponse,
    ModelProviderResponse,
)
from app.services.env_var_service import EnvVarService


@dataclass(frozen=True)
class ProviderSpec:
    provider_id: str
    display_name: str
    api_key_env_key: str
    base_url_env_key: str
    default_base_url: str
    api_key_settings_fields: tuple[str, ...] = ()
    base_url_settings_fields: tuple[str, ...] = ()
    known_models: tuple[tuple[str, str], ...] = ()
    legacy_api_key_env_keys: tuple[str, ...] = ()
    legacy_base_url_env_keys: tuple[str, ...] = ()


PROVIDER_SPECS: tuple[ProviderSpec, ...] = (
    ProviderSpec(
        provider_id="anthropic",
        display_name="Anthropic",
        api_key_env_key="ANTHROPIC_API_KEY",
        base_url_env_key="ANTHROPIC_BASE_URL",
        default_base_url="https://api.anthropic.com",
        api_key_settings_fields=("anthropic_api_key",),
        base_url_settings_fields=("anthropic_base_url",),
        known_models=(
            ("claude-sonnet-4-6", "Claude Sonnet 4.6"),
            ("claude-opus-4-6", "Claude Opus 4.6"),
        ),
    ),
    ProviderSpec(
        provider_id="glm",
        display_name="GLM",
        api_key_env_key="GLM_API_KEY",
        base_url_env_key="GLM_BASE_URL",
        default_base_url="https://open.bigmodel.cn/api/anthropic",
        known_models=(
            ("glm-4.7", "GLM-4.7"),
            ("glm-5", "GLM-5"),
        ),
    ),
    ProviderSpec(
        provider_id="minimax",
        display_name="MiniMax",
        api_key_env_key="MINIMAX_API_KEY",
        base_url_env_key="MINIMAX_BASE_URL",
        default_base_url="https://api.minimaxi.com/anthropic",
        known_models=(("MiniMax-M2.5", "MiniMax M2.5"),),
    ),
    ProviderSpec(
        provider_id="deepseek",
        display_name="DeepSeek",
        api_key_env_key="DEEPSEEK_API_KEY",
        base_url_env_key="DEEPSEEK_BASE_URL",
        default_base_url="https://api.deepseek.com/anthropic",
        known_models=(
            ("deepseek-chat", "DeepSeek Chat"),
            ("deepseek-reasoner", "DeepSeek Reasoner"),
        ),
    ),
)

PROVIDER_SPEC_MAP = {spec.provider_id: spec for spec in PROVIDER_SPECS}
MODEL_NAME_INDEX = {
    model_id: display_name
    for spec in PROVIDER_SPECS
    for model_id, display_name in spec.known_models
}


def infer_provider_id(model_id: str) -> str | None:
    value = (model_id or "").strip()
    if not value:
        return None

    lowered = value.lower()
    if lowered.startswith("claude-"):
        return "anthropic"
    if lowered.startswith("glm-") or value.startswith("GLM-"):
        return "glm"
    if lowered.startswith("minimax-") or value.startswith("MiniMax-"):
        return "minimax"
    if lowered.startswith("deepseek-"):
        return "deepseek"
    return None


def humanize_model_name(model_id: str) -> str:
    known = MODEL_NAME_INDEX.get(model_id)
    if known:
        return known

    value = (model_id or "").strip()
    if not value:
        return model_id

    parts = value.replace("_", "-").split("-")
    return " ".join(
        part.upper() if part.isalpha() and len(part) <= 4 else part for part in parts
    )


def get_allowed_model_ids(
    settings: Settings | None = None,
    *,
    default_model: str | None = None,
    model_list: list[str] | None = None,
) -> list[str]:
    active_settings = settings or get_settings()
    ordered: list[str] = []
    seen: set[str] = set()

    def push(value: str | None) -> None:
        clean = (value or "").strip()
        provider_id = infer_provider_id(clean)
        if (
            not clean
            or clean in seen
            or provider_id is None
            or provider_id not in PROVIDER_SPEC_MAP
        ):
            return
        seen.add(clean)
        ordered.append(clean)

    push(default_model if default_model is not None else active_settings.default_model)
    source_model_list = (
        model_list if model_list is not None else active_settings.model_list
    )
    for item in source_model_list or []:
        push(item)

    return ordered


def _build_model_definition(
    model_id: str,
    provider_id: str,
) -> ModelDefinitionResponse:
    return ModelDefinitionResponse(
        model_id=model_id,
        display_name=humanize_model_name(model_id),
        provider_id=provider_id,
    )


def _first_non_empty(mapping: dict[str, str], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = (mapping.get(key) or "").strip()
        if value:
            return value
    return ""


class ModelConfigService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.env_var_service = EnvVarService()

    def get_model_config(self, db: Session, user_id: str) -> ModelConfigResponse:
        del user_id

        system_env_values = self.env_var_service.get_system_env_map(db)
        effective_default_model = (
            system_env_values.get("DEFAULT_MODEL") or self.settings.default_model or ""
        ).strip()
        effective_model_list = self._parse_model_list(
            system_env_values.get("MODEL_LIST"),
            fallback=self.settings.model_list,
        )

        models: list[ModelDefinitionResponse] = []
        provider_model_ids: dict[str, list[str]] = {}
        for model_id in get_allowed_model_ids(
            self.settings,
            default_model=effective_default_model,
            model_list=effective_model_list,
        ):
            provider_id = infer_provider_id(model_id)
            if not provider_id:
                continue
            models.append(_build_model_definition(model_id, provider_id))
            provider_model_ids.setdefault(provider_id, []).append(model_id)

        providers: list[ModelProviderResponse] = []
        for spec in PROVIDER_SPECS:
            selected_model_ids = provider_model_ids.get(spec.provider_id, [])
            if not selected_model_ids:
                continue
            provider_state = self._build_provider_response(
                spec=spec,
                system_env_values=system_env_values,
                selected_model_ids=selected_model_ids,
            )
            providers.append(provider_state)

        return ModelConfigResponse(
            default_model=effective_default_model,
            model_list=[model.model_id for model in models],
            mem0_enabled=self.settings.mem0_enabled,
            models=models,
            providers=providers,
        )

    @staticmethod
    def _parse_model_list(raw_value: str | None, *, fallback: list[str]) -> list[str]:
        if raw_value is None or not raw_value.strip():
            return fallback
        return [
            item.strip()
            for item in raw_value.replace("\n", ",").split(",")
            if item.strip()
        ]

    def _build_provider_response(
        self,
        spec: ProviderSpec,
        system_env_values: dict[str, str],
        selected_model_ids: list[str],
    ) -> ModelProviderResponse:
        api_key_candidates = (spec.api_key_env_key, *spec.legacy_api_key_env_keys)
        base_url_candidates = (spec.base_url_env_key, *spec.legacy_base_url_env_keys)
        system_key = _first_non_empty(
            system_env_values, api_key_candidates
        ) or self._get_first_settings_value(spec.api_key_settings_fields)
        credential_state = "system" if system_key else "none"

        effective_base_url = _first_non_empty(
            system_env_values, base_url_candidates
        ) or self._get_first_settings_value(spec.base_url_settings_fields)
        if effective_base_url:
            base_url_source = "system"
        else:
            effective_base_url = spec.default_base_url
            base_url_source = "default"

        selected_models = [
            _build_model_definition(model_id, spec.provider_id)
            for model_id in selected_model_ids
        ]

        return ModelProviderResponse(
            provider_id=spec.provider_id,
            display_name=spec.display_name,
            api_key_env_key=spec.api_key_env_key,
            base_url_env_key=spec.base_url_env_key,
            credential_state=credential_state,
            default_base_url=spec.default_base_url,
            effective_base_url=effective_base_url,
            base_url_source=base_url_source,
            known_models=list(spec.known_models),
            models=selected_models,
        )

    def _get_first_settings_value(self, field_names: tuple[str, ...]) -> str:
        for field_name in field_names:
            value = getattr(self.settings, field_name, None)
            normalized = str(value or "").strip()
            if normalized:
                return normalized
        return ""
