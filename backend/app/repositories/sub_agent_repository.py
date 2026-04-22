from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.sub_agent import SubAgent


class SubAgentRepository:
    @staticmethod
    def create(session_db: Session, sub_agent: SubAgent) -> SubAgent:
        session_db.add(sub_agent)
        return sub_agent

    @staticmethod
    def get_by_id(session_db: Session, subagent_id: int) -> SubAgent | None:
        return session_db.query(SubAgent).filter(SubAgent.id == subagent_id).first()

    @staticmethod
    def get_by_user_and_name(
        session_db: Session, *, user_id: str, name: str
    ) -> SubAgent | None:
        return (
            session_db.query(SubAgent)
            .filter(SubAgent.user_id == user_id, SubAgent.name == name)
            .first()
        )

    @staticmethod
    def list_by_user(session_db: Session, *, user_id: str) -> list[SubAgent]:
        return (
            session_db.query(SubAgent)
            .filter(SubAgent.user_id == user_id)
            .order_by(SubAgent.created_at.desc())
            .all()
        )

    @staticmethod
    def list_enabled_by_user(session_db: Session, *, user_id: str) -> list[SubAgent]:
        return (
            session_db.query(SubAgent)
            .filter(SubAgent.user_id == user_id, SubAgent.enabled.is_(True))
            .order_by(SubAgent.created_at.desc())
            .all()
        )

    @staticmethod
    def list_visible_by_user(
        session_db: Session, *, user_id: str, system_user_id: str
    ) -> list[SubAgent]:
        user_names = (
            session_db.query(SubAgent.name)
            .filter(SubAgent.user_id == user_id)
            .scalar_subquery()
        )

        return (
            session_db.query(SubAgent)
            .filter(
                or_(
                    SubAgent.user_id == user_id,
                    and_(
                        SubAgent.user_id == system_user_id,
                        ~SubAgent.name.in_(user_names),
                    ),
                )
            )
            .order_by(SubAgent.created_at.desc())
            .all()
        )

    @staticmethod
    def list_enabled_visible_by_user(
        session_db: Session, *, user_id: str, system_user_id: str
    ) -> list[SubAgent]:
        user_names = (
            session_db.query(SubAgent.name)
            .filter(SubAgent.user_id == user_id)
            .scalar_subquery()
        )

        return (
            session_db.query(SubAgent)
            .filter(
                or_(
                    and_(
                        SubAgent.user_id == user_id,
                        SubAgent.enabled.is_(True),
                    ),
                    and_(
                        SubAgent.user_id == system_user_id,
                        SubAgent.enabled.is_(True),
                        ~SubAgent.name.in_(user_names),
                    ),
                )
            )
            .order_by(SubAgent.created_at.desc())
            .all()
        )

    @staticmethod
    def list_by_ids(
        session_db: Session, *, user_id: str, subagent_ids: list[int]
    ) -> list[SubAgent]:
        if not subagent_ids:
            return []
        return (
            session_db.query(SubAgent)
            .filter(SubAgent.user_id == user_id, SubAgent.id.in_(subagent_ids))
            .all()
        )

    @staticmethod
    def list_visible_by_ids(
        session_db: Session,
        *,
        user_id: str,
        system_user_id: str,
        subagent_ids: list[int],
    ) -> list[SubAgent]:
        if not subagent_ids:
            return []
        return (
            session_db.query(SubAgent)
            .filter(
                SubAgent.id.in_(subagent_ids),
                or_(
                    SubAgent.user_id == user_id,
                    SubAgent.user_id == system_user_id,
                ),
            )
            .all()
        )

    @staticmethod
    def delete(session_db: Session, sub_agent: SubAgent) -> None:
        session_db.delete(sub_agent)
