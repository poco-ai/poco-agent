import os
from typing import Any

import httpx
from fastapi import HTTPException, UploadFile

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.core.settings import get_settings
from app.schemas.audio import AudioTranscriptionResponse


class AudioTranscriptionService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _resolve_openai_api_key(self) -> str:
        api_key = (self.settings.openai_api_key or "").strip()
        if not api_key:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="OPENAI_API_KEY is required for audio transcription",
            )
        return api_key

    def _resolve_transcription_model(self) -> str:
        model = self.settings.openai_audio_transcription_model.strip()
        if not model:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="OPENAI_AUDIO_TRANSCRIPTION_MODEL is required",
            )
        return model

    def _resolve_transcription_url(self) -> str:
        base_url = (self.settings.openai_base_url or "").strip()
        if not base_url:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="OPENAI_BASE_URL is required for audio transcription",
            )

        normalized = base_url.rstrip("/")

        if normalized.endswith("/audio/transcriptions"):
            return normalized
        if normalized.endswith("/v1"):
            return f"{normalized}/audio/transcriptions"
        return f"{normalized}/v1/audio/transcriptions"

    @staticmethod
    def _normalize_language(language: str | None) -> str | None:
        value = (language or "").strip().lower()
        return value or None

    @staticmethod
    def _get_file_size(file: UploadFile) -> int | None:
        try:
            file.file.seek(0, os.SEEK_END)
            size = file.file.tell()
            file.file.seek(0)
            return size
        except Exception:
            return None

    def _extract_upstream_error_message(self, response: httpx.Response) -> str:
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
        return "Audio transcription request failed"

    async def transcribe(
        self,
        *,
        file: UploadFile,
        language: str | None = None,
    ) -> AudioTranscriptionResponse:
        max_size_bytes = self.settings.max_audio_upload_size_mb * 1024 * 1024
        size = self._get_file_size(file)
        if size is not None and size > max_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=(
                    "Audio file too large. "
                    f"Max {self.settings.max_audio_upload_size_mb}MB."
                ),
            )

        api_key = self._resolve_openai_api_key()
        model = self._resolve_transcription_model()
        target_url = self._resolve_transcription_url()

        data: dict[str, Any] = {
            "model": model,
            "response_format": "json",
        }
        normalized_language = self._normalize_language(language)
        if normalized_language is not None:
            data["language"] = normalized_language

        await file.seek(0)
        files = {
            "file": (
                file.filename or "recording.webm",
                file.file,
                file.content_type or "application/octet-stream",
            )
        }
        headers = {"Authorization": f"Bearer {api_key}"}

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    target_url,
                    headers=headers,
                    data=data,
                    files=files,
                )
        except httpx.TimeoutException as exc:
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="Audio transcription request timed out",
                details={"provider": "openai-compatible"},
            ) from exc
        except httpx.HTTPError as exc:
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="Failed to reach audio transcription provider",
                details={"provider": "openai-compatible", "error": str(exc)},
            ) from exc

        if response.status_code >= 400:
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message=self._extract_upstream_error_message(response),
                details={
                    "provider": "openai-compatible",
                    "status_code": response.status_code,
                },
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="Audio transcription provider returned invalid JSON",
                details={"provider": "openai-compatible"},
            ) from exc

        text = payload.get("text") if isinstance(payload, dict) else None
        if not isinstance(text, str) or not text.strip():
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="Audio transcription provider returned empty text",
                details={"provider": "openai-compatible"},
            )

        return AudioTranscriptionResponse(text=text.strip())
