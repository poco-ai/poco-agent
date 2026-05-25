import uuid
from pathlib import PurePosixPath
from typing import Any

from sqlalchemy.orm import Session

from app.repositories.agent_identity_repository import AgentIdentityRepository
from app.repositories.channel_artifact_repository import ChannelArtifactRepository
from app.repositories.server_channel_agent_member_repository import (
    ServerChannelAgentMemberRepository,
)
from app.repositories.server_channel_repository import ServerChannelMemberRepository
from app.repositories.server_channel_message_repository import (
    ServerChannelMessageRepository,
)
from app.repositories.user_repository import UserRepository
from app.schemas.agent_trigger import (
    AgentTriggerEnvelope,
    TriggerReferences,
    TriggerType,
)
from app.services.storage_service import S3StorageService


class ChannelSharedContextService:
    MAX_RECENT_MESSAGES = 8
    MAX_ARTIFACTS = 6
    MAX_TEXT_ARTIFACT_BYTES = 4 * 1024
    TEXT_EXTENSIONS = {
        ".md",
        ".txt",
        ".json",
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".yaml",
        ".yml",
        ".toml",
        ".sql",
    }

    def __init__(self) -> None:
        self._storage = S3StorageService()

    @staticmethod
    def _message_text(message: Any) -> str:
        content = getattr(message, "content", None)
        if isinstance(content, dict):
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()
            title = content.get("title")
            if isinstance(title, str) and title.strip():
                return title.strip()
        text_preview = getattr(message, "text_preview", None)
        if isinstance(text_preview, str) and text_preview.strip():
            return text_preview.strip()
        return ""

    @staticmethod
    def _message_author_label(message: Any) -> str:
        author_user = getattr(message, "author_user", None)
        if author_user is not None:
            display_name = getattr(author_user, "display_name", None)
            if isinstance(display_name, str) and display_name.strip():
                return display_name.strip()
            user_id = getattr(author_user, "user_id", None)
            if isinstance(user_id, str) and user_id.strip():
                return user_id.strip()
        author_user_id = getattr(message, "author_user_id", None)
        if isinstance(author_user_id, str) and author_user_id.strip():
            return author_user_id.strip()
        return "Unknown"

    @staticmethod
    def _message_preview(message: Any) -> str:
        text_preview = getattr(message, "text_preview", None)
        if isinstance(text_preview, str) and text_preview.strip():
            return text_preview.strip()
        return ChannelSharedContextService._message_text(message)

    @classmethod
    def _is_text_artifact(cls, artifact: Any) -> bool:
        mime_type = getattr(artifact, "mime_type", None)
        if isinstance(mime_type, str) and mime_type.startswith("text/"):
            return True
        suffix = PurePosixPath(getattr(artifact, "logical_path", "")).suffix.lower()
        return suffix in cls.TEXT_EXTENSIONS

    def _artifact_block(self, artifact: Any) -> str:
        display_name = getattr(artifact, "display_name", "artifact")
        logical_path = getattr(artifact, "logical_path", "")
        lines = [
            f"- {display_name} ({logical_path})",
        ]
        artifact_id = getattr(artifact, "id", None)
        if artifact_id is not None:
            lines.append(f"  artifact_id: {artifact_id}")
        mime_type = getattr(artifact, "mime_type", None)
        if isinstance(mime_type, str) and mime_type.strip():
            lines.append(f"  mime_type: {mime_type.strip()}")
        size_bytes = getattr(artifact, "size_bytes", None)
        if isinstance(size_bytes, int):
            lines.append(f"  size_bytes: {size_bytes}")
        lines.append("  [metadata only: use read_channel_artifact for content]")
        return "\n".join(lines)

    def extract_trigger_body(self, message: Any) -> str:
        return self._message_text(message)

    @staticmethod
    def build_trigger_envelope(
        *,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
        message: Any,
        current_user: Any,
        target_agent_identity_id: uuid.UUID,
        target_agent_handle: str,
        trigger_type: TriggerType,
        references: TriggerReferences | None = None,
    ) -> AgentTriggerEnvelope:
        message_id = getattr(message, "id")
        thread_root_message_id = (
            getattr(message, "thread_root_message_id", None) or message_id
        )
        display_name = getattr(current_user, "display_name", None) or getattr(
            current_user,
            "primary_email",
            None,
        )
        user_id = getattr(current_user, "id", None) or getattr(
            message,
            "author_user_id",
            None,
        )
        return AgentTriggerEnvelope(
            trigger_type=trigger_type,
            server_id=server_id,
            channel_id=channel_id,
            trigger_message_id=message_id,
            thread_root_message_id=thread_root_message_id,
            target_agent_identity_id=target_agent_identity_id,
            target_agent_handle=target_agent_handle,
            source_actor={
                "actor_type": "user",
                "user_id": user_id,
                "display_name": display_name,
            },
            references=references or {"message_ids": [message_id]},
            handoff={
                "dedupe_key": f"channel-trigger:{message_id}:{target_agent_identity_id}",
            },
        )

    def build_message_trigger_prompt(
        self,
        db: Session,
        *,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
        message: Any,
        current_user: Any,
        agent_display_name: str,
        agent_handle: str | None = None,
    ) -> str:
        trigger_body = self.extract_trigger_body(message)
        return self.build_legacy_prompt_for_sdk(
            db,
            server_id=server_id,
            channel_id=channel_id,
            trigger_message_id=getattr(message, "id", None),
            thread_root_message_id=getattr(message, "thread_root_message_id", None)
            or getattr(message, "id", None),
            trigger_body=trigger_body,
            current_user=current_user,
            agent_display_name=agent_display_name,
            agent_handle=agent_handle,
        )

    def build_legacy_prompt_for_sdk(
        self,
        db: Session,
        *,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
        trigger_message_id: uuid.UUID | None,
        thread_root_message_id: uuid.UUID | None,
        trigger_body: str,
        current_user: Any,
        agent_display_name: str,
        agent_handle: str | None = None,
    ) -> str:
        recent_messages = ServerChannelMessageRepository.list_by_channel(
            db,
            channel_id,
            limit=self.MAX_RECENT_MESSAGES,
        )
        recent_messages = list(reversed(recent_messages))
        artifacts = ChannelArtifactRepository.list_by_channel(
            db, channel_id=channel_id
        )[: self.MAX_ARTIFACTS]
        human_memberships = ServerChannelMemberRepository.list_by_channel(
            db, channel_id
        )
        humans_by_id = UserRepository.list_by_ids(
            db,
            [membership.user_id for membership in human_memberships],
        )
        human_lookup = {user.id: user for user in humans_by_id}
        agent_memberships = ServerChannelAgentMemberRepository.list_by_channel(
            db, channel_id
        )
        channel_agents = [
            agent
            for membership in agent_memberships
            if (
                agent := AgentIdentityRepository.get_by_id(
                    db,
                    membership.agent_identity_id,
                )
            )
            is not None
        ]

        actor_label = (
            getattr(current_user, "display_name", None)
            or getattr(current_user, "primary_email", None)
            or getattr(current_user, "id", "User")
        )

        lines = [
            f"You are {agent_display_name}.",
            f"{actor_label} triggered you from a server conversation.",
            f"Channel ID: {channel_id}",
            f"Trigger message ID: {trigger_message_id or ''}",
            f"Thread root message ID: {thread_root_message_id or ''}",
            "",
            "Trigger message:",
            trigger_body or "[no visible trigger text]",
            "",
            "Channel people you can collaborate with:",
        ]

        if human_memberships:
            for membership in human_memberships:
                user = human_lookup.get(membership.user_id)
                human_label = (
                    (getattr(user, "display_name", None) or "").strip()
                    or (getattr(user, "primary_email", None) or "").strip()
                    or membership.user_id
                )
                lines.append(f"- Human: {human_label} (@{membership.user_id})")
        else:
            lines.append("- [no visible human members]")

        lines.extend(
            [
                "",
                "Channel agents you can collaborate with:",
            ]
        )
        if channel_agents:
            for agent in channel_agents:
                lines.append(f"- Agent: {agent.display_name} (@{agent.handle})")
        else:
            lines.append("- [no visible agents]")

        lines.extend(
            [
                "",
                "Behavior rules:",
                f"- Your handle is @{agent_handle or agent_display_name}.",
                "- If the current turn is clearly aimed at another agent or human, you may stay silent.",
                "- If you judge that your reply would not add value, you may stay silent.",
                "- You may mention other agents or humans with @handle when you want to collaborate.",
                "- If you mention someone for handoff, say that you are handing off and avoid duplicating their work.",
                "- If you mention someone for collaboration, give your own partial answer first, then clearly ask for what you need.",
                "",
                "Recent conversation context:",
            ]
        )

        if recent_messages:
            for recent in recent_messages:
                if getattr(recent, "id", None) == trigger_message_id:
                    continue
                text = self._message_preview(recent)
                if not text:
                    continue
                lines.append(
                    f"- {getattr(recent, 'id', '')} "
                    f"{self._message_author_label(recent)}: {text}"
                )
        else:
            lines.append("- [no recent visible messages]")

        lines.append("")
        lines.append("Published channel artifacts available through runtime tools:")
        if artifacts:
            for artifact in artifacts:
                lines.append(self._artifact_block(artifact))
        else:
            lines.append("- [no published artifacts yet]")

        lines.append("")
        lines.extend(
            [
                "Shared artifact rules:",
                "- Published artifact logical_path values are not /workspace paths.",
                "- Use list_channel_artifacts or search_channel_artifacts before "
                "reading shared files.",
                "- Prefer read_channel_artifact with artifact_id. Use logical_path "
                "only when passing the exact logical_path returned by artifact tools; "
                "display_name is not a stable read identifier.",
                "- Do not assume access to private agent state, raw local mount "
                "paths, or unpublished session workspace files.",
                "",
                "Act on the trigger message and the shared channel context above.",
            ]
        )
        return "\n".join(lines)
