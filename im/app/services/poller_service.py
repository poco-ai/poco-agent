import asyncio
import logging

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.settings import get_settings
from app.repositories.active_session_repository import ActiveSessionRepository
from app.repositories.channel_repository import ChannelRepository
from app.repositories.channel_delivery_repository import ChannelDeliveryRepository
from app.repositories.dedup_repository import DedupRepository
from app.repositories.watch_repository import WatchRepository
from app.services.backend_client import BackendClient, BackendClientError
from app.services.message_formatter import MessageFormatter
from app.services.notification_gateway import NotificationGateway

logger = logging.getLogger(__name__)


class PollerService:
    """Background pollers for Backend state (sessions/runs/messages/user-input)."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.backend = BackendClient()
        self.formatter = MessageFormatter()
        self.gateway = NotificationGateway()
        # Hint updated by the session-messages loop to gate user-input polling.
        self._has_non_terminal_targets = True

    async def run_user_input_loop(self) -> None:
        interval = max(0.2, float(self.settings.poll_user_input_interval_seconds))
        while True:
            try:
                if self._has_non_terminal_targets:
                    await self._poll_user_input_requests()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("poll_user_input_failed")
            await asyncio.sleep(interval)

    async def run_sessions_recent_loop(self) -> None:
        interval = max(1.0, float(self.settings.poll_sessions_recent_interval_seconds))
        while True:
            try:
                await self._poll_recent_sessions()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("poll_sessions_recent_failed")
            await asyncio.sleep(interval)

    async def run_sessions_full_loop(self) -> None:
        interval = max(10.0, float(self.settings.poll_sessions_full_interval_seconds))
        while True:
            try:
                await self._poll_all_sessions()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("poll_sessions_full_failed")
            await asyncio.sleep(interval)

    async def run_session_messages_loop(self) -> None:
        interval = max(0.5, float(self.settings.poll_session_messages_interval_seconds))
        while True:
            try:
                await self._poll_active_session_messages()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("poll_session_messages_failed")
            await asyncio.sleep(interval)

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

    async def _poll_user_input_requests(self) -> None:
        try:
            pending = await self.backend.list_user_input_requests()
        except BackendClientError as exc:
            logger.warning("backend_list_user_input_failed", extra={"error": str(exc)})
            return

        if not pending:
            return

        db = SessionLocal()
        try:
            for entry in pending:
                request_id = str(entry.get("id") or "").strip()
                session_id = str(entry.get("session_id") or "").strip()
                tool_name = str(entry.get("tool_name") or "").strip()
                tool_input = entry.get("tool_input")
                expires_at = entry.get("expires_at")
                status = str(entry.get("status") or "").strip()

                if not request_id or not session_id or status != "pending":
                    continue

                target_channel_ids = self._get_target_channel_ids(
                    db, session_id=session_id
                )
                if not target_channel_ids:
                    continue

                for channel_id in target_channel_ids:
                    key = f"ui:{channel_id}:{request_id}"
                    if DedupRepository.exists(db, key=key):
                        continue

                    text = self.formatter.format_user_input_request(
                        request_id=request_id,
                        session_id=session_id,
                        tool_name=tool_name,
                        tool_input=tool_input if isinstance(tool_input, dict) else None,
                        expires_at=str(expires_at) if expires_at else None,
                    )
                    await self._send_to_channel(db, channel_id=channel_id, text=text)
                    DedupRepository.put(db, key=key)
        finally:
            db.close()

    async def _poll_recent_sessions(self) -> None:
        # First page only. This captures newly created sessions quickly.
        await self._poll_sessions_page(limit=100, offset=0)

    async def _poll_all_sessions(self) -> None:
        # Full scan is best-effort and can be heavy; keep it periodic.
        limit = 100
        offset = 0
        while True:
            batch = await self._poll_sessions_page(limit=limit, offset=offset)
            if batch <= 0:
                break
            offset += limit

    async def _poll_active_session_messages(self) -> None:
        try:
            sessions = await self.backend.list_sessions(
                limit=100, offset=0, kind="chat"
            )
        except BackendClientError as exc:
            logger.warning("backend_list_sessions_failed", extra={"error": str(exc)})
            return

        if not sessions:
            self._has_non_terminal_targets = False
            return

        has_non_terminal_targets = False
        db = SessionLocal()
        try:
            for item in sessions:
                session_id = str(item.get("session_id") or item.get("id") or "").strip()
                if not session_id:
                    continue
                status = _normalize_status(str(item.get("status") or ""))
                if status not in {"pending", "queued", "claimed", "running"}:
                    continue
                title = str(item.get("title") or "").strip() or None
                target_channel_ids = self._get_target_channel_ids(
                    db, session_id=session_id
                )
                if not target_channel_ids:
                    continue
                has_non_terminal_targets = True
                await self._emit_assistant_text_updates(
                    db,
                    session_id=session_id,
                    title=title,
                    target_channel_ids=target_channel_ids,
                )
        finally:
            db.close()
        self._has_non_terminal_targets = has_non_terminal_targets

    async def _poll_sessions_page(self, *, limit: int, offset: int) -> int:
        try:
            sessions = await self.backend.list_sessions(
                limit=limit, offset=offset, kind="chat"
            )
        except BackendClientError as exc:
            logger.warning("backend_list_sessions_failed", extra={"error": str(exc)})
            return 0

        if not sessions:
            return 0

        db = SessionLocal()
        try:
            for item in sessions:
                session_id = str(item.get("session_id") or item.get("id") or "").strip()
                if not session_id:
                    continue
                status = _normalize_status(str(item.get("status") or ""))
                title = str(item.get("title") or "").strip() or None

                if status not in {"completed", "failed", "canceled"}:
                    continue

                target_channel_ids = self._get_target_channel_ids(
                    db, session_id=session_id
                )
                if not target_channel_ids:
                    continue

                # Flush assistant text updates first so terminal notifications come last.
                await self._emit_assistant_text_updates(
                    db,
                    session_id=session_id,
                    title=title,
                    target_channel_ids=target_channel_ids,
                )

                run_id, run_status, last_error = await self._get_latest_run_detail(
                    session_id=session_id
                )
                run_id = run_id or None
                run_status = _effective_notification_status(
                    run_status=run_status,
                    session_status=status,
                )

                for channel_id in target_channel_ids:
                    dedup_key = f"run:{channel_id}:{run_id or session_id}:{run_status}"
                    if DedupRepository.exists(db, key=dedup_key):
                        continue
                    text = self.formatter.format_terminal_notification(
                        session_id=session_id,
                        title=title,
                        status=run_status,
                        run_id=run_id,
                        last_error=last_error if run_status == "failed" else None,
                    )
                    await self._send_to_channel(db, channel_id=channel_id, text=text)
                    DedupRepository.put(db, key=dedup_key)
        finally:
            db.close()

        return len(sessions)

    async def _emit_assistant_text_updates(
        self,
        db: Session,
        *,
        session_id: str,
        title: str | None,
        target_channel_ids: set[int],
    ) -> None:
        try:
            messages = await self.backend.get_session_messages(session_id=session_id)
        except BackendClientError:
            return

        text_entries = _extract_assistant_text_entries(messages)
        if not text_entries:
            return

        bootstrap_tail = 3
        for channel_id in target_channel_ids:
            init_key = f"msg:init:{channel_id}:{session_id}"
            if not DedupRepository.exists(db, key=init_key):
                # Avoid flooding historical records when the text-stream feature is first enabled.
                if len(text_entries) > bootstrap_tail:
                    for message_id, _ in text_entries[:-bootstrap_tail]:
                        key = f"msg:{channel_id}:{session_id}:{message_id}"
                        DedupRepository.put(db, key=key)
                    pending_entries = text_entries[-bootstrap_tail:]
                else:
                    pending_entries = text_entries
                DedupRepository.put(db, key=init_key)
            else:
                pending_entries = text_entries

            for message_id, text in pending_entries:
                key = f"msg:{channel_id}:{session_id}:{message_id}"
                if DedupRepository.exists(db, key=key):
                    continue
                rendered = self.formatter.format_assistant_text_update(
                    session_id=session_id,
                    text=text,
                    title=title,
                )
                if not rendered:
                    DedupRepository.put(db, key=key)
                    continue
                await self._send_to_channel(db, channel_id=channel_id, text=rendered)
                DedupRepository.put(db, key=key)

    async def _get_latest_run_detail(
        self, *, session_id: str
    ) -> tuple[str | None, str | None, str | None]:
        try:
            runs = await self.backend.list_runs_by_session(session_id=session_id)
        except BackendClientError:
            return None, None, None
        if not runs:
            return None, None, None
        latest = runs[-1]
        run_id = str(latest.get("run_id") or latest.get("id") or "").strip() or None
        run_status = str(latest.get("status") or "").strip() or None
        last_error = (
            str(latest.get("last_error") or "").strip() or None
            if run_status == "failed"
            else None
        )
        return run_id, run_status, last_error

    async def _send_to_channel(
        self, db: Session, *, channel_id: int, text: str
    ) -> None:
        from app.models.channel import Channel  # local import to avoid circulars

        ch: Channel | None = db.get(Channel, channel_id)
        if not ch or not ch.enabled:
            return
        # DingTalk sessionWebhook can expire; prefer stable conversationId for polling-based notifications.
        if ch.provider == "dingtalk":
            destination = ch.destination
        else:
            destination = (
                ChannelDeliveryRepository.get_send_address(db, channel_id=channel_id)
                or ch.destination
            )
        await self.gateway.send_text(
            provider=ch.provider,
            destination=destination,
            text=text,
        )


def _normalize_status(raw: str | None) -> str:
    normalized = (raw or "").strip().lower()
    if normalized == "cancelled":
        return "canceled"
    return normalized


def _effective_notification_status(
    *, run_status: str | None, session_status: str
) -> str:
    run = _normalize_status(run_status)
    if run in {"completed", "failed", "canceled"}:
        return run
    session = _normalize_status(session_status)
    if session in {"completed", "failed", "canceled"}:
        return session
    return run or session or "unknown"


def _extract_assistant_text_entries(
    messages: list[dict],
) -> list[tuple[int, str]]:
    entries: list[tuple[int, str]] = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        message_id = _parse_message_id(msg.get("id"))
        if message_id is None:
            continue
        text = _extract_assistant_text(msg)
        if not text:
            continue
        entries.append((message_id, text))
    return entries


def _parse_message_id(raw: object) -> int | None:
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str) and raw.isdigit():
        return int(raw)
    return None


def _extract_assistant_text(message: dict) -> str:
    role = str(message.get("role") or "").strip().lower()
    if role != "assistant":
        return ""

    content = message.get("content")
    if not isinstance(content, dict):
        return ""

    # System init payload is an internal handshake, not user-facing content.
    if (
        _type_includes(content.get("_type"), "SystemMessage")
        and str(content.get("subtype") or "").strip() == "init"
    ):
        return ""

    # Nested subagent transcript usually belongs to a tool detail thread.
    if content.get("parent_tool_use_id"):
        return ""

    raw_texts: list[str] = []
    text_field = content.get("text")
    if isinstance(text_field, str) and text_field.strip():
        raw_texts.append(text_field.strip())

    blocks = content.get("content")
    if isinstance(blocks, list):
        for block in blocks:
            if not isinstance(block, dict):
                continue
            if not _type_includes(block.get("_type"), "TextBlock"):
                continue
            block_text = block.get("text")
            if isinstance(block_text, str) and block_text.strip():
                raw_texts.append(block_text.strip())

    if not raw_texts:
        return ""

    cleaned: list[str] = []
    seen: set[str] = set()
    for text in raw_texts:
        normalized = text.replace("\ufffd", "").strip()
        if not normalized:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)

    return "\n\n".join(cleaned)


def _type_includes(type_value: object, needle: str) -> bool:
    if not isinstance(type_value, str):
        return False
    value = type_value.strip()
    if not value:
        return False
    return value == needle or needle in value
