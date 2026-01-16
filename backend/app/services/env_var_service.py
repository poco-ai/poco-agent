import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.core.settings import get_settings
from app.models.env_var import UserEnvVar
from app.repositories.env_var_repository import EnvVarRepository
from app.schemas.env_var import EnvVarCreateRequest, EnvVarUpdateRequest, EnvVarResponse
from app.utils.crypto import decrypt_value, encrypt_value

logger = logging.getLogger(__name__)


class EnvVarService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _encrypt(self, value: str) -> str:
        return encrypt_value(value, self.settings.secret_key)

    def _decrypt(self, token: str) -> str:
        return decrypt_value(token, self.settings.secret_key)

    def create_env_var(
        self, db: Session, user_id: str, request: EnvVarCreateRequest
    ) -> EnvVarResponse:
        existing = EnvVarRepository.get_by_user_and_key(db, user_id, request.key)
        if existing:
            raise AppException(
                error_code=ErrorCode.ENV_VAR_ALREADY_EXISTS,
                message=f"Env var already exists: {request.key}",
            )

        env_var = UserEnvVar(
            user_id=user_id,
            key=request.key,
            value_ciphertext=self._encrypt(request.value),
            is_secret=request.is_secret,
            description=request.description,
            scope=request.scope,
        )

        try:
            EnvVarRepository.create(db, env_var)
            db.commit()
            db.refresh(env_var)
        except IntegrityError as exc:
            db.rollback()
            raise AppException(
                error_code=ErrorCode.ENV_VAR_ALREADY_EXISTS,
                message=f"Env var already exists: {request.key}",
            ) from exc

        return self._to_response(env_var, include_secret=False)

    def update_env_var(
        self, db: Session, user_id: str, env_var_id: int, request: EnvVarUpdateRequest
    ) -> EnvVarResponse:
        env_var = EnvVarRepository.get_by_id(db, env_var_id)
        if not env_var or env_var.user_id != user_id:
            raise AppException(
                error_code=ErrorCode.ENV_VAR_NOT_FOUND,
                message=f"Env var not found: {env_var_id}",
            )

        if request.value is not None:
            env_var.value_ciphertext = self._encrypt(request.value)
        if request.is_secret is not None:
            env_var.is_secret = request.is_secret
        if request.description is not None:
            env_var.description = request.description
        if request.scope is not None:
            env_var.scope = request.scope

        db.commit()
        db.refresh(env_var)
        return self._to_response(env_var, include_secret=False)

    def delete_env_var(self, db: Session, user_id: str, env_var_id: int) -> None:
        env_var = EnvVarRepository.get_by_id(db, env_var_id)
        if not env_var or env_var.user_id != user_id:
            raise AppException(
                error_code=ErrorCode.ENV_VAR_NOT_FOUND,
                message=f"Env var not found: {env_var_id}",
            )
        EnvVarRepository.delete(db, env_var)
        db.commit()

    def list_env_vars(
        self, db: Session, user_id: str, include_secrets: bool = False
    ) -> list[EnvVarResponse]:
        env_vars = EnvVarRepository.list_by_user(db, user_id)
        return [self._to_response(ev, include_secrets) for ev in env_vars]

    def _to_response(self, env_var: UserEnvVar, include_secret: bool) -> EnvVarResponse:
        value: str | None
        if env_var.is_secret and not include_secret:
            value = "******"
        else:
            try:
                value = self._decrypt(env_var.value_ciphertext)
            except Exception:
                logger.exception("Failed to decrypt env var")
                value = None

        return EnvVarResponse(
            id=env_var.id,
            user_id=env_var.user_id,
            key=env_var.key,
            value=value,
            is_secret=env_var.is_secret,
            description=env_var.description,
            scope=env_var.scope,
            created_at=env_var.created_at,
            updated_at=env_var.updated_at,
        )
