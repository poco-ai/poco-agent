from sqlalchemy.orm import Session

from app.models.user_skill_install import UserSkillInstall


class UserSkillInstallRepository:
    @staticmethod
    def create(session_db: Session, install: UserSkillInstall) -> UserSkillInstall:
        session_db.add(install)
        return install

    @staticmethod
    def get_by_id(session_db: Session, install_id: int) -> UserSkillInstall | None:
        return (
            session_db.query(UserSkillInstall)
            .filter(UserSkillInstall.id == install_id)
            .first()
        )

    @staticmethod
    def get_by_user_and_preset(
        session_db: Session, user_id: str, preset_id: int
    ) -> UserSkillInstall | None:
        return (
            session_db.query(UserSkillInstall)
            .filter(
                UserSkillInstall.user_id == user_id,
                UserSkillInstall.preset_id == preset_id,
            )
            .first()
        )

    @staticmethod
    def list_by_user(session_db: Session, user_id: str) -> list[UserSkillInstall]:
        return (
            session_db.query(UserSkillInstall)
            .filter(UserSkillInstall.user_id == user_id)
            .order_by(UserSkillInstall.created_at.desc())
            .all()
        )

    @staticmethod
    def delete(session_db: Session, install: UserSkillInstall) -> None:
        session_db.delete(install)
