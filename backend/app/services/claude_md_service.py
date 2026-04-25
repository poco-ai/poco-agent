from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.claude_md import UserClaudeMdSetting
from app.repositories.claude_md_repository import ClaudeMdRepository
from app.schemas.claude_md import ClaudeMdResponse, ClaudeMdUpsertRequest
from app.services.constants import SYSTEM_USER_ID


class ClaudeMdService:
    """Service layer for user-level CLAUDE.md settings."""

    # Keep this conservative to avoid blowing up DB payloads / logs.
    max_bytes: int = 64 * 1024

    @staticmethod
    def _normalize_content(value: str) -> str:
        return value if isinstance(value, str) else ""

    def _validate_size(self, content: str) -> None:
        if len(content.encode("utf-8")) > self.max_bytes:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"CLAUDE.md is too large (max {self.max_bytes} bytes)",
            )

    def get_settings(self, db: Session, user_id: str) -> ClaudeMdResponse:
        """Get the stored CLAUDE.md settings for a user (defaults to disabled)."""
        setting = ClaudeMdRepository.get_by_user_id(db, user_id=user_id)
        if not setting:
            return ClaudeMdResponse(enabled=False, content="", updated_at=None)

        content = self._normalize_content(setting.content)
        enabled = bool(setting.enabled) and bool(content.strip())
        return ClaudeMdResponse(
            enabled=enabled,
            content=content,
            updated_at=setting.updated_at,
        )

    def get_effective_settings(self, db: Session, user_id: str) -> ClaudeMdResponse:
        setting = ClaudeMdRepository.get_by_user_id(db, user_id=user_id)
        if setting and ((setting.content or "").strip() or setting.enabled):
            content = self._normalize_content(setting.content)
            enabled = bool(setting.enabled) and bool(content.strip())
            return ClaudeMdResponse(
                enabled=enabled,
                content=content,
                updated_at=setting.updated_at,
            )

        system_setting = ClaudeMdRepository.get_by_user_id(db, user_id=SYSTEM_USER_ID)
        if not system_setting:
            return ClaudeMdResponse(enabled=False, content="", updated_at=None)

        system_content = self._normalize_content(system_setting.content)
        effective_enabled = bool(system_setting.enabled) and bool(
            system_content.strip()
        )
        return ClaudeMdResponse(
            enabled=effective_enabled,
            content=system_content,
            updated_at=system_setting.updated_at,
        )

    def upsert_settings(
        self, db: Session, user_id: str, request: ClaudeMdUpsertRequest
    ) -> ClaudeMdResponse:
        content = self._normalize_content(request.content)
        self._validate_size(content)

        enabled = bool(request.enabled)

        setting = ClaudeMdRepository.get_by_user_id(db, user_id=user_id)
        if not setting:
            setting = UserClaudeMdSetting(
                user_id=user_id,
                enabled=enabled,
                content=content,
            )
            try:
                ClaudeMdRepository.create(db, setting)
                db.commit()
                db.refresh(setting)
            except IntegrityError as exc:
                db.rollback()
                raise AppException(
                    error_code=ErrorCode.DATABASE_ERROR,
                    message="Failed to create CLAUDE.md settings",
                ) from exc
        else:
            setting.enabled = enabled
            setting.content = content
            db.commit()
            db.refresh(setting)

        # Effective enablement depends on both flag and content.
        effective_enabled = bool(setting.enabled) and bool(setting.content.strip())
        return ClaudeMdResponse(
            enabled=effective_enabled,
            content=setting.content,
            updated_at=setting.updated_at,
        )

    def delete_settings(self, db: Session, user_id: str) -> None:
        setting = ClaudeMdRepository.get_by_user_id(db, user_id=user_id)
        if not setting:
            return
        ClaudeMdRepository.delete(db, setting)
        db.commit()
