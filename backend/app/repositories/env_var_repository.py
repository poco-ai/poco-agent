from sqlalchemy.orm import Session

from app.models.env_var import UserEnvVar


class EnvVarRepository:
    @staticmethod
    def create(session_db: Session, env_var: UserEnvVar) -> UserEnvVar:
        session_db.add(env_var)
        return env_var

    @staticmethod
    def get_by_id(session_db: Session, env_var_id: int) -> UserEnvVar | None:
        return session_db.query(UserEnvVar).filter(UserEnvVar.id == env_var_id).first()

    @staticmethod
    def get_by_user_and_key(
        session_db: Session, user_id: str, key: str
    ) -> UserEnvVar | None:
        return (
            session_db.query(UserEnvVar)
            .filter(UserEnvVar.user_id == user_id, UserEnvVar.key == key)
            .first()
        )

    @staticmethod
    def list_by_user(session_db: Session, user_id: str) -> list[UserEnvVar]:
        return (
            session_db.query(UserEnvVar)
            .filter(UserEnvVar.user_id == user_id)
            .order_by(UserEnvVar.created_at.desc())
            .all()
        )

    @staticmethod
    def delete(session_db: Session, env_var: UserEnvVar) -> None:
        session_db.delete(env_var)
