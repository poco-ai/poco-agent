from sqlalchemy.orm import Session

from app.repositories.skill_repository import SkillRepository
from app.repositories.user_skill_install_repository import UserSkillInstallRepository


class SkillConfigService:
    """Service for building skill configs used by the executor manager stager."""

    def resolve_user_skill_files(
        self,
        db: Session,
        user_id: str,
        skill_ids: list[int],
    ) -> dict:
        """Resolve skills for a user given selected skill ids.

        Returns a dict compatible with executor_manager SkillStager:
        {skill_name: {"enabled": True, "entry": {...}}, ...}
        """
        if not skill_ids:
            return {}

        installs = UserSkillInstallRepository.list_by_user(db, user_id)
        installed_ids = {i.skill_id for i in installs}

        # Preserve caller ordering but avoid duplicates.
        ordered_ids: list[int] = []
        seen: set[int] = set()
        for sid in skill_ids:
            if sid in seen:
                continue
            seen.add(sid)
            ordered_ids.append(sid)

        selected: dict[str, tuple[str, dict]] = {}
        for skill_id in ordered_ids:
            if skill_id not in installed_ids:
                continue
            skill = SkillRepository.get_by_id(db, skill_id)
            if not skill or not isinstance(skill.entry, dict):
                continue

            # If both user and system skills share the same name, prefer the user one.
            existing = selected.get(skill.name)
            if existing is None:
                selected[skill.name] = (skill.scope, skill.entry)
                continue
            existing_scope, _ = existing
            if existing_scope != "user" and skill.scope == "user":
                selected[skill.name] = (skill.scope, skill.entry)

        return {
            name: {"enabled": True, "entry": entry}
            for name, (_, entry) in selected.items()
        }
