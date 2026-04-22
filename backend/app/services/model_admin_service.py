from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.schemas.env_var import SystemEnvVarCreateRequest, SystemEnvVarUpdateRequest
from app.schemas.model_config import ModelConfigResponse
from app.services.env_var_service import EnvVarService
from app.services.model_config_service import ModelConfigService


class ModelAdminService:
    def __init__(self) -> None:
        self.env_var_service = EnvVarService()
        self.model_config_service = ModelConfigService()

    def get_model_config(self, db: Session) -> ModelConfigResponse:
        return self.model_config_service.get_model_config(db, user_id="")

    def update_model_config(
        self, db: Session, *, default_model: str, model_list: list[str]
    ) -> ModelConfigResponse:
        normalized_default = (default_model or "").strip()
        if not normalized_default:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="default_model cannot be empty",
            )
        normalized_list: list[str] = []
        seen: set[str] = set()
        for item in [normalized_default, *model_list]:
            value = (item or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            normalized_list.append(value)

        self._upsert_system_env(db, key="DEFAULT_MODEL", value=normalized_default)
        self._upsert_system_env(db, key="MODEL_LIST", value=",".join(normalized_list))
        return self.get_model_config(db)

    def _upsert_system_env(self, db: Session, *, key: str, value: str) -> None:
        existing = next(
            (
                item
                for item in self.env_var_service.list_system_env_vars(db)
                if item.key == key
            ),
            None,
        )
        if existing is None:
            self.env_var_service.create_system_env_var(
                db,
                SystemEnvVarCreateRequest(key=key, value=value),
            )
            return
        self.env_var_service.update_system_env_var(
            db,
            existing.id,
            SystemEnvVarUpdateRequest(value=value),
        )
