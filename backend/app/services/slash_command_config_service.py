import json
import re

from sqlalchemy.orm import Session

from app.models.skill import Skill
from app.models.slash_command import SlashCommand
from app.repositories.skill_repository import SkillRepository
from app.repositories.slash_command_repository import SlashCommandRepository
from app.repositories.user_skill_install_repository import UserSkillInstallRepository
from app.schemas.slash_command_config import SlashCommandSuggestionResponse
from app.services.constants import SYSTEM_USER_ID
from app.utils.markdown_front_matter import remove_model_from_yaml_front_matter


_COMMAND_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
_RESERVED_COMMAND_NAMES = {"clear", "compact", "help"}


def _json_string(value: str) -> str:
    # JSON strings are valid YAML scalars, and handle escaping reliably.
    return json.dumps(value)


class SlashCommandConfigService:
    def list_suggestions(
        self,
        db: Session,
        *,
        user_id: str,
        skill_names: list[str] | None = None,
    ) -> list[SlashCommandSuggestionResponse]:
        suggestions: dict[str, SlashCommandSuggestionResponse] = {}

        commands = SlashCommandRepository.list_enabled_visible_by_user(
            db, user_id=user_id, system_user_id=SYSTEM_USER_ID
        )
        for cmd in commands:
            name = self._normalize_command_name(cmd.name)
            if not name or name in _RESERVED_COMMAND_NAMES:
                continue
            suggestions[name] = SlashCommandSuggestionResponse(
                name=name,
                description=cmd.description,
                argument_hint=cmd.argument_hint,
                source="custom",
            )

        for skill_name, skill_description in self._resolve_skill_aliases(
            db, user_id=user_id, skill_names=skill_names
        ):
            if skill_name in _RESERVED_COMMAND_NAMES:
                continue
            if skill_name in suggestions:
                continue
            suggestions[skill_name] = SlashCommandSuggestionResponse(
                name=skill_name,
                description=skill_description or f"Run skill: {skill_name}",
                argument_hint="Describe the task for this skill",
                source="skill",
            )

        return [suggestions[name] for name in sorted(suggestions.keys())]

    def resolve_user_commands(
        self,
        db: Session,
        *,
        user_id: str,
        names: list[str] | None = None,
        skill_names: list[str] | None = None,
    ) -> dict[str, str]:
        name_set = self._normalize_requested_name_set(names)

        commands = SlashCommandRepository.list_enabled_visible_by_user(
            db, user_id=user_id, system_user_id=SYSTEM_USER_ID
        )
        rendered: dict[str, str] = {}
        for cmd in commands:
            name = self._normalize_command_name(cmd.name)
            if not name:
                continue
            if name in _RESERVED_COMMAND_NAMES:
                continue
            if name_set is not None and name not in name_set:
                continue
            rendered[name] = self._render_command(cmd)

        for skill_name, _skill_description in self._resolve_skill_aliases(
            db, user_id=user_id, skill_names=skill_names
        ):
            if skill_name in _RESERVED_COMMAND_NAMES:
                continue
            if name_set is not None and skill_name not in name_set:
                continue
            # Custom slash commands always win over skill aliases with the same name.
            if skill_name in rendered:
                continue
            rendered[skill_name] = self._render_skill_command(skill_name)
        return rendered

    def _render_command(self, command: SlashCommand) -> str:
        mode = (command.mode or "").strip() or "raw"
        if mode == "structured":
            return self._render_structured(command)
        return remove_model_from_yaml_front_matter(command.raw_markdown or "")

    @staticmethod
    def _render_structured(command: SlashCommand) -> str:
        front_lines: list[str] = []
        if command.allowed_tools:
            front_lines.append(f"allowed-tools: {_json_string(command.allowed_tools)}")
        if command.description:
            front_lines.append(f"description: {_json_string(command.description)}")
        if command.argument_hint:
            front_lines.append(f"argument-hint: {_json_string(command.argument_hint)}")

        body = (command.content or "").rstrip()
        if front_lines:
            front = "\n".join(front_lines)
            return f"---\n{front}\n---\n\n{body}\n"
        return body + "\n"

    @staticmethod
    def _render_skill_command(skill_name: str) -> str:
        description = _json_string(f"Run skill: {skill_name}")
        argument_hint = _json_string("Describe the task for this skill")
        body = (
            f'Use the skill "{skill_name}" to complete the request.\n'
            f"Apply instructions from ~/.claude/skills/{skill_name}/SKILL.md.\n"
            "If slash command arguments are provided, treat them as task details.\n"
        )
        return (
            "---\n"
            f"description: {description}\n"
            f"argument-hint: {argument_hint}\n"
            "---\n\n"
            f"{body}"
        )

    @staticmethod
    def _normalize_command_name(name: str | None) -> str | None:
        value = (name or "").strip()
        if not value or value in {".", ".."}:
            return None
        if not _COMMAND_NAME_PATTERN.fullmatch(value):
            return None
        return value

    def _resolve_skill_aliases(
        self,
        db: Session,
        *,
        user_id: str,
        skill_names: list[str] | None = None,
    ) -> list[tuple[str, str | None]]:
        if skill_names is not None:
            provided: list[tuple[str, str | None]] = []
            seen: set[str] = set()
            for raw in skill_names:
                name = self._normalize_command_name(raw)
                if name is None or name in seen:
                    continue
                seen.add(name)
                provided.append((name, None))
            return sorted(provided, key=lambda item: item[0])

        installs = UserSkillInstallRepository.list_by_user(db, user_id=user_id)
        ordered_enabled_ids: list[int] = []
        seen_ids: set[int] = set()
        for install in installs:
            if not install.enabled:
                continue
            if install.skill_id in seen_ids:
                continue
            seen_ids.add(install.skill_id)
            ordered_enabled_ids.append(install.skill_id)

        skills = SkillRepository.list_by_ids(db, ordered_enabled_ids)
        skill_by_id = {skill.id: skill for skill in skills}

        selected: dict[str, tuple[str, str | None]] = {}
        for skill_id in ordered_enabled_ids:
            skill = skill_by_id.get(skill_id)
            if skill is None:
                continue
            if skill.scope != "system" and skill.owner_user_id != user_id:
                continue
            self._merge_skill_alias(selected, skill)

        for skill in SkillRepository.list_visible(db, user_id=user_id):
            if skill.scope != "system":
                continue
            self._merge_skill_alias(selected, skill)

        return [
            (name, description)
            for name, (_scope, description) in sorted(selected.items())
        ]

    def _merge_skill_alias(
        self,
        selected: dict[str, tuple[str, str | None]],
        skill: Skill,
    ) -> None:
        name = self._normalize_command_name(skill.name)
        if not name:
            return

        existing = selected.get(name)
        if existing is None:
            selected[name] = (skill.scope, skill.description)
            return

        existing_scope, _existing_description = existing
        if existing_scope != "user" and skill.scope == "user":
            selected[name] = (skill.scope, skill.description)

    def _normalize_requested_name_set(
        self,
        names: list[str] | None,
    ) -> set[str] | None:
        if names is None:
            return None
        normalized = {
            name
            for raw in names
            if (name := self._normalize_command_name(raw)) is not None
        }
        # Keep historical behavior: empty list means "no filtering".
        return normalized or None
