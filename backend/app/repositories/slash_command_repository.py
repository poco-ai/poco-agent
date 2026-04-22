from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.slash_command import SlashCommand


class SlashCommandRepository:
    @staticmethod
    def create(session_db: Session, command: SlashCommand) -> SlashCommand:
        session_db.add(command)
        return command

    @staticmethod
    def get_by_id(session_db: Session, command_id: int) -> SlashCommand | None:
        return (
            session_db.query(SlashCommand).filter(SlashCommand.id == command_id).first()
        )

    @staticmethod
    def get_by_name(
        session_db: Session, user_id: str, name: str
    ) -> SlashCommand | None:
        return (
            session_db.query(SlashCommand)
            .filter(SlashCommand.user_id == user_id, SlashCommand.name == name)
            .first()
        )

    @staticmethod
    def list_by_user(session_db: Session, user_id: str) -> list[SlashCommand]:
        return (
            session_db.query(SlashCommand)
            .filter(SlashCommand.user_id == user_id)
            .order_by(SlashCommand.created_at.desc())
            .all()
        )

    @staticmethod
    def list_enabled_by_user(session_db: Session, user_id: str) -> list[SlashCommand]:
        return (
            session_db.query(SlashCommand)
            .filter(SlashCommand.user_id == user_id, SlashCommand.enabled.is_(True))
            .order_by(SlashCommand.created_at.desc())
            .all()
        )

    @staticmethod
    def list_visible_by_user(
        session_db: Session, user_id: str, system_user_id: str
    ) -> list[SlashCommand]:
        user_command_names = (
            session_db.query(SlashCommand.name)
            .filter(SlashCommand.user_id == user_id)
            .scalar_subquery()
        )

        return (
            session_db.query(SlashCommand)
            .filter(
                or_(
                    SlashCommand.user_id == user_id,
                    and_(
                        SlashCommand.user_id == system_user_id,
                        ~SlashCommand.name.in_(user_command_names),
                    ),
                )
            )
            .order_by(SlashCommand.created_at.desc())
            .all()
        )

    @staticmethod
    def list_enabled_visible_by_user(
        session_db: Session, user_id: str, system_user_id: str
    ) -> list[SlashCommand]:
        user_command_names = (
            session_db.query(SlashCommand.name)
            .filter(SlashCommand.user_id == user_id)
            .scalar_subquery()
        )

        return (
            session_db.query(SlashCommand)
            .filter(
                or_(
                    and_(
                        SlashCommand.user_id == user_id,
                        SlashCommand.enabled.is_(True),
                    ),
                    and_(
                        SlashCommand.user_id == system_user_id,
                        SlashCommand.enabled.is_(True),
                        ~SlashCommand.name.in_(user_command_names),
                    ),
                )
            )
            .order_by(SlashCommand.created_at.desc())
            .all()
        )

    @staticmethod
    def delete(session_db: Session, command: SlashCommand) -> None:
        session_db.delete(command)
