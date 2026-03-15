from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.models.channel import Channel
from app.repositories.active_session_repository import ActiveSessionRepository
from app.repositories.channel_delivery_repository import ChannelDeliveryRepository
from app.repositories.channel_repository import ChannelRepository
from app.repositories.dedup_repository import DedupRepository
from app.repositories.watch_repository import WatchRepository
from app.schemas.backend_event import BackendEvent
from app.services.message_formatter import MessageFormatter
from app.services.notification_gateway import NotificationGateway


class BackendEventService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.formatter = MessageFormatter()
        self.gateway = NotificationGateway()

    async def process_event(self, db: Session, *, event: BackendEvent) -> int:
        expected_user_id = (
            self.settings.backend_user_id.strip() or "default"
            if self.settings.backend_user_id
            else "default"
        )
        if event.user_id != expected_user_id:
            return 0

        session_id = event.session.id.strip()
        if not session_id:
            return 0

        target_channel_ids = self._get_target_channel_ids(db, session_id=session_id)
        if not target_channel_ids:
            return 0

        delivered = 0
        if event.type == "assistant_message.created":
            message = event.message
            if message is None or not message.text.strip():
                return 0
            for channel_id in target_channel_ids:
                key = f"msg:{channel_id}:{session_id}:{message.id}"
                if DedupRepository.exists(db, key=key):
                    continue
                rendered = self.formatter.format_assistant_text_update(
                    session_id=session_id,
                    text=message.text,
                    title=event.session.title,
                )
                if not rendered:
                    DedupRepository.put(db, key=key)
                    continue
                if not await self._send_to_channel(
                    db, channel_id=channel_id, text=rendered
                ):
                    raise RuntimeError(
                        f"failed to deliver assistant message event to channel {channel_id}"
                    )
                DedupRepository.put(db, key=key)
                delivered += 1
            return delivered

        if event.type == "run.terminal":
            run = event.run
            raw_status = run.status if run is not None else event.session.status
            status = (raw_status or "").strip()
            if status not in {"completed", "failed", "canceled"}:
                return 0
            run_ref = (
                run.id.strip()
                if run is not None and isinstance(run.id, str) and run.id.strip()
                else session_id
            )
            for channel_id in target_channel_ids:
                key = f"run:{channel_id}:{run_ref}:{status}"
                if DedupRepository.exists(db, key=key):
                    continue
                rendered = self.formatter.format_terminal_notification(
                    session_id=session_id,
                    title=event.session.title,
                    status=status,
                    run_id=run.id if run is not None else None,
                    last_error=(run.error_message if run is not None else None),
                )
                if not await self._send_to_channel(
                    db, channel_id=channel_id, text=rendered
                ):
                    raise RuntimeError(
                        f"failed to deliver run terminal event to channel {channel_id}"
                    )
                DedupRepository.put(db, key=key)
                delivered += 1
            return delivered

        if event.type == "user_input_request.created":
            request = event.user_input_request
            if request is None or request.status != "pending":
                return 0
            for channel_id in target_channel_ids:
                key = f"ui:{channel_id}:{request.id}"
                if DedupRepository.exists(db, key=key):
                    continue
                rendered = self.formatter.format_user_input_request(
                    request_id=request.id,
                    session_id=session_id,
                    tool_name=request.tool_name,
                    tool_input=request.tool_input,
                    expires_at=request.expires_at.isoformat(),
                    title=event.session.title,
                )
                if not await self._send_to_channel(
                    db, channel_id=channel_id, text=rendered
                ):
                    raise RuntimeError(
                        f"failed to deliver user input event to channel {channel_id}"
                    )
                DedupRepository.put(db, key=key)
                delivered += 1
            return delivered

        return 0

    def _get_target_channel_ids(self, db: Session, *, session_id: str) -> set[int]:
        target: set[int] = set()

        for ch in ChannelRepository.list_enabled(db):
            if ch.subscribe_all:
                target.add(ch.id)

        for watch in WatchRepository.list_by_session(db, session_id=session_id):
            target.add(watch.channel_id)

        for active in ActiveSessionRepository.list_by_session(
            db, session_id=session_id
        ):
            target.add(active.channel_id)

        return target

    async def _send_to_channel(
        self, db: Session, *, channel_id: int, text: str
    ) -> bool:
        ch: Channel | None = db.get(Channel, channel_id)
        if not ch or not ch.enabled:
            return True

        if ch.provider == "dingtalk":
            destination = ch.destination
        else:
            destination = (
                ChannelDeliveryRepository.get_send_address(db, channel_id=channel_id)
                or ch.destination
            )

        return await self.gateway.send_text(
            provider=ch.provider,
            destination=destination,
            text=text,
        )
