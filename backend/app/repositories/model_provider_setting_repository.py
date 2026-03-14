from sqlalchemy.orm import Session

from app.models.model_provider_setting import UserModelProviderSetting


class ModelProviderSettingRepository:
    @staticmethod
    def list_by_user_id(
        session_db: Session, user_id: str
    ) -> list[UserModelProviderSetting]:
        return (
            session_db.query(UserModelProviderSetting)
            .filter(UserModelProviderSetting.user_id == user_id)
            .all()
        )

    @staticmethod
    def get_by_user_and_provider(
        session_db: Session,
        user_id: str,
        provider_id: str,
    ) -> UserModelProviderSetting | None:
        return (
            session_db.query(UserModelProviderSetting)
            .filter(UserModelProviderSetting.user_id == user_id)
            .filter(UserModelProviderSetting.provider_id == provider_id)
            .first()
        )

    @staticmethod
    def create(
        session_db: Session, setting: UserModelProviderSetting
    ) -> UserModelProviderSetting:
        session_db.add(setting)
        return setting

    @staticmethod
    def delete(session_db: Session, setting: UserModelProviderSetting) -> None:
        session_db.delete(setting)
