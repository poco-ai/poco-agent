import uuid

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.server_channel_task import ServerChannelTask


class ServerChannelTaskRepository:
    @staticmethod
    def create(session_db: Session, task: ServerChannelTask) -> ServerChannelTask:
        session_db.add(task)
        return task

    @staticmethod
    def get_by_id(
        session_db: Session,
        task_id: uuid.UUID,
    ) -> ServerChannelTask | None:
        return (
            session_db.query(ServerChannelTask)
            .filter(ServerChannelTask.id == task_id)
            .first()
        )

    @staticmethod
    def list_by_channel(
        session_db: Session,
        channel_id: uuid.UUID,
    ) -> list[ServerChannelTask]:
        return (
            session_db.query(ServerChannelTask)
            .filter(ServerChannelTask.channel_id == channel_id)
            .order_by(
                ServerChannelTask.created_at.desc(),
                ServerChannelTask.id.desc(),
            )
            .all()
        )

    @staticmethod
    def get_max_display_number(
        session_db: Session,
        channel_id: uuid.UUID,
    ) -> int | None:
        return (
            session_db.query(func.max(ServerChannelTask.display_number))
            .filter(ServerChannelTask.channel_id == channel_id)
            .scalar()
        )

    @staticmethod
    def list_by_channel_and_status(
        session_db: Session,
        channel_id: uuid.UUID,
        status: str,
        *,
        exclude_task_id: uuid.UUID | None = None,
    ) -> list[ServerChannelTask]:
        query = session_db.query(ServerChannelTask).filter(
            ServerChannelTask.channel_id == channel_id,
            ServerChannelTask.status == status,
        )
        if exclude_task_id is not None:
            query = query.filter(ServerChannelTask.id != exclude_task_id)
        return query.order_by(
            ServerChannelTask.position.asc(),
            ServerChannelTask.created_at.asc(),
            ServerChannelTask.id.asc(),
        ).all()
