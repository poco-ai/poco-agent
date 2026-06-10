import logging
import unicodedata
import uuid
from dataclasses import dataclass

from anthropic import Anthropic

from app.core.database import SessionLocal
from app.core.settings import get_settings
from app.repositories.session_repository import SessionRepository
from app.services.env_var_service import EnvVarService
from app.services.model_config_service import (
    PROVIDER_SPECS,
    PROVIDER_SPEC_MAP,
    ProviderSpec,
    infer_provider_id,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an assistant skilled in conversation. "
    "You need to summarize the user's conversation into a title within 10 words. "
    "The language of the title should be consistent with the user's primary language. "
    "Return only the title as plain text, without punctuation or special symbols, "
    "and without any prefixes, quotes, or extra lines."
)


@dataclass(frozen=True)
class TitleModelConfig:
    provider_id: str
    model: str
    api_key: str
    base_url: str


class SessionTitleService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.env_var_service = EnvVarService()

    def generate_and_update(self, session_id: uuid.UUID, prompt: str) -> None:
        if not prompt or not prompt.strip():
            return

        db = SessionLocal()
        try:
            db_session = SessionRepository.get_by_id(db, session_id)
            if not db_session:
                logger.warning(
                    "Title generation skipped: session not found %s", session_id
                )
                return
            if db_session.title:
                return

            model_config = self._resolve_model_config(db)
            if model_config is None:
                return

            title = self._generate_title(prompt, model_config)
            if not title:
                return

            db_session.title = title
            db.commit()
            logger.info("Generated title for session %s", session_id)
        except Exception as exc:
            logger.exception("Failed to persist session title: %s", exc)
        finally:
            db.close()

    def _resolve_model_config(self, db) -> TitleModelConfig | None:
        env_map = self.env_var_service.get_system_env_map(db)
        candidate_models = self._build_candidate_models(env_map)

        for model in candidate_models:
            provider_id = infer_provider_id(model)
            if not provider_id:
                continue
            spec = PROVIDER_SPEC_MAP.get(provider_id)
            if spec is None:
                continue
            resolved = self._resolve_provider_config(spec, model, env_map)
            if resolved is not None:
                return resolved

        for spec in PROVIDER_SPECS:
            fallback_model = self._first_model_for_provider(
                provider_id=spec.provider_id,
                candidate_models=candidate_models,
            )
            if not fallback_model:
                continue
            resolved = self._resolve_provider_config(spec, fallback_model, env_map)
            if resolved is not None:
                logger.info(
                    "Using %s for title generation because the default model provider has no configured credential",
                    spec.provider_id,
                )
                return resolved

        logger.warning(
            "No configured model provider credential found; title generation disabled"
        )
        return None

    def _build_candidate_models(self, env_map: dict[str, str]) -> list[str]:
        candidates: list[str] = []

        def push(value: str | None) -> None:
            normalized = (value or "").strip()
            if normalized and normalized not in candidates:
                candidates.append(normalized)

        push(env_map.get("DEFAULT_MODEL") or self.settings.default_model)
        raw_model_list = env_map.get("MODEL_LIST")
        model_list = (
            [
                item.strip()
                for item in raw_model_list.replace("\n", ",").split(",")
                if item.strip()
            ]
            if raw_model_list and raw_model_list.strip()
            else self.settings.model_list
        )
        for item in model_list:
            push(item)
        return candidates

    def _resolve_provider_config(
        self,
        spec: ProviderSpec,
        model: str,
        env_map: dict[str, str],
    ) -> TitleModelConfig | None:
        api_key = self._first_env_value(
            env_map,
            (spec.api_key_env_key, *spec.legacy_api_key_env_keys),
        ) or self._first_settings_value(spec.api_key_settings_fields)
        if not api_key:
            return None

        base_url = (
            self._first_env_value(
                env_map,
                (spec.base_url_env_key, *spec.legacy_base_url_env_keys),
            )
            or self._first_settings_value(spec.base_url_settings_fields)
            or spec.default_base_url
        )
        return TitleModelConfig(
            provider_id=spec.provider_id,
            model=model,
            api_key=api_key,
            base_url=self._normalize_anthropic_base_url(base_url),
        )

    @staticmethod
    def _first_model_for_provider(
        *,
        provider_id: str,
        candidate_models: list[str],
    ) -> str | None:
        for model in candidate_models:
            if infer_provider_id(model) == provider_id:
                return model
        spec = PROVIDER_SPEC_MAP.get(provider_id)
        if spec and spec.known_models:
            return spec.known_models[0][0]
        return None

    @staticmethod
    def _first_env_value(env_map: dict[str, str], keys: tuple[str, ...]) -> str:
        for key in keys:
            value = (env_map.get(key) or "").strip()
            if value:
                return value
        return ""

    def _first_settings_value(self, field_names: tuple[str, ...]) -> str:
        for field_name in field_names:
            value = getattr(self.settings, field_name, None)
            normalized = str(value or "").strip()
            if normalized:
                return normalized
        return ""

    @staticmethod
    def _normalize_anthropic_base_url(base_url: str) -> str:
        normalized = (base_url or "").strip().rstrip("/")
        if normalized.endswith("/v1"):
            return normalized[: -len("/v1")]
        return normalized

    def _generate_title(
        self,
        prompt: str,
        model_config: TitleModelConfig,
    ) -> str | None:
        client = Anthropic(
            api_key=model_config.api_key,
            base_url=model_config.base_url,
            timeout=15.0,
            max_retries=2,
        )
        try:
            message = client.messages.create(
                model=model_config.model,
                messages=[{"role": "user", "content": prompt}],
                system=SYSTEM_PROMPT,
                temperature=0.2,
                max_tokens=32,
            )
        except Exception as exc:
            logger.exception(
                "Title generation failed with provider %s: %s",
                model_config.provider_id,
                exc,
            )
            return None

        text_parts: list[str] = []
        for block in getattr(message, "content", []) or []:
            if isinstance(block, dict):
                block_type = block.get("type")
                text = block.get("text")
            else:
                block_type = getattr(block, "type", None)
                text = getattr(block, "text", None)

            if block_type != "text":
                continue
            if isinstance(text, str) and text:
                text_parts.append(text)

        content = "".join(text_parts).strip()
        cleaned = self._sanitize_title(content)
        if not cleaned:
            return None
        return cleaned

    def _sanitize_title(self, text: str) -> str:
        text = text.replace("\r", " ").replace("\n", " ").strip()
        text = text.replace('"', "").replace("'", "")

        cleaned_chars: list[str] = []
        for ch in text:
            if ch.isspace():
                cleaned_chars.append(" ")
                continue
            category = unicodedata.category(ch)
            if category.startswith("P") or category.startswith("S"):
                continue
            cleaned_chars.append(ch)

        cleaned = "".join(cleaned_chars)
        cleaned = " ".join(cleaned.split())

        if not cleaned:
            return ""

        words = cleaned.split(" ")
        if len(words) > 10:
            cleaned = " ".join(words[:10])
        return cleaned
