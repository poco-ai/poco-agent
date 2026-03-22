import uuid

from sqlalchemy.orm import Session

from app.models.pending_skill_creation import PendingSkillCreation


class PendingSkillCreationRepository:
    @staticmethod
    def create(
        session_db: Session,
        pending: PendingSkillCreation,
    ) -> PendingSkillCreation:
        session_db.add(pending)
        return pending

    @staticmethod
    def get_by_id(
        session_db: Session,
        creation_id: uuid.UUID,
    ) -> PendingSkillCreation | None:
        return (
            session_db.query(PendingSkillCreation)
            .filter(PendingSkillCreation.id == creation_id)
            .first()
        )

    @staticmethod
    def list_by_user(
        session_db: Session,
        *,
        user_id: str,
        session_id: uuid.UUID | None = None,
        statuses: list[str] | None = None,
    ) -> list[PendingSkillCreation]:
        query = session_db.query(PendingSkillCreation).filter(
            PendingSkillCreation.user_id == user_id
        )
        if session_id is not None:
            query = query.filter(PendingSkillCreation.session_id == session_id)
        if statuses:
            query = query.filter(PendingSkillCreation.status.in_(statuses))
        return query.order_by(PendingSkillCreation.created_at.desc()).all()

    @staticmethod
    def get_by_session_and_skill_relative_path(
        session_db: Session,
        *,
        session_id: uuid.UUID,
        skill_relative_path: str,
    ) -> PendingSkillCreation | None:
        return (
            session_db.query(PendingSkillCreation)
            .filter(
                PendingSkillCreation.session_id == session_id,
                PendingSkillCreation.skill_relative_path == skill_relative_path,
            )
            .first()
        )

    @staticmethod
    def find_by_session_and_path(
        session_db: Session,
        *,
        session_id: uuid.UUID,
        skill_relative_path: str,
    ) -> PendingSkillCreation | None:
        return PendingSkillCreationRepository.get_by_session_and_skill_relative_path(
            session_db,
            session_id=session_id,
            skill_relative_path=skill_relative_path,
        )
