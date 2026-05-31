import uuid

from sqlalchemy.orm import Session

from app.models.channel_artifact import ChannelArtifact


class ChannelArtifactRepository:
    @staticmethod
    def get_by_session_and_path(
        session_db: Session,
        *,
        source_session_id: uuid.UUID,
        logical_path: str,
    ) -> ChannelArtifact | None:
        return (
            session_db.query(ChannelArtifact)
            .filter(
                ChannelArtifact.source_session_id == source_session_id,
                ChannelArtifact.logical_path == logical_path,
            )
            .first()
        )

    @classmethod
    def upsert_many(
        cls,
        session_db: Session,
        *,
        artifacts: list[ChannelArtifact],
    ) -> list[ChannelArtifact]:
        persisted: list[ChannelArtifact] = []
        for artifact in artifacts:
            if artifact.source_session_id is None:
                session_db.add(artifact)
                persisted.append(artifact)
                continue

            existing = cls.get_by_session_and_path(
                session_db,
                source_session_id=artifact.source_session_id,
                logical_path=artifact.logical_path,
            )
            if existing is None:
                session_db.add(artifact)
                persisted.append(artifact)
                continue

            existing.server_id = artifact.server_id
            existing.channel_id = artifact.channel_id
            existing.agent_identity_id = artifact.agent_identity_id
            existing.publisher_user_id = artifact.publisher_user_id
            existing.source_kind = artifact.source_kind
            existing.display_name = artifact.display_name
            existing.object_key = artifact.object_key
            existing.mime_type = artifact.mime_type
            existing.size_bytes = artifact.size_bytes
            existing.is_previewable = artifact.is_previewable
            persisted.append(existing)
        return persisted

    @staticmethod
    def list_by_channel(
        session_db: Session,
        *,
        channel_id: uuid.UUID,
    ) -> list[ChannelArtifact]:
        return (
            session_db.query(ChannelArtifact)
            .filter(ChannelArtifact.channel_id == channel_id)
            .order_by(
                ChannelArtifact.agent_identity_id.asc().nulls_last(),
                ChannelArtifact.publisher_user_id.asc().nulls_last(),
                ChannelArtifact.logical_path.asc(),
            )
            .all()
        )

    @staticmethod
    def get_by_channel_and_id(
        session_db: Session,
        *,
        channel_id: uuid.UUID,
        artifact_id: uuid.UUID,
    ) -> ChannelArtifact | None:
        return (
            session_db.query(ChannelArtifact)
            .filter(
                ChannelArtifact.channel_id == channel_id,
                ChannelArtifact.id == artifact_id,
            )
            .first()
        )

    @staticmethod
    def get_by_channel_and_path(
        session_db: Session,
        *,
        channel_id: uuid.UUID,
        logical_path: str,
    ) -> ChannelArtifact | None:
        return (
            session_db.query(ChannelArtifact)
            .filter(
                ChannelArtifact.channel_id == channel_id,
                ChannelArtifact.logical_path == logical_path,
            )
            .first()
        )

    @staticmethod
    def search_by_channel(
        session_db: Session,
        *,
        channel_id: uuid.UUID,
        query: str,
        limit: int,
    ) -> list[ChannelArtifact]:
        pattern = f"%{query}%"
        return (
            session_db.query(ChannelArtifact)
            .filter(ChannelArtifact.channel_id == channel_id)
            .filter(
                ChannelArtifact.display_name.ilike(pattern)
                | ChannelArtifact.logical_path.ilike(pattern)
                | ChannelArtifact.source_kind.ilike(pattern)
            )
            .order_by(ChannelArtifact.logical_path.asc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def delete(session_db: Session, artifact: ChannelArtifact) -> None:
        session_db.delete(artifact)
