from sqlalchemy.orm import Session

from app.models.runtime_env_policy import RuntimeEnvPolicy


class RuntimeEnvPolicyRepository:
    @staticmethod
    def get_first(session_db: Session) -> RuntimeEnvPolicy | None:
        return (
            session_db.query(RuntimeEnvPolicy)
            .order_by(RuntimeEnvPolicy.id.asc())
            .first()
        )

    @staticmethod
    def create(
        session_db: Session,
        policy: RuntimeEnvPolicy,
    ) -> RuntimeEnvPolicy:
        session_db.add(policy)
        return policy
