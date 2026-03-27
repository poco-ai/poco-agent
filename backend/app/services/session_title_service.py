import logging
import unicodedata
import uuid
from typing import Any, Literal

import httpx
from anthropic import Anthropic

from app.core.settings import get_settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an assistant skilled in conversation. "
    "You need to summarize the user's conversation into a title within 10 words. "
    "The language of the title should be consistent with the user's primary language. "
    "Return only the title as plain text, without punctuation or special symbols, "
    "and without any prefixes, quotes, or extra lines."
)


class SessionTitleService:
    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = (settings.anthropic_api_key or "").strip()
        self._auth_token = (settings.anthropic_auth_token or "").strip()
        self._auth_mode = self._resolve_auth_mode()
        self._enabled = self._auth_mode is not None
        self._base_url = self._normalize_base_url(settings.anthropic_base_url)
        self._messages_url = f"{self._base_url}/v1/messages"

        self._client: Anthropic | None = None
        self._model = settings.default_model
        if not self._enabled:
            logger.warning("Anthropic credential is not set; title generation disabled")
        elif self._auth_mode == "api_key":
            self._client = Anthropic(
                api_key=self._api_key,
                base_url=self._base_url,
                timeout=15.0,
                max_retries=2,
            )

    @staticmethod
    def _normalize_base_url(raw_base_url: str | None) -> str:
        base_url = (raw_base_url or "").strip() or "https://api.anthropic.com"
        base_url = base_url.rstrip("/")
        # The SDK expects a base URL without a trailing "/v1".
        if base_url.endswith("/v1"):
            base_url = base_url[: -len("/v1")]
        return base_url

    def _resolve_auth_mode(self) -> Literal["token", "api_key"] | None:
        if self._auth_token:
            return "token"
        if self._api_key:
            return "api_key"
        return None

    def _build_messages_headers(self) -> dict[str, str]:
        headers = {
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        if self._auth_mode == "token":
            headers["authorization"] = f"Bearer {self._auth_token}"
        elif self._auth_mode == "api_key":
            headers["x-api-key"] = self._api_key
        return headers

    def generate_and_update(self, session_id: uuid.UUID, prompt: str) -> None:
        if not prompt or not prompt.strip():
            return

        # Delay database imports so auth-only usage does not require DB initialization.
        from app.core.database import SessionLocal
        from app.repositories.session_repository import SessionRepository

        title = self._generate_title(prompt)
        if not title:
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
            db_session.title = title
            db.commit()
            logger.info("Generated title for session %s", session_id)
        except Exception as exc:
            logger.exception("Failed to persist session title: %s", exc)
        finally:
            db.close()

    def _generate_title(self, prompt: str) -> str | None:
        if not self._enabled:
            return None

        content: str | None
        try:
            if self._auth_mode == "token":
                content = self._generate_title_with_token(prompt)
            else:
                content = self._generate_title_with_api_key(prompt)
        except Exception as exc:
            logger.exception("Anthropic title generation failed: %s", exc)
            return None

        if not content:
            return None

        cleaned = self._sanitize_title(content)
        if not cleaned:
            return None
        return cleaned

    def _generate_title_with_api_key(self, prompt: str) -> str | None:
        if self._client is None:
            return None

        message = self._client.messages.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            system=SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=32,
        )
        return self._extract_text_content(getattr(message, "content", []) or [])

    def _generate_title_with_token(self, prompt: str) -> str | None:
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "system": SYSTEM_PROMPT,
            "temperature": 0.2,
            "max_tokens": 32,
        }

        # The Python SDK documents API-key auth; use direct HTTP for Bearer-token auth.
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                self._messages_url,
                headers=self._build_messages_headers(),
                json=payload,
            )

        if response.status_code >= 400:
            logger.error(
                "Anthropic title generation failed: %s",
                self._extract_upstream_error_message(response),
            )
            return None

        try:
            message = response.json()
        except ValueError:
            logger.error("Anthropic title generation failed: invalid JSON response")
            return None

        if not isinstance(message, dict):
            logger.error("Anthropic title generation failed: unexpected response shape")
            return None

        return self._extract_text_content(message.get("content"))

    @staticmethod
    def _extract_upstream_error_message(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            payload = None

        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                message = error.get("message")
                if isinstance(message, str) and message.strip():
                    return message.strip()
            message = payload.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()

        text = response.text.strip()
        if text:
            return text
        return f"HTTP {response.status_code}"

    @staticmethod
    def _extract_text_content(content_blocks: Any) -> str | None:
        if not isinstance(content_blocks, list):
            return None

        text_parts: list[str] = []
        for block in content_blocks:
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
        return content or None

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
