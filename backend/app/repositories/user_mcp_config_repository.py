from sqlalchemy.orm import Session

from app.models.user_mcp_config import UserMcpConfig


class UserMcpConfigRepository:
    @staticmethod
    def create(session_db: Session, config: UserMcpConfig) -> UserMcpConfig:
        session_db.add(config)
        return config

    @staticmethod
    def get_by_id(session_db: Session, config_id: int) -> UserMcpConfig | None:
        return (
            session_db.query(UserMcpConfig)
            .filter(UserMcpConfig.id == config_id)
            .first()
        )

    @staticmethod
    def get_by_user_and_preset(
        session_db: Session, user_id: str, preset_id: int
    ) -> UserMcpConfig | None:
        return (
            session_db.query(UserMcpConfig)
            .filter(
                UserMcpConfig.user_id == user_id,
                UserMcpConfig.preset_id == preset_id,
            )
            .first()
        )

    @staticmethod
    def list_by_user(session_db: Session, user_id: str) -> list[UserMcpConfig]:
        return (
            session_db.query(UserMcpConfig)
            .filter(UserMcpConfig.user_id == user_id)
            .order_by(UserMcpConfig.created_at.desc())
            .all()
        )

    @staticmethod
    def delete(session_db: Session, config: UserMcpConfig) -> None:
        session_db.delete(config)
