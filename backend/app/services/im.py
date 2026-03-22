import asyncio
import json
import logging
import re
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.errors.exceptions import AppException
from app.core.settings import get_settings
from app.models.agent_message import AgentMessage
from app.models.agent_run import AgentRun
from app.models.agent_session import AgentSession
from app.models.im import Channel
from app.models.user_input_request import UserInputRequest
from app.repositories.im import (
    ActiveSessionRepository,
    ChannelDeliveryRepository,
    ChannelRepository,
    DedupRepository,
    ImEventOutboxRepository,
    WatchRepository,
)
from app.repositories.run_repository import RunRepository
from app.schemas.callback import AgentCallbackRequest
from app.schemas.im import (
    EventStateSnapshot,
    ImBackendEvent,
    InboundMessage,
    MessageSnapshot,
    RunSnapshot,
    SessionSnapshot,
    UserInputRequestSnapshot,
)
from app.schemas.session import SessionResponse, SessionStateResponse, TaskConfig
from app.schemas.task import TaskEnqueueRequest, TaskEnqueueResponse
from app.schemas.user_input_request import UserInputAnswerRequest
from app.services.im_providers import NotificationGateway
from app.services.session_service import SessionService
from app.services.session_title_service import SessionTitleService
from app.services.task_service import TaskService
from app.services.user_input_request_service import UserInputRequestService

logger = logging.getLogger(__name__)

_TASK_SERVICE = TaskService()
_SESSION_SERVICE = SessionService()
_TITLE_SERVICE = SessionTitleService()
_USER_INPUT_SERVICE = UserInputRequestService()
_LEADING_AT_TAG_RE = re.compile(r"^(?:<at\s+[^>]*>.*?</at>\s*)+", re.IGNORECASE)
_LEADING_MENTION_RE = re.compile(r"^(?:[@＠][^\s]+\s*)+")
CommandHandler = Callable[[Session, Channel, str], Awaitable[list[str]]]


class BackendClientError(RuntimeError):
    pass


class BackendClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.backend_user_id = (
            settings.backend_user_id or "default"
        ).strip() or "default"
        self._task_service = _TASK_SERVICE
        self._session_service = _SESSION_SERVICE
        self._title_service = _TITLE_SERVICE
        self._user_input_service = _USER_INPUT_SERVICE

    async def enqueue_task(
        self,
        *,
        prompt: str,
        session_id: str | None = None,
        project_id: str | None = None,
        config: dict[str, Any] | None = None,
        permission_mode: str = "default",
    ) -> dict[str, Any]:
        task_request = TaskEnqueueRequest(
            prompt=prompt,
            session_id=_parse_uuid(session_id, field_name="session_id"),
            project_id=_parse_uuid(project_id, field_name="project_id"),
            config=TaskConfig.model_validate(config) if config is not None else None,
            permission_mode=permission_mode,
            schedule_mode="immediate",
        )
        result = await self._run_sync(self._enqueue_task_sync, request=task_request)
        if task_request.session_id is None:
            self._schedule_title_generation(result.session_id, prompt)
        return result.model_dump(mode="json")

    async def list_sessions(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        kind: str = "chat",
    ) -> list[dict[str, Any]]:
        return await self._run_sync(
            self._list_sessions_sync,
            limit=limit,
            offset=offset,
            kind=kind,
        )

    async def get_session_state(self, *, session_id: str) -> dict[str, Any]:
        return await self._run_sync(
            self._get_session_state_sync,
            session_id=_parse_uuid(session_id, field_name="session_id", required=True),
        )

    async def answer_user_input_request(
        self,
        *,
        request_id: str,
        answers: dict[str, str],
    ) -> dict[str, Any]:
        answer_request = UserInputAnswerRequest(answers=answers)
        return await self._run_sync(
            self._answer_user_input_request_sync,
            request_id=_parse_uuid(request_id, field_name="request_id", required=True),
            answer_request=answer_request,
        )

    async def _run_sync(self, func, /, **kwargs):
        try:
            return await asyncio.to_thread(func, **kwargs)
        except BackendClientError:
            raise
        except AppException as exc:
            raise BackendClientError(exc.message) from exc
        except ValidationError as exc:
            raise BackendClientError(str(exc)) from exc
        except ValueError as exc:
            raise BackendClientError(str(exc)) from exc
        except Exception as exc:
            logger.exception("embedded_backend_client_call_failed")
            raise BackendClientError(f"Internal backend error: {exc}") from exc

    def _enqueue_task_sync(self, *, request: TaskEnqueueRequest) -> TaskEnqueueResponse:
        db = SessionLocal()
        try:
            return self._task_service.enqueue_task(db, self.backend_user_id, request)
        finally:
            db.close()

    def _list_sessions_sync(
        self,
        *,
        limit: int,
        offset: int,
        kind: str,
    ) -> list[dict[str, Any]]:
        db = SessionLocal()
        try:
            kind_filter = kind.strip().lower()
            kind_value = None if kind_filter in {"", "all"} else kind_filter
            sessions = self._session_service.list_sessions(
                db,
                self.backend_user_id,
                limit,
                offset,
                None,
                kind=kind_value,
            )
            return [
                SessionResponse.model_validate(session).model_dump(mode="json")
                for session in sessions
            ]
        finally:
            db.close()

    def _get_session_state_sync(self, *, session_id: uuid.UUID) -> dict[str, Any]:
        db = SessionLocal()
        try:
            session = self._session_service.get_session(db, session_id)
            if session.user_id != self.backend_user_id:
                raise BackendClientError("Session does not belong to the IM user")
            return SessionStateResponse.model_validate(session).model_dump(mode="json")
        finally:
            db.close()

    def _answer_user_input_request_sync(
        self,
        *,
        request_id: uuid.UUID,
        answer_request: UserInputAnswerRequest,
    ) -> dict[str, Any]:
        db = SessionLocal()
        try:
            result = self._user_input_service.answer_request(
                db,
                user_id=self.backend_user_id,
                request_id=str(request_id),
                answer_request=answer_request,
            )
            return result.model_dump(mode="json")
        finally:
            db.close()

    def _schedule_title_generation(self, session_id: uuid.UUID, prompt: str) -> None:
        task = asyncio.create_task(
            asyncio.to_thread(
                self._title_service.generate_and_update,
                session_id,
                prompt,
            )
        )
        task.add_done_callback(_log_background_task_exception)


class MessageFormatter:
    def __init__(self) -> None:
        self.settings = get_settings()

    def session_url(self, session_id: str) -> str:
        base = self.settings.frontend_public_url.rstrip("/")
        lng = (self.settings.frontend_default_language or "zh").strip() or "zh"
        return f"{base}/{lng}/chat/{session_id}"

    def format_task_created(
        self,
        *,
        session_id: str,
        run_id: str | None,
        status: str | None,
    ) -> str:
        _ = run_id
        suffix = _task_created_suffix(status)
        lines = [f"🚀 已创建任务{suffix}"]
        if session_id:
            lines.append(f"🌐 前端查看: {self.session_url(session_id)}")
        return "\n".join(lines)

    def format_terminal_notification(
        self,
        *,
        session_id: str,
        title: str | None,
        status: str,
        run_id: str | None,
        last_error: str | None,
    ) -> str:
        _ = run_id
        clean_title = (title or "").strip()
        normalized_status = _normalize_status(status)
        header = _terminal_header(normalized_status)
        lines = [header]
        if clean_title:
            lines.append(f"📝 标题: {clean_title}")
        if normalized_status == "failed" and last_error:
            err = last_error.strip()
            if len(err) > 800:
                err = err[:800] + "...(truncated)"
            lines.append(f"⚠️ 错误: {err}")
        lines.append(f"🌐 前端查看: {self.session_url(session_id)}")
        return "\n".join(lines)

    def format_assistant_text_update(
        self,
        *,
        session_id: str,
        text: str,
        title: str | None = None,
    ) -> str:
        _ = session_id, title
        clean_text = _clean_stream_text(text)
        if not clean_text:
            return ""
        return f"💬 {clean_text}"

    def format_user_input_request(
        self,
        *,
        request_id: str,
        session_id: str,
        tool_name: str,
        tool_input: dict[str, Any] | None,
        expires_at: str | None,
        title: str | None = None,
    ) -> str:
        lines: list[str] = ["需要你的输入"]
        clean_title = (title or "").strip()
        if clean_title:
            lines.append(f"标题: {clean_title}")
        lines.append(f"session_id: {session_id}")
        lines.append(f"request_id: {request_id}")
        lines.append(f"tool: {tool_name}")
        if expires_at:
            lines.append(f"expires_at: {expires_at}")

        if tool_name == "ExitPlanMode":
            plan = ""
            if isinstance(tool_input, dict):
                plan = str(tool_input.get("plan") or "").strip()
            if plan:
                if len(plan) > 1200:
                    plan = plan[:1200] + "...(truncated)"
                lines.append("")
                lines.append("Plan:")
                lines.append(plan)
            lines.append("")
            lines.append("请使用 /answer 回复：")
            lines.append(f'/answer {request_id} {{"approved":"true"}}')
            lines.append(f'/answer {request_id} {{"approved":"false"}}')
            return "\n".join(lines)

        questions = []
        if isinstance(tool_input, dict):
            raw = tool_input.get("questions")
            if isinstance(raw, list):
                questions = [q for q in raw if isinstance(q, dict)]

        if questions:
            lines.append("")
            lines.append("问题：")
            for idx, q in enumerate(questions, start=1):
                header = str(q.get("header") or "").strip()
                question = str(q.get("question") or "").strip()
                multi = bool(q.get("multiSelect"))
                if header:
                    lines.append(f"{idx}. {header}")
                if question:
                    lines.append(f"   - {question}")
                lines.append(f"   - 多选: {'是' if multi else '否'}")
                options = q.get("options")
                if isinstance(options, list) and options:
                    lines.append("   - 选项:")
                    for opt in options:
                        if not isinstance(opt, dict):
                            continue
                        label = str(opt.get("label") or "").strip()
                        desc = str(opt.get("description") or "").strip()
                        if not label:
                            continue
                        suffix = f" ({desc})" if desc else ""
                        lines.append(f"     * {label}{suffix}")

        lines.append("")
        lines.append("请使用 JSON 回复（key 为问题文本 question）：")
        example = {"<question>": "<answer>"}
        lines.append(f"/answer {request_id} {json.dumps(example, ensure_ascii=False)}")
        lines.append(f"前端查看: {self.session_url(session_id)}")
        return "\n".join(lines)


@dataclass(slots=True)
class ParsedCommand:
    name: str
    args: str


class CommandService:
    def __init__(self) -> None:
        self.backend = BackendClient()
        self.formatter = MessageFormatter()
        self._handlers: dict[str, CommandHandler] = {
            "help": self._cmd_help,
            "start": self._cmd_help,
            "list": self._cmd_list,
            "new": self._cmd_new,
            "connect": self._cmd_connect,
            "watch": self._cmd_watch,
            "watches": self._cmd_watches,
            "watchlist": self._cmd_watches,
            "unwatch": self._cmd_unwatch,
            "link": self._cmd_link,
            "current": self._cmd_link,
            "clear": self._cmd_clear,
            "disconnect": self._cmd_clear,
            "answer": self._cmd_answer,
        }

    async def handle_text(
        self,
        *,
        db: Session,
        channel: Channel,
        text: str,
    ) -> list[str]:
        clean = _normalize_incoming_text(text)
        if not clean:
            return [self._help_text()]

        if clean.startswith("/"):
            parsed = _parse_command(clean)
            if not parsed:
                return [self._help_text()]
            handler = self._handlers.get(parsed.name)
            if not handler:
                return [self._help_text()]
            return await handler(db, channel, parsed.args)

        active = ActiveSessionRepository.get_by_channel(db, channel_id=channel.id)
        if not active:
            return [
                "当前未连接会话。请先使用 /list 查看会话，或 /new 创建新会话，然后 /connect 连接。"
            ]

        try:
            result = await self.backend.enqueue_task(
                prompt=clean,
                session_id=active.session_id,
            )
        except BackendClientError as exc:
            logger.warning("enqueue_task_failed", extra={"error": str(exc)})
            return [f"发送失败：{exc}"]

        session_id = str(result.get("session_id") or active.session_id)
        run_id = str(result.get("run_id") or "")
        status = str(result.get("status") or "")
        self._ensure_watch(db, channel_id=channel.id, session_id=session_id)
        return [
            self.formatter.format_task_created(
                session_id=session_id,
                run_id=run_id or None,
                status=status or None,
            )
        ]

    async def _cmd_help(self, db: Session, channel: Channel, args: str) -> list[str]:
        _ = db, channel, args
        return [self._help_text()]

    async def _cmd_list(self, db: Session, channel: Channel, args: str) -> list[str]:
        limit = _parse_positive_int(args, default=10, max_value=30)
        try:
            sessions = await self.backend.list_sessions(
                limit=limit, offset=0, kind="chat"
            )
        except BackendClientError as exc:
            return [f"查询失败：{exc}"]

        if not sessions:
            return ["暂无会话。你可以使用 /new <任务描述> 创建会话。"]

        active = ActiveSessionRepository.get_by_channel(db, channel_id=channel.id)
        active_session_id = active.session_id if active else ""
        watched_set = {
            row.session_id
            for row in WatchRepository.list_by_channel(db, channel_id=channel.id)
        }

        lines = [f"最近会话（最多 {limit} 条）："]
        for idx, item in enumerate(sessions, start=1):
            session_id = _extract_session_id(item)
            if not session_id:
                continue
            status = str(item.get("status") or "unknown")
            title = str(item.get("title") or "").strip() or "(无标题)"
            short_id = session_id[:8]

            tags: list[str] = []
            if session_id == active_session_id:
                tags.append("👉 当前")
            if session_id in watched_set:
                tags.append("👀 订阅")
            tag_str = f" [{' / '.join(tags)}]" if tags else ""
            lines.append(
                f"{idx}. {_format_status_badge(status)} {title} ({short_id}){tag_str}"
            )

        lines.append("")
        lines.append("使用 /connect <序号|session_id> 连接会话")
        lines.append("使用 /new <任务描述> 创建并连接新会话")
        return ["\n".join(lines)]

    async def _cmd_new(self, db: Session, channel: Channel, args: str) -> list[str]:
        prompt = args.strip()
        if not prompt:
            return ["用法：/new <任务描述>"]

        try:
            result = await self.backend.enqueue_task(prompt=prompt)
        except BackendClientError as exc:
            return [f"创建失败：{exc}"]

        session_id = str(result.get("session_id") or "")
        run_id = str(result.get("run_id") or "")
        status = str(result.get("status") or "")
        if session_id:
            self._set_active_session(db, channel_id=channel.id, session_id=session_id)
            self._ensure_watch(db, channel_id=channel.id, session_id=session_id)

        created_text = self.formatter.format_task_created(
            session_id=session_id,
            run_id=run_id or None,
            status=status or None,
        )
        return [f"{created_text}\n已自动连接该会话。"]

    async def _cmd_connect(self, db: Session, channel: Channel, args: str) -> list[str]:
        ref = args.strip()
        if not ref:
            return ["用法：/connect <session_id|序号>"]

        try:
            session_id = await self._resolve_session_ref(ref)
            await self.backend.get_session_state(session_id=session_id)
        except BackendClientError as exc:
            return [f"连接失败：{exc}"]
        except ValueError as exc:
            return [str(exc)]

        self._set_active_session(db, channel_id=channel.id, session_id=session_id)
        self._ensure_watch(db, channel_id=channel.id, session_id=session_id)
        return [
            f"🔗 已连接会话：{session_id}\n"
            f"🌐 前端查看: {self.formatter.session_url(session_id)}"
        ]

    async def _cmd_watch(self, db: Session, channel: Channel, args: str) -> list[str]:
        session_id = args.strip()
        if not session_id:
            return ["用法：/watch <session_id>"]
        self._ensure_watch(db, channel_id=channel.id, session_id=session_id)
        return [
            f"👀 已订阅会话：{session_id}\n"
            f"🌐 前端查看: {self.formatter.session_url(session_id)}"
        ]

    async def _cmd_watches(self, db: Session, channel: Channel, args: str) -> list[str]:
        _ = args
        watches = WatchRepository.list_by_channel(db, channel_id=channel.id)
        if not watches:
            return ["当前没有订阅会话。可用 /watch <session_id> 添加订阅。"]

        active = ActiveSessionRepository.get_by_channel(db, channel_id=channel.id)
        active_session_id = active.session_id if active else ""

        lines = [f"当前订阅列表（共 {len(watches)} 条）："]
        for idx, watch in enumerate(watches, start=1):
            marker = " [👉 当前]" if watch.session_id == active_session_id else ""
            lines.append(f"{idx}. {watch.session_id}{marker}")

        lines.append("")
        lines.append("使用 /unwatch <序号|session_id> 取消订阅")
        return ["\n".join(lines)]

    async def _cmd_unwatch(self, db: Session, channel: Channel, args: str) -> list[str]:
        ref = args.strip()
        if not ref:
            return ["用法：/unwatch <session_id|序号>"]

        try:
            session_id = self._resolve_watch_ref(db, channel_id=channel.id, ref=ref)
        except ValueError as exc:
            return [str(exc)]

        watch = WatchRepository.get_watch(
            db,
            channel_id=channel.id,
            session_id=session_id,
        )
        if watch is None:
            return [f"未找到订阅：{session_id}"]
        WatchRepository.delete(db, watch)
        return [f"✅ 已取消订阅：{session_id}"]

    async def _cmd_link(self, db: Session, channel: Channel, args: str) -> list[str]:
        _ = args
        active = ActiveSessionRepository.get_by_channel(db, channel_id=channel.id)
        if not active:
            return [
                "当前没有绑定的会话。用 /list 查看会话并 /connect，或者用 /new 创建。"
            ]
        return [
            f"👉 当前会话：{active.session_id}\n"
            f"🌐 前端查看: {self.formatter.session_url(active.session_id)}"
        ]

    async def _cmd_clear(self, db: Session, channel: Channel, args: str) -> list[str]:
        _ = args
        active = ActiveSessionRepository.get_by_channel(db, channel_id=channel.id)
        if active is not None:
            ActiveSessionRepository.delete(db, active)
        return ["已清除当前会话绑定"]

    async def _cmd_answer(self, db: Session, channel: Channel, args: str) -> list[str]:
        _ = db, channel
        parts = args.split(maxsplit=1)
        request_id = parts[0].strip() if parts else ""
        raw_json = parts[1].strip() if len(parts) > 1 else ""
        if not request_id or not raw_json:
            return ['用法：/answer <request_id> {"问题": "答案"}']

        try:
            parsed = json.loads(raw_json)
        except Exception:
            return [
                '答案 JSON 解析失败，请检查格式，例如：/answer <id> {"question":"answer"}'
            ]

        if not isinstance(parsed, dict):
            return ['答案必须是 JSON object，例如：{"question":"answer"}']

        answers: dict[str, str] = {}
        for key, value in parsed.items():
            if not isinstance(key, str):
                continue
            answers[key] = value if isinstance(value, str) else str(value)

        if not answers:
            return ["未解析到有效答案"]

        try:
            await self.backend.answer_user_input_request(
                request_id=request_id,
                answers=answers,
            )
        except BackendClientError as exc:
            return [f"提交失败：{exc}"]

        return ["已提交"]

    async def _resolve_session_ref(self, ref: str) -> str:
        raw = ref.strip()
        if not raw:
            raise ValueError("会话标识不能为空")

        if raw.isdigit():
            index = int(raw)
            if index <= 0:
                raise ValueError("会话序号必须大于 0")
            limit = min(max(index, 10), 50)
            sessions = await self.backend.list_sessions(
                limit=limit, offset=0, kind="chat"
            )
            if index > len(sessions):
                raise ValueError(f"序号超出范围：当前仅有 {len(sessions)} 条可选")
            session_id = _extract_session_id(sessions[index - 1])
            if not session_id:
                raise ValueError("无法解析会话 ID，请改用完整 session_id")
            return session_id

        return raw

    def _resolve_watch_ref(self, db: Session, *, channel_id: int, ref: str) -> str:
        raw = ref.strip()
        if not raw:
            raise ValueError("订阅标识不能为空")

        if raw.isdigit():
            index = int(raw)
            if index <= 0:
                raise ValueError("订阅序号必须大于 0")
            watches = WatchRepository.list_by_channel(db, channel_id=channel_id)
            if not watches:
                raise ValueError("当前没有订阅会话。可用 /watch <session_id> 添加。")
            if index > len(watches):
                raise ValueError(f"序号超出范围：当前仅有 {len(watches)} 条订阅")
            return watches[index - 1].session_id

        return raw

    def _set_active_session(
        self,
        db: Session,
        *,
        channel_id: int,
        session_id: str,
    ) -> None:
        existing = ActiveSessionRepository.get_by_channel(db, channel_id=channel_id)
        if existing is not None:
            existing.session_id = session_id
            return

        entry = ActiveSessionRepository.create(
            db, channel_id=channel_id, session_id=session_id
        )
        try:
            with db.begin_nested():
                db.flush([entry])
        except IntegrityError:
            existing = ActiveSessionRepository.get_by_channel(db, channel_id=channel_id)
            if existing is None:
                raise
            existing.session_id = session_id
            db.flush([existing])

    def _ensure_watch(
        self,
        db: Session,
        *,
        channel_id: int,
        session_id: str,
    ) -> None:
        existing = WatchRepository.get_watch(
            db,
            channel_id=channel_id,
            session_id=session_id,
        )
        if existing is not None:
            return

        entry = WatchRepository.create(db, channel_id=channel_id, session_id=session_id)
        try:
            with db.begin_nested():
                db.flush([entry])
        except IntegrityError:
            existing = WatchRepository.get_watch(
                db,
                channel_id=channel_id,
                session_id=session_id,
            )
            if existing is None:
                raise

    def _help_text(self) -> str:
        return (
            "可用命令：\n"
            "/help  查看命令帮助\n"
            "/list [n]  查看最近会话（默认 10）\n"
            "/connect <session_id|序号>  连接到会话\n"
            "/new <任务>  创建新会话并自动连接\n"
            "/watch <session_id>  订阅某个会话（前端会话也可）\n"
            "/watches  查看全部订阅\n"
            "/unwatch <session_id|序号>  取消订阅\n"
            "/link  查看当前连接会话\n"
            "/clear  清除当前会话绑定\n"
            '/answer <request_id> {"问题":"答案"}  回答 AskQuestion\n'
            '/answer <request_id> {"approved":"true|false"}  回答 Plan Approval\n'
            "\n"
            "普通文本：如果已连接会话，会作为续聊消息发送。"
        )


class InboundMessageService:
    def __init__(self) -> None:
        self.commands = CommandService()
        self.gateway = NotificationGateway()

    async def handle_message(self, *, message: InboundMessage) -> None:
        db = SessionLocal()
        responses: list[str] = []
        send_address: str | None = None
        try:
            if message.message_id:
                dedup_key = f"in:{message.provider}:{message.message_id}"
                if not self._register_inbound_dedup(db, key=dedup_key):
                    return

            channel = self._get_or_create_channel(
                db,
                provider=message.provider,
                destination=message.destination,
            )
            if not channel.enabled:
                logger.info(
                    "im_channel_disabled_ignoring_inbound",
                    extra={
                        "provider": message.provider,
                        "destination": message.destination,
                        "channel_id": channel.id,
                    },
                )
                db.commit()
                return

            send_address = self._resolve_send_address(
                db, channel=channel, message=message
            )
            responses = await self.commands.handle_text(
                db=db, channel=channel, text=message.text
            )
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        if not responses:
            return

        target = send_address or message.destination
        for resp in responses:
            sent = await self.gateway.send_text(
                provider=message.provider,
                destination=target,
                text=resp,
            )
            if not sent:
                logger.warning(
                    "im_inbound_reply_failed",
                    extra={"provider": message.provider, "destination": target},
                )

    def _register_inbound_dedup(self, db: Session, *, key: str) -> bool:
        row = DedupRepository.create(db, key=key)
        try:
            with db.begin_nested():
                db.flush([row])
        except IntegrityError:
            return False
        return True

    def _get_or_create_channel(
        self,
        db: Session,
        *,
        provider: str,
        destination: str,
    ) -> Channel:
        existing = ChannelRepository.get_by_provider_destination(
            db,
            provider=provider,
            destination=destination,
        )
        if existing is not None:
            return existing

        channel = ChannelRepository.create(
            db, provider=provider, destination=destination
        )
        try:
            with db.begin_nested():
                db.flush([channel])
        except IntegrityError:
            existing = ChannelRepository.get_by_provider_destination(
                db,
                provider=provider,
                destination=destination,
            )
            if existing is not None:
                return existing
            raise
        return channel

    def _resolve_send_address(
        self,
        db: Session,
        *,
        channel: Channel,
        message: InboundMessage,
    ) -> str:
        candidate = (message.send_address or "").strip()
        if candidate:
            current = ChannelDeliveryRepository.get_by_channel(
                db, channel_id=channel.id
            )
            if current is not None:
                current.send_address = candidate
                return candidate

            delivery = ChannelDeliveryRepository.create(
                db,
                channel_id=channel.id,
                send_address=candidate,
            )
            try:
                with db.begin_nested():
                    db.flush([delivery])
            except IntegrityError:
                current = ChannelDeliveryRepository.get_by_channel(
                    db, channel_id=channel.id
                )
                if current is None:
                    raise
                current.send_address = candidate
            return candidate

        stored = ChannelDeliveryRepository.get_send_address(db, channel_id=channel.id)
        return (stored or "").strip() or channel.destination


class BackendEventService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.formatter = MessageFormatter()
        self.gateway = NotificationGateway()

    async def process_event(self, db: Session, *, event: ImBackendEvent) -> int:
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

        if event.type == "assistant_message.created":
            message = event.message
            if message is None or not message.text.strip():
                return 0
            delivered = 0
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
                    self._commit_processed_key(db, key=key)
                    continue
                if not await self._send_to_channel(
                    db, channel_id=channel_id, text=rendered
                ):
                    raise RuntimeError(
                        f"failed to deliver assistant message event to channel {channel_id}"
                    )
                self._commit_processed_key(db, key=key)
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
            delivered = 0
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
                self._commit_processed_key(db, key=key)
                delivered += 1
            return delivered

        if event.type == "user_input_request.created":
            request = event.user_input_request
            if request is None or request.status != "pending":
                return 0
            delivered = 0
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
                self._commit_processed_key(db, key=key)
                delivered += 1
            return delivered

        return 0

    def _commit_processed_key(self, db: Session, *, key: str) -> None:
        try:
            self._mark_processed_key(db, key=key)
            db.commit()
        except Exception:
            db.rollback()
            raise

    def _mark_processed_key(self, db: Session, *, key: str) -> None:
        if DedupRepository.exists(db, key=key):
            return
        row = DedupRepository.create(db, key=key)
        try:
            with db.begin_nested():
                db.flush([row])
        except IntegrityError:
            return

    def _get_target_channel_ids(self, db: Session, *, session_id: str) -> set[int]:
        target: set[int] = set()

        for channel in ChannelRepository.list_enabled(db):
            if channel.subscribe_all:
                target.add(channel.id)

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
        channel = ChannelRepository.get_by_id(db, channel_id=channel_id)
        if channel is None or not channel.enabled:
            return True

        if channel.provider == "dingtalk":
            destination = channel.destination
        else:
            destination = (
                ChannelDeliveryRepository.get_send_address(db, channel_id=channel_id)
                or channel.destination
            )

        return await self.gateway.send_text(
            provider=channel.provider,
            destination=destination,
            text=text,
        )


class ImEventService:
    EVENT_VERSION = 1

    def enqueue_assistant_message_created(
        self,
        db: Session,
        *,
        db_session: AgentSession,
        db_run: AgentRun | None,
        db_message: AgentMessage,
        raw_message: dict[str, Any],
        callback: AgentCallbackRequest,
    ) -> None:
        text = _extract_visible_assistant_text(raw_message)
        if not text:
            return

        event = ImBackendEvent(
            id=str(uuid.uuid4()),
            type="assistant_message.created",
            version=self.EVENT_VERSION,
            occurred_at=callback.time,
            user_id=db_session.user_id,
            session=_build_session_snapshot(db_session),
            run=_build_run_snapshot(
                db_run,
                callback_status=callback.status.value,
                error_message=callback.error_message,
            ),
            state=_build_state_snapshot(callback),
            message=MessageSnapshot(
                id=db_message.id,
                role="assistant",
                text=text,
                text_preview=(db_message.text_preview or text[:500] or None),
            ),
        )
        ImEventOutboxRepository.create_if_absent(
            db,
            event_key=f"assistant-message:{db_message.id}",
            event_type=event.type,
            event_version=event.version,
            user_id=db_session.user_id,
            session_id=db_session.id,
            run_id=db_run.id if db_run is not None else None,
            message_id=db_message.id,
            user_input_request_id=None,
            payload=event.model_dump(mode="json"),
        )

    def enqueue_run_terminal(
        self,
        db: Session,
        *,
        db_session: AgentSession,
        db_run: AgentRun | None,
        callback: AgentCallbackRequest,
    ) -> None:
        terminal_run = db_run
        if terminal_run is None:
            terminal_run = RunRepository.get_latest_terminal_by_session(
                db, db_session.id
            )

        run_status = (
            terminal_run.status
            if terminal_run is not None and (terminal_run.status or "").strip()
            else callback.status.value
        )
        event_key = (
            f"run-terminal:{terminal_run.id}:{run_status}"
            if terminal_run is not None
            else f"run-terminal:session:{db_session.id}:{run_status}"
        )
        event = ImBackendEvent(
            id=str(uuid.uuid4()),
            type="run.terminal",
            version=self.EVENT_VERSION,
            occurred_at=callback.time,
            user_id=db_session.user_id,
            session=_build_session_snapshot(db_session),
            run=_build_run_snapshot(
                terminal_run,
                callback_status=callback.status.value,
                error_message=callback.error_message,
            ),
            state=_build_state_snapshot(callback),
        )
        ImEventOutboxRepository.create_if_absent(
            db,
            event_key=event_key,
            event_type=event.type,
            event_version=event.version,
            user_id=db_session.user_id,
            session_id=db_session.id,
            run_id=terminal_run.id if terminal_run is not None else None,
            message_id=None,
            user_input_request_id=None,
            payload=event.model_dump(mode="json"),
        )

    def enqueue_user_input_request_created(
        self,
        db: Session,
        *,
        db_session: AgentSession,
        request: UserInputRequest,
    ) -> None:
        event = ImBackendEvent(
            id=str(uuid.uuid4()),
            type="user_input_request.created",
            version=self.EVENT_VERSION,
            occurred_at=request.created_at or datetime.now(timezone.utc),
            user_id=db_session.user_id,
            session=_build_session_snapshot(db_session),
            user_input_request=UserInputRequestSnapshot(
                id=str(request.id),
                tool_name=request.tool_name,
                tool_input=request.tool_input or {},
                status=request.status,
                expires_at=request.expires_at,
                answered_at=request.answered_at,
            ),
        )
        ImEventOutboxRepository.create_if_absent(
            db,
            event_key=f"user-input-created:{request.id}",
            event_type=event.type,
            event_version=event.version,
            user_id=db_session.user_id,
            session_id=db_session.id,
            run_id=None,
            message_id=None,
            user_input_request_id=request.id,
            payload=event.model_dump(mode="json"),
        )


@dataclass(slots=True)
class ClaimedEvent:
    id: str
    event_type: str
    attempt_count: int
    payload: dict


class ImEventDispatcher:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._backend_event_service = BackendEventService()

    @property
    def enabled(self) -> bool:
        return bool(self.settings.im_event_dispatch_enabled)

    async def run_forever(self) -> None:
        if not self.enabled:
            logger.info("im_event_dispatcher_disabled")
            return

        interval = max(0.2, float(self.settings.im_event_dispatch_interval_seconds))
        while True:
            try:
                await self._dispatch_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("im_event_dispatcher_iteration_failed")
            await asyncio.sleep(interval)

    async def _dispatch_once(self) -> None:
        batch_size = max(1, int(self.settings.im_event_dispatch_batch_size))
        lease_seconds = max(5, int(self.settings.im_event_dispatch_lease_seconds))
        claimed = await asyncio.to_thread(
            self._claim_due_batch, batch_size, lease_seconds
        )
        if not claimed:
            return

        for event in claimed:
            try:
                await self._deliver(event)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                delay = min(60.0, float(2 ** min(event.attempt_count, 6)))
                await asyncio.to_thread(self._mark_retry, event.id, str(exc), delay)
                logger.warning(
                    "im_event_delivery_failed",
                    extra={
                        "event_id": event.id,
                        "event_type": event.event_type,
                        "attempt_count": event.attempt_count,
                        "error": str(exc),
                    },
                )
            else:
                await asyncio.to_thread(self._mark_delivered, event.id)

    async def _deliver(self, event: ClaimedEvent) -> None:
        parsed = ImBackendEvent.model_validate(event.payload)
        db = SessionLocal()
        try:
            await self._backend_event_service.process_event(db, event=parsed)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _claim_due_batch(limit: int, lease_seconds: int) -> list[ClaimedEvent]:
        db = SessionLocal()
        try:
            rows = ImEventOutboxRepository.claim_due_batch(
                db,
                limit=limit,
                lease_seconds=lease_seconds,
            )
            db.commit()
            claimed: list[ClaimedEvent] = []
            for row in rows:
                payload = row.payload if isinstance(row.payload, dict) else {}
                claimed.append(
                    ClaimedEvent(
                        id=str(row.id),
                        event_type=row.event_type,
                        attempt_count=int(row.attempt_count or 0),
                        payload=payload,
                    )
                )
            return claimed
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _mark_delivered(event_id: str) -> None:
        db = SessionLocal()
        try:
            ImEventOutboxRepository.mark_delivered(db, event_id=event_id)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _mark_retry(event_id: str, error_message: str, delay_seconds: float) -> None:
        db = SessionLocal()
        try:
            ImEventOutboxRepository.mark_retry(
                db,
                event_id=event_id,
                error_message=error_message,
                delay_seconds=delay_seconds,
            )
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


def _parse_uuid(
    value: str | None,
    *,
    field_name: str,
    required: bool = False,
) -> uuid.UUID | None:
    raw = (value or "").strip()
    if not raw:
        if required:
            raise BackendClientError(f"{field_name} cannot be empty")
        return None
    try:
        return uuid.UUID(raw)
    except ValueError as exc:
        raise BackendClientError(f"Invalid {field_name}: {raw}") from exc


def _log_background_task_exception(task: asyncio.Task[None]) -> None:
    try:
        task.result()
    except Exception:
        logger.exception("embedded_session_title_generation_failed")


def _normalize_status(status: str | None) -> str:
    normalized = (status or "").strip().lower()
    if normalized == "cancelled":
        return "canceled"
    return normalized or "unknown"


def _task_created_suffix(status: str | None) -> str:
    normalized = _normalize_status(status)
    if normalized in {"queued", "pending", "created", "scheduled"}:
        return "，当前排队中 🕒"
    if normalized in {"claimed", "running", "in_progress", "executing"}:
        return "，已开始运行 ⏳"
    if normalized in {"completed", "done", "success", "succeeded"}:
        return "，已完成 ✅"
    if normalized in {"failed", "error"}:
        return "，执行失败 ❌"
    if normalized in {"canceled", "aborted"}:
        return "，已取消 🚫"
    return ""


def _terminal_header(status: str) -> str:
    if status == "completed":
        return "✅ 任务完成（已同步全部结果）"
    if status == "failed":
        return "❌ 任务失败"
    if status == "canceled":
        return "🚫 任务已取消"
    if status in {"claimed", "running", "in_progress", "executing"}:
        return "⏳ 任务进行中"
    if status in {"queued", "pending", "created", "scheduled"}:
        return "🕒 任务排队中"
    return f"📌 任务状态更新（{status}）"


def _clean_stream_text(text: str) -> str:
    cleaned = (text or "").replace("\ufffd", "").strip()
    if len(cleaned) > 3000:
        return cleaned[:3000] + "\n...(truncated)"
    return cleaned


def _parse_command(text: str) -> ParsedCommand | None:
    raw = text.strip()
    if not raw.startswith("/"):
        return None
    body = raw[1:]
    if not body:
        return None
    parts = body.split(maxsplit=1)
    name = parts[0].strip().lower()
    args = parts[1].strip() if len(parts) > 1 else ""
    if not name:
        return None
    return ParsedCommand(name=name, args=args)


def _extract_session_id(item: dict) -> str:
    if not isinstance(item, dict):
        return ""
    return str(item.get("session_id") or item.get("id") or "").strip()


def _parse_positive_int(raw: str, *, default: int, max_value: int) -> int:
    text = raw.strip()
    if not text:
        return default
    try:
        value = int(text)
    except ValueError:
        return default
    if value <= 0:
        return default
    return min(value, max_value)


def _format_status_badge(status: str) -> str:
    text = status.strip() or "unknown"
    return f"{_status_emoji(text)} [{text}]"


def _status_emoji(status: str) -> str:
    normalized = status.strip().lower()
    if normalized in {"completed", "done", "success", "succeeded"}:
        return "✅"
    if normalized in {"claimed", "running", "in_progress", "executing"}:
        return "⏳"
    if normalized in {"pending", "queued", "scheduled", "created"}:
        return "🕒"
    if normalized in {"failed", "error"}:
        return "❌"
    if normalized in {"cancelled", "canceled", "aborted"}:
        return "🚫"
    return "❔"


def _normalize_incoming_text(text: str) -> str:
    clean = (text or "").strip()
    if not clean:
        return ""

    clean = clean.replace("\u2005", " ").replace("\u2006", " ")
    clean = clean.replace("\u200b", "").replace("\ufeff", "").strip()

    while True:
        matched = _LEADING_AT_TAG_RE.match(clean)
        if not matched:
            break
        clean = clean[matched.end() :].strip()

    while True:
        matched = _LEADING_MENTION_RE.match(clean)
        if not matched:
            break
        clean = clean[matched.end() :].strip()

    if clean.startswith("／"):
        clean = "/" + clean[1:]

    return clean


def _build_session_snapshot(db_session: AgentSession) -> SessionSnapshot:
    return SessionSnapshot(
        id=str(db_session.id),
        title=(db_session.title or None),
        status=db_session.status,
    )


def _build_run_snapshot(
    db_run: AgentRun | None,
    *,
    callback_status: str | None = None,
    error_message: str | None = None,
) -> RunSnapshot | None:
    if db_run is None and not callback_status:
        return None
    return RunSnapshot(
        id=str(db_run.id) if db_run is not None else None,
        status=(db_run.status if db_run is not None else callback_status),
        progress=(db_run.progress if db_run is not None else None),
        error_message=(
            db_run.last_error
            if db_run is not None and db_run.last_error
            else error_message
        ),
    )


def _build_state_snapshot(callback: AgentCallbackRequest) -> EventStateSnapshot | None:
    state_patch = callback.state_patch
    if state_patch is None:
        return None
    todos = state_patch.todos or []
    completed = sum(1 for item in todos if item.status == "completed")
    return EventStateSnapshot(
        callback_status=callback.status.value,
        current_step=state_patch.current_step,
        todos_total=len(todos),
        todos_completed=completed,
    )


def _extract_visible_assistant_text(message: dict[str, Any]) -> str:
    message_type = str(message.get("_type") or "").strip()
    if "ResultMessage" in message_type:
        result = message.get("result")
        if isinstance(result, str) and result.strip():
            return result.replace("\ufffd", "").strip()
        return ""

    if "AssistantMessage" not in message_type:
        return ""

    content = message.get("content")
    if not isinstance(content, list):
        return ""

    raw_texts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("parent_tool_use_id"):
            continue
        if "TextBlock" not in str(block.get("_type") or ""):
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
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)

    return "\n\n".join(cleaned)
