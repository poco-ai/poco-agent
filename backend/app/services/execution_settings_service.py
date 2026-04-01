from copy import deepcopy

from sqlalchemy.orm import Session

from app.models.user_execution_setting import UserExecutionSetting
from app.repositories.user_execution_setting_repository import (
    UserExecutionSettingRepository,
)
from app.schemas.execution_settings import ExecutionSettings


def _default_execution_settings() -> ExecutionSettings:
    return ExecutionSettings.model_validate(
        {
            "schema_version": "v1",
            "hooks": {
                "pipeline": [
                    {
                        "key": "workspace",
                        "phase": "message",
                        "order": 10,
                        "enabled": True,
                    },
                    {
                        "key": "todo",
                        "phase": "message",
                        "order": 20,
                        "enabled": True,
                    },
                    {
                        "key": "callback",
                        "phase": "message",
                        "order": 30,
                        "enabled": True,
                    },
                    {
                        "key": "run_snapshot",
                        "phase": "teardown",
                        "order": 100,
                        "enabled": True,
                    },
                ]
            },
        }
    )


class ExecutionSettingsService:
    def get_or_create(self, db: Session, user_id: str) -> ExecutionSettings:
        existing = UserExecutionSettingRepository.get_by_user_id(db, user_id)
        if existing is None:
            defaults = _default_execution_settings()
            record = UserExecutionSetting(
                user_id=user_id,
                schema_version=defaults.schema_version,
                settings=defaults.model_dump(mode="json"),
            )
            UserExecutionSettingRepository.create(db, record)
            db.commit()
            db.refresh(record)
            existing = record

        return ExecutionSettings.model_validate(
            {
                "schema_version": existing.schema_version,
                **(
                    deepcopy(existing.settings)
                    if isinstance(existing.settings, dict)
                    else {}
                ),
            }
        )

    def update(
        self, db: Session, user_id: str, settings: ExecutionSettings
    ) -> ExecutionSettings:
        existing = UserExecutionSettingRepository.get_by_user_id(db, user_id)
        if existing is None:
            existing = UserExecutionSetting(
                user_id=user_id,
                schema_version=settings.schema_version,
                settings=settings.model_dump(mode="json"),
            )
            UserExecutionSettingRepository.create(db, existing)
        else:
            existing.schema_version = settings.schema_version
            existing.settings = settings.model_dump(mode="json")

        db.commit()
        db.refresh(existing)
        return ExecutionSettings.model_validate(
            {
                "schema_version": existing.schema_version,
                **(
                    deepcopy(existing.settings)
                    if isinstance(existing.settings, dict)
                    else {}
                ),
            }
        )

    def resolve_for_execution(self, db: Session, user_id: str) -> dict:
        return self.get_or_create(db, user_id).model_dump(mode="json")
