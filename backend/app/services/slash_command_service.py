import re

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.slash_command import SlashCommand
from app.repositories.slash_command_repository import SlashCommandRepository
from app.schemas.slash_command import (
    SlashCommandAdminResponse,
    SlashCommandCreateRequest,
    SlashCommandMode,
    SlashCommandResponse,
    SlashCommandUpdateRequest,
)
from app.services.constants import SYSTEM_USER_ID


_COMMAND_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
_RESERVED_COMMAND_NAMES = {"clear", "compact", "help"}


def _validate_command_name(name: str) -> str:
    value = (name or "").strip()
    if not value or value in {".", ".."} or not _COMMAND_NAME_PATTERN.fullmatch(value):
        raise AppException(
            error_code=ErrorCode.BAD_REQUEST,
            message=f"Invalid slash command name: {name}",
        )
    if value in _RESERVED_COMMAND_NAMES:
        raise AppException(
            error_code=ErrorCode.BAD_REQUEST,
            message=f"Slash command name is reserved: {value}",
        )
    return value


def _normalize_mode(mode: str | None) -> SlashCommandMode:
    value = (mode or "").strip() or "raw"
    if value == "raw":
        return "raw"
    if value == "structured":
        return "structured"
    else:
        raise AppException(
            error_code=ErrorCode.BAD_REQUEST,
            message=f"Invalid slash command mode: {mode}",
        )


def _require_non_empty(value: str | None, *, field: str) -> str:
    text = (value or "").strip()
    if not text:
        raise AppException(
            error_code=ErrorCode.BAD_REQUEST,
            message=f"{field} cannot be empty",
        )
    return text


class SlashCommandService:
    def list_commands(self, db: Session, user_id: str) -> list[SlashCommandResponse]:
        commands = SlashCommandRepository.list_visible_by_user(
            db, user_id=user_id, system_user_id=SYSTEM_USER_ID
        )
        return [self._to_response(c) for c in commands]

    def list_commands_for_admin(
        self, db: Session, user_id: str
    ) -> list[SlashCommandAdminResponse]:
        commands = SlashCommandRepository.list_by_user(db, user_id=user_id)
        return [self._to_admin_response(c) for c in commands]

    def get_command(
        self, db: Session, user_id: str, command_id: int
    ) -> SlashCommandResponse:
        command = SlashCommandRepository.get_by_id(db, command_id)
        if not command or command.user_id != user_id:
            raise AppException(
                error_code=ErrorCode.SLASH_COMMAND_NOT_FOUND,
                message=f"Slash command not found: {command_id}",
            )
        return self._to_response(command)

    def create_command(
        self, db: Session, user_id: str, request: SlashCommandCreateRequest
    ) -> SlashCommandResponse:
        name = _validate_command_name(request.name)
        mode = _normalize_mode(request.mode)

        if SlashCommandRepository.get_by_name(db, user_id=user_id, name=name):
            raise AppException(
                error_code=ErrorCode.SLASH_COMMAND_ALREADY_EXISTS,
                message=f"Slash command already exists: {name}",
            )

        raw_markdown = request.raw_markdown
        content = request.content
        if mode == "raw":
            raw_markdown = _require_non_empty(raw_markdown, field="raw_markdown")
            content = None
        else:
            content = _require_non_empty(content, field="content")
            raw_markdown = None

        command = SlashCommand(
            user_id=user_id,
            name=name,
            enabled=bool(request.enabled),
            mode=mode,
            description=(request.description or "").strip() or None,
            argument_hint=(request.argument_hint or "").strip() or None,
            allowed_tools=(request.allowed_tools or "").strip() or None,
            content=content,
            raw_markdown=raw_markdown,
        )

        SlashCommandRepository.create(db, command)
        db.commit()
        db.refresh(command)
        return self._to_response(command)

    def update_command(
        self,
        db: Session,
        user_id: str,
        command_id: int,
        request: SlashCommandUpdateRequest,
    ) -> SlashCommandResponse:
        command = SlashCommandRepository.get_by_id(db, command_id)
        if not command or command.user_id != user_id:
            raise AppException(
                error_code=ErrorCode.SLASH_COMMAND_NOT_FOUND,
                message=f"Slash command not found: {command_id}",
            )

        if command.user_id == SYSTEM_USER_ID and user_id != SYSTEM_USER_ID:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Cannot modify system slash commands",
            )

        if (
            request.name is not None
            and request.name.strip()
            and request.name != command.name
        ):
            new_name = _validate_command_name(request.name)
            if SlashCommandRepository.get_by_name(db, user_id=user_id, name=new_name):
                raise AppException(
                    error_code=ErrorCode.SLASH_COMMAND_ALREADY_EXISTS,
                    message=f"Slash command already exists: {new_name}",
                )
            command.name = new_name

        if request.enabled is not None:
            command.enabled = bool(request.enabled)

        if request.mode is not None:
            command.mode = _normalize_mode(request.mode)

        if request.description is not None:
            command.description = request.description.strip() or None
        if request.argument_hint is not None:
            command.argument_hint = request.argument_hint.strip() or None
        if request.allowed_tools is not None:
            command.allowed_tools = request.allowed_tools.strip() or None

        # Content payload is validated based on the final mode.
        if command.mode == "raw":
            if request.raw_markdown is not None:
                command.raw_markdown = _require_non_empty(
                    request.raw_markdown, field="raw_markdown"
                )
            # Avoid mixing modes.
            if request.content is not None:
                command.content = None
        else:
            if request.content is not None:
                command.content = _require_non_empty(request.content, field="content")
            if request.raw_markdown is not None:
                command.raw_markdown = None

        # Ensure the command stays executable after updates, especially when switching modes.
        if command.mode == "raw" and not (command.raw_markdown or "").strip():
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="raw_markdown cannot be empty",
            )
        if command.mode == "structured" and not (command.content or "").strip():
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="content cannot be empty",
            )

        db.commit()
        db.refresh(command)
        return self._to_response(command)

    def delete_command(self, db: Session, user_id: str, command_id: int) -> None:
        command = SlashCommandRepository.get_by_id(db, command_id)
        if not command or command.user_id != user_id:
            raise AppException(
                error_code=ErrorCode.SLASH_COMMAND_NOT_FOUND,
                message=f"Slash command not found: {command_id}",
            )
        if command.user_id == SYSTEM_USER_ID and user_id != SYSTEM_USER_ID:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Cannot delete system slash commands",
            )
        SlashCommandRepository.delete(db, command)
        db.commit()

    @staticmethod
    def _to_response(command: SlashCommand) -> SlashCommandResponse:
        mode: SlashCommandMode = "structured" if command.mode == "structured" else "raw"
        return SlashCommandResponse(
            id=command.id,
            user_id=command.user_id,
            name=command.name,
            enabled=bool(command.enabled),
            mode=mode,
            description=command.description,
            argument_hint=command.argument_hint,
            allowed_tools=command.allowed_tools,
            content=command.content,
            raw_markdown=command.raw_markdown,
            created_at=command.created_at,
            updated_at=command.updated_at,
        )

    @staticmethod
    def _to_admin_response(command: SlashCommand) -> SlashCommandAdminResponse:
        mode: SlashCommandMode = "structured" if command.mode == "structured" else "raw"
        return SlashCommandAdminResponse(
            id=command.id,
            user_id=command.user_id,
            name=command.name,
            enabled=bool(command.enabled),
            mode=mode,
            description=command.description,
            argument_hint=command.argument_hint,
            allowed_tools=command.allowed_tools,
            content=command.content,
            raw_markdown=command.raw_markdown,
            created_at=command.created_at,
            updated_at=command.updated_at,
        )
