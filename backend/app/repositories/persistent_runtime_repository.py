import uuid

from sqlalchemy.orm import Session

from app.models.persistent_runtime import PersistentRuntime


class PersistentRuntimeRepository:
    @staticmethod
    def create(
        session_db: Session,
        runtime: PersistentRuntime,
    ) -> PersistentRuntime:
        session_db.add(runtime)
        return runtime

    @staticmethod
    def get_by_runtime_key(
        session_db: Session,
        runtime_key: str,
    ) -> PersistentRuntime | None:
        return (
            session_db.query(PersistentRuntime)
            .filter(PersistentRuntime.runtime_key == runtime_key)
            .first()
        )

    @staticmethod
    def get_by_owner(
        session_db: Session,
        *,
        owner_type: str,
        owner_id: uuid.UUID,
    ) -> PersistentRuntime | None:
        return (
            session_db.query(PersistentRuntime)
            .filter(PersistentRuntime.owner_type == owner_type)
            .filter(PersistentRuntime.owner_id == owner_id)
            .first()
        )

    @staticmethod
    def get_by_container_id(
        session_db: Session,
        container_id: str,
    ) -> PersistentRuntime | None:
        return (
            session_db.query(PersistentRuntime)
            .filter(PersistentRuntime.container_id == container_id)
            .first()
        )

    @staticmethod
    def get_by_session_id(
        session_db: Session,
        session_id: uuid.UUID,
    ) -> PersistentRuntime | None:
        return (
            session_db.query(PersistentRuntime)
            .filter(PersistentRuntime.session_id == session_id)
            .first()
        )

    @staticmethod
    def list_by_lifecycle_states(
        session_db: Session,
        *,
        lifecycle_states: list[str] | None = None,
        limit: int | None = None,
    ) -> list[PersistentRuntime]:
        query = session_db.query(PersistentRuntime)
        if lifecycle_states:
            query = query.filter(PersistentRuntime.lifecycle_state.in_(lifecycle_states))
        query = query.order_by(PersistentRuntime.updated_at.asc())
        if limit is not None:
            query = query.limit(limit)
        return query.all()
