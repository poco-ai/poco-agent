from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.skill import Skill


class SkillRepository:
    @staticmethod
    def create(session_db: Session, skill: Skill) -> Skill:
        session_db.add(skill)
        return skill

    @staticmethod
    def get_by_id(session_db: Session, skill_id: int) -> Skill | None:
        return session_db.query(Skill).filter(Skill.id == skill_id).first()

    @staticmethod
    def get_by_name(session_db: Session, name: str, user_id: str) -> Skill | None:
        """Get a user-owned skill by name."""
        return (
            session_db.query(Skill)
            .filter(Skill.name == name, Skill.owner_user_id == user_id)
            .first()
        )

    @staticmethod
    def list_visible(session_db: Session, user_id: str) -> list[Skill]:
        """List skills visible to the user.

        Mirrors MCP visibility rules: user-scoped skills override system skills with the same name.
        """
        user_skill_names = (
            session_db.query(Skill.name)
            .filter(Skill.scope == "user", Skill.owner_user_id == user_id)
            .scalar_subquery()
        )

        query = session_db.query(Skill).filter(
            or_(
                and_(Skill.scope == "user", Skill.owner_user_id == user_id),
                and_(Skill.scope == "system", ~Skill.name.in_(user_skill_names)),
            )
        )
        return query.order_by(Skill.created_at.desc()).all()

    @staticmethod
    def delete(session_db: Session, skill: Skill) -> None:
        session_db.delete(skill)
