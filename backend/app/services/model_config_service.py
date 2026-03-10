import json
import os
from dataclasses import dataclass
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.core.settings import Settings, get_settings
from app.models.env_var import UserEnvVar
from app.models.model_provider_setting import UserModelProviderSetting
from app.repositories.env_var_repository import EnvVarRepository
from app.repositories.model_provider_setting_repository import (
    ModelProviderSettingRepository,
)
from app.schemas.model_config import (
    ModelConfigResponse,
    ModelDefinitionResponse,
    ModelProviderResponse,
    ProviderModelDiscoveryRequest,
    ProviderModelDiscoveryResponse,
    ProviderModelSettingsUpsertRequest,
)
from app.services.env_var_service import SYSTEM_USER_ID
from app.utils.crypto import decrypt_value


@dataclass(frozen=True)
class ProviderSpec:
    provider_id: str
    display_name: str
    api_key_env_key: str
    base_url_env_key: str
    default_base_url: str
    discovery_mode: str | None = None
    known_models: tuple[tuple[str, str], ...] = ()


PROVIDER_SPECS: tuple[ProviderSpec, ...] = (
    ProviderSpec(
        provider_id="anthropic",
        display_name="Anthropic",
        api_key_env_key="ANTHROPIC_API_KEY",
        base_url_env_key="ANTHROPIC_BASE_URL",
        default_base_url="https://api.anthropic.com",
        discovery_mode="anthropic",
        known_models=(
            ("claude-sonnet-4-20250514", "Claude Sonnet 4"),
            ("claude-opus-4-20250514", "Claude Opus 4"),
        ),
    ),
    ProviderSpec(
        provider_id="openai",
        display_name="OpenAI",
        api_key_env_key="OPENAI_API_KEY",
        base_url_env_key="OPENAI_BASE_URL",
        default_base_url="https://api.openai.com/v1",
        discovery_mode="openai-compatible",
        known_models=(
            ("gpt-4.1", "GPT-4.1"),
            ("gpt-4.1-mini", "GPT-4.1 Mini"),
        ),
    ),
    ProviderSpec(
        provider_id="glm",
        display_name="GLM",
        api_key_env_key="GLM_API_KEY",
        base_url_env_key="GLM_BASE_URL",
        default_base_url="https://open.bigmodel.cn/api/paas/v4/",
        known_models=(
            ("GLM-4.7", "GLM-4.7"),
            ("glm-5", "GLM-5"),
        ),
    ),
    ProviderSpec(
        provider_id="minimax",
        display_name="MiniMax",
        api_key_env_key="MINIMAX_API_KEY",
        base_url_env_key="MINIMAX_BASE_URL",
        default_base_url="https://api.minimaxi.com/v1",
        known_models=(
            ("MiniMax-M2.5", "MiniMax M2.5"),
            ("MiniMax-M2", "MiniMax M2"),
        ),
    ),
    ProviderSpec(
        provider_id="deepseek",
        display_name="DeepSeek",
        api_key_env_key="DEEPSEEK_API_KEY",
        base_url_env_key="DEEPSEEK_BASE_URL",
        default_base_url="https://api.deepseek.com",
        discovery_mode="openai-compatible",
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
    if lowered.startswith(("gpt", "o1", "o3", "o4")):
        return "openai"
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
        part.upper() if part.isalpha() and len(part) <= 4 else part
        for part in parts
    )


def get_allowed_model_ids(settings: Settings | None = None) -> list[str]:
    active_settings = settings or get_settings()
    ordered: list[str] = []
    seen: set[str] = set()

    def push(value: str | None) -> None:
        clean = (value or "").strip()
        if not clean or clean in seen:
            return
        seen.add(clean)
        ordered.append(clean)

    push(active_settings.default_model)
    for item in active_settings.model_list or []:
        push(item)

    return ordered


def _decrypt_ciphertext(ciphertext: str, secret_key: str) -> str:
    if not ciphertext:
        return ""
    return decrypt_value(ciphertext, secret_key).strip()


def _normalize_model_ids(model_ids: list[str] | None) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for item in model_ids or []:
        clean = (item or "").strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        ordered.append(clean)
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


class ModelConfigService:
    discovery_timeout_seconds: int = 10

    def __init__(self) -> None:
        self.settings = get_settings()

    def get_model_config(self, db: Session, user_id: str) -> ModelConfigResponse:
        provider_model_settings = self._load_provider_model_settings(db, user_id)
        user_env_values, system_env_values = self._load_provider_env_values(db, user_id)

        models: list[ModelDefinitionResponse] = []
        seen_keys: set[tuple[str, str]] = set()

        def push_model(model_id: str | None, provider_id: str | None = None) -> None:
            clean = (model_id or "").strip()
            resolved_provider_id = (provider_id or infer_provider_id(clean) or "").strip()
            if not clean or not resolved_provider_id:
                return
            key = (resolved_provider_id, clean)
            if key in seen_keys:
                return
            seen_keys.add(key)
            models.append(_build_model_definition(clean, resolved_provider_id))

        push_model(self.settings.default_model)
        for item in self.settings.model_list or []:
            push_model(item)
        for provider_id, model_ids in provider_model_settings.items():
            for model_id in model_ids:
                push_model(model_id, provider_id)

        providers: list[ModelProviderResponse] = []
        for spec in PROVIDER_SPECS:
            provider_state = self._build_provider_response(
                spec=spec,
                user_env_values=user_env_values,
                system_env_values=system_env_values,
                selected_model_ids=provider_model_settings.get(spec.provider_id, []),
            )
            providers.append(provider_state)

        return ModelConfigResponse(
            default_model=(self.settings.default_model or "").strip(),
            model_list=[model.model_id for model in models],
            mem0_enabled=self.settings.mem0_enabled,
            models=models,
            providers=providers,
        )

    def upsert_provider_models(
        self,
        db: Session,
        user_id: str,
        provider_id: str,
        request: ProviderModelSettingsUpsertRequest,
    ) -> ModelProviderResponse:
        spec = self._get_provider_spec(provider_id)
        model_ids = _normalize_model_ids(request.model_ids)

        setting = ModelProviderSettingRepository.get_by_user_and_provider(
            db,
            user_id=user_id,
            provider_id=provider_id,
        )

        if not model_ids:
            if setting:
                ModelProviderSettingRepository.delete(db, setting)
                db.commit()
            user_env_values, system_env_values = self._load_provider_env_values(db, user_id)
            return self._build_provider_response(
                spec=spec,
                user_env_values=user_env_values,
                system_env_values=system_env_values,
                selected_model_ids=[],
            )

        if not setting:
            setting = UserModelProviderSetting(
                user_id=user_id,
                provider_id=provider_id,
                model_ids=model_ids,
            )
            try:
                ModelProviderSettingRepository.create(db, setting)
                db.commit()
                db.refresh(setting)
            except IntegrityError as exc:
                db.rollback()
                raise AppException(
                    error_code=ErrorCode.DATABASE_ERROR,
                    message="Failed to save provider models",
                ) from exc
        else:
            setting.model_ids = model_ids
            db.commit()
            db.refresh(setting)

        user_env_values, system_env_values = self._load_provider_env_values(db, user_id)
        return self._build_provider_response(
            spec=spec,
            user_env_values=user_env_values,
            system_env_values=system_env_values,
            selected_model_ids=model_ids,
        )

    def discover_provider_models(
        self,
        db: Session,
        user_id: str,
        provider_id: str,
        request: ProviderModelDiscoveryRequest,
    ) -> ProviderModelDiscoveryResponse:
        spec = self._get_provider_spec(provider_id)
        if not spec.discovery_mode:
            return ProviderModelDiscoveryResponse(provider_id=provider_id, models=[])

        user_env_values, system_env_values = self._load_provider_env_values(db, user_id)
        api_key, base_url = self._resolve_discovery_credentials(
            spec=spec,
            user_env_values=user_env_values,
            system_env_values=system_env_values,
            request=request,
        )

        if not api_key:
            return ProviderModelDiscoveryResponse(provider_id=provider_id, models=[])

        try:
            if spec.discovery_mode == "anthropic":
                models = self._discover_anthropic_models(
                    provider_id=provider_id,
                    api_key=api_key,
                    base_url=base_url,
                )
            else:
                models = self._discover_openai_compatible_models(
                    provider_id=provider_id,
                    api_key=api_key,
                    base_url=base_url,
                )
        except AppException:
            raise
        except Exception:
            models = []

        return ProviderModelDiscoveryResponse(provider_id=provider_id, models=models)

    def _build_provider_response(
        self,
        spec: ProviderSpec,
        user_env_values: dict[str, str],
        system_env_values: dict[str, str],
        selected_model_ids: list[str],
    ) -> ModelProviderResponse:
        user_key = user_env_values.get(spec.api_key_env_key, "")
        process_key = (os.getenv(spec.api_key_env_key) or "").strip()

        if user_key:
            credential_state = "user"
        elif system_env_values.get(spec.api_key_env_key, "") or process_key:
            credential_state = "system"
        else:
            credential_state = "none"

        user_base_url = user_env_values.get(spec.base_url_env_key, "")
        system_base_url = system_env_values.get(spec.base_url_env_key, "")
        process_base_url = (os.getenv(spec.base_url_env_key) or "").strip()

        if user_base_url:
            effective_base_url = user_base_url
            base_url_source = "user"
        elif system_base_url or process_base_url:
            effective_base_url = system_base_url or process_base_url
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
            supports_model_discovery=bool(spec.discovery_mode),
            models=selected_models,
            discovered_models=[],
        )

    def _get_provider_spec(self, provider_id: str) -> ProviderSpec:
        spec = PROVIDER_SPEC_MAP.get(provider_id)
        if not spec:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Unknown provider: {provider_id}",
            )
        return spec

    def _load_provider_env_values(
        self,
        db: Session,
        user_id: str,
    ) -> tuple[dict[str, str], dict[str, str]]:
        relevant_env_keys = {
            spec.api_key_env_key for spec in PROVIDER_SPECS
        } | {spec.base_url_env_key for spec in PROVIDER_SPECS}

        system_items = self._load_env_values(
            EnvVarRepository.list_by_user_and_scope(
                db, user_id=SYSTEM_USER_ID, scope="system"
            ),
            relevant_env_keys,
        )
        user_items = self._load_env_values(
            EnvVarRepository.list_by_user_and_scope(db, user_id=user_id, scope="user"),
            relevant_env_keys,
        )
        return user_items, system_items

    def _load_provider_model_settings(
        self,
        db: Session,
        user_id: str,
    ) -> dict[str, list[str]]:
        settings = ModelProviderSettingRepository.list_by_user_id(db, user_id)
        return {
            setting.provider_id: _normalize_model_ids(setting.model_ids)
            for setting in settings
        }

    def _load_env_values(
        self,
        env_vars: list[UserEnvVar],
        relevant_keys: set[str],
    ) -> dict[str, str]:
        values: dict[str, str] = {}
        for item in env_vars:
            if item.key not in relevant_keys:
                continue
            try:
                values[item.key] = _decrypt_ciphertext(
                    item.value_ciphertext,
                    self.settings.secret_key,
                )
            except Exception:
                continue
        return values

    def _resolve_discovery_credentials(
        self,
        spec: ProviderSpec,
        user_env_values: dict[str, str],
        system_env_values: dict[str, str],
        request: ProviderModelDiscoveryRequest,
    ) -> tuple[str, str]:
        override_key = (request.api_key or "").strip()
        api_key = override_key or user_env_values.get(spec.api_key_env_key, "")
        if not api_key:
            api_key = system_env_values.get(spec.api_key_env_key, "") or (
                os.getenv(spec.api_key_env_key) or ""
            ).strip()

        if request.base_url is None:
            base_url = (
                user_env_values.get(spec.base_url_env_key, "")
                or system_env_values.get(spec.base_url_env_key, "")
                or (os.getenv(spec.base_url_env_key) or "").strip()
                or spec.default_base_url
            )
        else:
            base_url = (request.base_url or "").strip() or spec.default_base_url

        return api_key.strip(), base_url.strip()

    def _discover_openai_compatible_models(
        self,
        provider_id: str,
        api_key: str,
        base_url: str,
    ) -> list[ModelDefinitionResponse]:
        endpoint = self._join_url(base_url, "models")
        payload = self._request_json(
            endpoint,
            headers={
                "Authorization": f"Bearer {api_key}",
            },
        )
        data = payload.get("data")
        if not isinstance(data, list):
            return []

        model_ids = [
            str(item.get("id") or "").strip()
            for item in data
            if isinstance(item, dict)
        ]
        return [
            _build_model_definition(model_id, provider_id)
            for model_id in _normalize_model_ids(model_ids)
        ]

    def _discover_anthropic_models(
        self,
        provider_id: str,
        api_key: str,
        base_url: str,
    ) -> list[ModelDefinitionResponse]:
        endpoint = self._join_url(base_url, "v1/models")
        payload = self._request_json(
            endpoint,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        data = payload.get("data")
        if not isinstance(data, list):
            return []

        model_ids = [
            str(item.get("id") or "").strip()
            for item in data
            if isinstance(item, dict)
        ]
        return [
            _build_model_definition(model_id, provider_id)
            for model_id in _normalize_model_ids(model_ids)
        ]

    def _join_url(self, base_url: str, path: str) -> str:
        clean_base = (base_url or "").strip().rstrip("/")
        clean_path = path.lstrip("/")
        if not clean_base:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Base URL is required for model discovery",
            )
        if clean_base.endswith(f"/{clean_path}"):
            return clean_base
        if clean_base.endswith("/v1") and clean_path.startswith("v1/"):
            return f"{clean_base}/{clean_path.removeprefix('v1/')}"
        return urllib_parse.urljoin(f"{clean_base}/", clean_path)

    def _request_json(self, url: str, headers: dict[str, str]) -> dict:
        request = urllib_request.Request(
            url,
            headers={
                "Accept": "application/json",
                **headers,
            },
            method="GET",
        )
        try:
            with urllib_request.urlopen(
                request,
                timeout=self.discovery_timeout_seconds,
            ) as response:
                payload = response.read().decode("utf-8")
        except urllib_error.HTTPError as exc:
            if exc.code in (401, 403, 404):
                return {}
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message=f"Provider model discovery failed: {exc.code}",
            ) from exc
        except urllib_error.URLError:
            return {}

        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            return {}

        return parsed if isinstance(parsed, dict) else {}
