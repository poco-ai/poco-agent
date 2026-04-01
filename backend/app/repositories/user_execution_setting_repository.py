from sqlalchemy.orm import Session

from app.models.user_execution_setting import UserExecutionSetting


class UserExecutionSettingRepository:
    @staticmethod
    def get_by_user_id(
        session_db: Session, user_id: str
    ) -> UserExecutionSetting | None:
        return (
            session_db.query(UserExecutionSetting)
            .filter(UserExecutionSetting.user_id == user_id)
            .first()
        )

    @staticmethod
    def create(
        session_db: Session, execution_setting: UserExecutionSetting
    ) -> UserExecutionSetting:
        session_db.add(execution_setting)
        return execution_setting
