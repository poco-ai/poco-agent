import logging
import os
from typing import Literal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.core.settings import get_settings
from app.models.env_var import UserEnvVar
from app.repositories.env_var_repository import EnvVarRepository
from app.schemas.env_var import (
    EnvVarCreateRequest,
    EnvVarPublicResponse,
    EnvVarUpdateRequest,
    SystemEnvVarAdminResponse,
    SystemEnvVarCreateRequest,
    SystemEnvVarResponse,
    SystemEnvVarUpdateRequest,
)
from app.services.constants import SYSTEM_USER_ID
from app.utils.crypto import decrypt_value, encrypt_value

logger = logging.getLogger(__name__)

EnvVarScope = Literal["system", "user"]
RESERVED_USER_ENV_VAR_KEYS = frozenset(
    {
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_BASE_URL",
        "GLM_API_KEY",
        "GLM_BASE_URL",
        "MINIMAX_API_KEY",
        "MINIMAX_BASE_URL",
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_BASE_URL",
        "SKILLSMP_API_KEY",
    }
)
PROCESS_ENV_KEYS = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_BASE_URL",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "GLM_API_KEY",
    "GLM_BASE_URL",
    "MINIMAX_API_KEY",
    "MINIMAX_BASE_URL",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_BASE_URL",
    "SKILLSMP_API_KEY",
)


def _require_scope(value: str) -> EnvVarScope:
    if value not in ("system", "user"):
        raise AppException(
            error_code=ErrorCode.BAD_REQUEST,
            message=f"Invalid env var scope: {value}",
        )
    return value


def _normalize_key(key: str) -> str:
    value = (key or "").strip()
    if not value:
        raise AppException(
            error_code=ErrorCode.BAD_REQUEST,
            message="Env var key cannot be empty",
        )
    return value


def _normalize_user_value(value: str) -> str:
    v = (value or "").strip()
    if not v:
        raise AppException(
            error_code=ErrorCode.BAD_REQUEST,
            message="Env var value cannot be empty",
        )
    return v


def _ensure_user_key_allowed(key: str) -> None:
    if key in RESERVED_USER_ENV_VAR_KEYS:
        raise AppException(
            error_code=ErrorCode.BAD_REQUEST,
            message=f"Env var key is reserved: {key}",
        )


def _require_regular_user_id(user_id: str) -> None:
    if user_id == SYSTEM_USER_ID:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Reserved user id",
        )


class EnvVarService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _encrypt(self, value: str) -> str:
        return encrypt_value(value, self.settings.secret_key)

    def _decrypt(self, token: str) -> str:
        return decrypt_value(token, self.settings.secret_key)

    # ----------------------------
    # Public (UI) APIs: no secrets
    # ----------------------------

    def list_public_env_vars(
        self, db: Session, user_id: str
    ) -> list[EnvVarPublicResponse]:
        _require_regular_user_id(user_id)
        system_vars = EnvVarRepository.list_by_user_and_scope(
            db, user_id=SYSTEM_USER_ID, scope="system"
        )
        user_vars = EnvVarRepository.list_by_user_and_scope(
            db, user_id=user_id, scope="user"
        )

        items: list[EnvVarPublicResponse] = []
        for ev in system_vars:
            if ev.key in RESERVED_USER_ENV_VAR_KEYS:
                continue
            items.append(self._to_public_response(ev, is_set=self._is_set(ev)))
        for ev in user_vars:
            if ev.key in RESERVED_USER_ENV_VAR_KEYS:
                continue
            # User vars always have a non-empty value (enforced by create/update rules).
            items.append(self._to_public_response(ev, is_set=True))
        return items

    def create_user_env_var(
        self, db: Session, user_id: str, request: EnvVarCreateRequest
    ) -> EnvVarPublicResponse:
        _require_regular_user_id(user_id)
        key = _normalize_key(request.key)
        _ensure_user_key_allowed(key)
        value = _normalize_user_value(request.value)

        existing = EnvVarRepository.get_by_user_and_key(db, user_id, key)
        if existing:
            raise AppException(
                error_code=ErrorCode.ENV_VAR_ALREADY_EXISTS,
                message=f"Env var already exists: {key}",
            )

        env_var = UserEnvVar(
            user_id=user_id,
            key=key,
            value_ciphertext=self._encrypt(value),
            description=request.description,
            scope=_require_scope("user"),
        )

        try:
            EnvVarRepository.create(db, env_var)
            db.commit()
            db.refresh(env_var)
        except IntegrityError as exc:
            db.rollback()
            raise AppException(
                error_code=ErrorCode.ENV_VAR_ALREADY_EXISTS,
                message=f"Env var already exists: {key}",
            ) from exc

        return self._to_public_response(env_var, is_set=True)

    def update_user_env_var(
        self, db: Session, user_id: str, env_var_id: int, request: EnvVarUpdateRequest
    ) -> EnvVarPublicResponse:
        _require_regular_user_id(user_id)
        env_var = EnvVarRepository.get_by_id(db, env_var_id)
        if not env_var or env_var.user_id != user_id or env_var.scope != "user":
            raise AppException(
                error_code=ErrorCode.ENV_VAR_NOT_FOUND,
                message=f"Env var not found: {env_var_id}",
            )
        _ensure_user_key_allowed(env_var.key)

        if request.value is not None:
            value = _normalize_user_value(request.value)
            env_var.value_ciphertext = self._encrypt(value)
        if request.description is not None:
            env_var.description = request.description

        db.commit()
        db.refresh(env_var)
        return self._to_public_response(env_var, is_set=True)

    def delete_user_env_var(self, db: Session, user_id: str, env_var_id: int) -> None:
        _require_regular_user_id(user_id)
        env_var = EnvVarRepository.get_by_id(db, env_var_id)
        if not env_var or env_var.user_id != user_id or env_var.scope != "user":
            raise AppException(
                error_code=ErrorCode.ENV_VAR_NOT_FOUND,
                message=f"Env var not found: {env_var_id}",
            )
        EnvVarRepository.delete(db, env_var)
        db.commit()

    def _to_public_response(
        self, env_var: UserEnvVar, *, is_set: bool
    ) -> EnvVarPublicResponse:
        return EnvVarPublicResponse(
            id=env_var.id,
            user_id=env_var.user_id,
            key=env_var.key,
            description=env_var.description,
            scope=_require_scope(env_var.scope),
            is_set=bool(is_set),
            created_at=env_var.created_at,
            updated_at=env_var.updated_at,
        )

    def _is_set(self, env_var: UserEnvVar) -> bool:
        """System env vars can be "declared but unset" by storing an empty value."""
        try:
            value = self._decrypt(env_var.value_ciphertext)
        except Exception:
            logger.exception("Failed to decrypt env var")
            return False
        return bool(value.strip())

    # ---------------------------------
    # Internal APIs: secrets + env_map
    # ---------------------------------

    def get_system_env_map(self, db: Session) -> dict[str, str]:
        """Return env_map containing process env plus system-managed values only."""
        env_map = self._load_process_env_map()

        system_vars = EnvVarRepository.list_by_user_and_scope(
            db, user_id=SYSTEM_USER_ID, scope="system"
        )
        for item in system_vars:
            try:
                value = self._decrypt(item.value_ciphertext)
            except Exception:
                logger.exception("Failed to decrypt system env var: %s", item.key)
                continue
            if value.strip():
                env_map[item.key] = value

        return env_map

    def get_env_map(self, db: Session, user_id: str) -> dict[str, str]:
        """Return env_map for config resolution: system + user (user overrides system).

        Empty values are treated as "unset" and excluded from the map so that
        `${env:KEY}` fails loudly when not configured.
        """
        env_map = self.get_system_env_map(db)

        user_vars = EnvVarRepository.list_by_user_and_scope(
            db, user_id=user_id, scope="user"
        )
        for item in user_vars:
            if item.key in RESERVED_USER_ENV_VAR_KEYS:
                continue
            try:
                value = self._decrypt(item.value_ciphertext)
            except Exception:
                logger.exception("Failed to decrypt user env var: %s", item.key)
                continue
            if value.strip():
                env_map[item.key] = value
        return env_map

    def _load_process_env_map(self) -> dict[str, str]:
        env_map: dict[str, str] = {}
        for key in PROCESS_ENV_KEYS:
            value = (os.getenv(key) or "").strip()
            if value:
                env_map[key] = value
        return env_map

    def list_system_env_vars(self, db: Session) -> list[SystemEnvVarResponse]:
        return self.list_system_env_vars_internal(db)

    def list_system_env_vars_internal(self, db: Session) -> list[SystemEnvVarResponse]:
        system_vars = EnvVarRepository.list_by_user_and_scope(
            db, user_id=SYSTEM_USER_ID, scope="system"
        )
        result: list[SystemEnvVarResponse] = []
        for ev in system_vars:
            try:
                value = self._decrypt(ev.value_ciphertext)
            except Exception:
                logger.exception("Failed to decrypt system env var: %s", ev.key)
                value = ""
            result.append(
                SystemEnvVarResponse(
                    id=ev.id,
                    user_id=ev.user_id,
                    key=ev.key,
                    value=value,
                    description=ev.description,
                    scope=_require_scope(ev.scope),
                    created_at=ev.created_at,
                    updated_at=ev.updated_at,
                )
            )
        return result

    def create_system_env_var(
        self, db: Session, request: SystemEnvVarCreateRequest
    ) -> SystemEnvVarResponse:
        key = _normalize_key(request.key)
        # System vars can be empty to represent "declared but unset".
        value = (request.value or "").strip()

        existing = EnvVarRepository.get_by_user_and_key(db, SYSTEM_USER_ID, key)
        if existing:
            raise AppException(
                error_code=ErrorCode.ENV_VAR_ALREADY_EXISTS,
                message=f"System env var already exists: {key}",
            )

        env_var = UserEnvVar(
            user_id=SYSTEM_USER_ID,
            key=key,
            value_ciphertext=self._encrypt(value),
            description=request.description,
            scope=_require_scope("system"),
        )

        try:
            EnvVarRepository.create(db, env_var)
            db.commit()
            db.refresh(env_var)
        except IntegrityError as exc:
            db.rollback()
            raise AppException(
                error_code=ErrorCode.ENV_VAR_ALREADY_EXISTS,
                message=f"System env var already exists: {key}",
            ) from exc

        return SystemEnvVarResponse(
            id=env_var.id,
            user_id=env_var.user_id,
            key=env_var.key,
            value=value,
            description=env_var.description,
            scope=_require_scope(env_var.scope),
            created_at=env_var.created_at,
            updated_at=env_var.updated_at,
        )

    def update_system_env_var(
        self, db: Session, env_var_id: int, request: SystemEnvVarUpdateRequest
    ) -> SystemEnvVarResponse:
        env_var = EnvVarRepository.get_by_id(db, env_var_id)
        if (
            not env_var
            or env_var.user_id != SYSTEM_USER_ID
            or env_var.scope != "system"
        ):
            raise AppException(
                error_code=ErrorCode.ENV_VAR_NOT_FOUND,
                message=f"System env var not found: {env_var_id}",
            )

        if request.value is not None:
            value = (request.value or "").strip()
            env_var.value_ciphertext = self._encrypt(value)
        else:
            # Use existing (decrypted) value for response
            try:
                value = self._decrypt(env_var.value_ciphertext)
            except Exception:
                logger.exception("Failed to decrypt system env var")
                value = ""

        if request.description is not None:
            env_var.description = request.description

        db.commit()
        db.refresh(env_var)
        return SystemEnvVarResponse(
            id=env_var.id,
            user_id=env_var.user_id,
            key=env_var.key,
            value=value,
            description=env_var.description,
            scope=_require_scope(env_var.scope),
            created_at=env_var.created_at,
            updated_at=env_var.updated_at,
        )

    def delete_system_env_var(self, db: Session, env_var_id: int) -> None:
        env_var = EnvVarRepository.get_by_id(db, env_var_id)
        if (
            not env_var
            or env_var.user_id != SYSTEM_USER_ID
            or env_var.scope != "system"
        ):
            raise AppException(
                error_code=ErrorCode.ENV_VAR_NOT_FOUND,
                message=f"System env var not found: {env_var_id}",
            )
        EnvVarRepository.delete(db, env_var)
        db.commit()

    def _mask_secret_value(self, value: str) -> str:
        clean = (value or "").strip()
        if not clean:
            return ""
        if len(clean) <= 8:
            return "*" * len(clean)
        return f"{clean[:4]}...{clean[-4:]}"

    def list_system_env_vars_for_admin(
        self, db: Session
    ) -> list[SystemEnvVarAdminResponse]:
        system_vars = EnvVarRepository.list_by_user_and_scope(
            db, user_id=SYSTEM_USER_ID, scope="system"
        )
        result: list[SystemEnvVarAdminResponse] = []
        for ev in system_vars:
            try:
                value = self._decrypt(ev.value_ciphertext)
            except Exception:
                logger.exception("Failed to decrypt system env var: %s", ev.key)
                value = ""
            result.append(
                SystemEnvVarAdminResponse(
                    id=ev.id,
                    user_id=ev.user_id,
                    key=ev.key,
                    description=ev.description,
                    scope=_require_scope(ev.scope),
                    is_set=bool(value.strip()),
                    masked_value=self._mask_secret_value(value),
                    created_at=ev.created_at,
                    updated_at=ev.updated_at,
                )
            )
        return result
