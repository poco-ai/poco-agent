from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.lifecycle.builtin_skills import BUILTIN_SKILLS, SkillBootstrapService


class BuiltinSkillsTests(unittest.TestCase):
    def test_all_skill_assets_are_declared_as_builtin_skills(self) -> None:
        assets_root = Path(__file__).resolve().parents[1] / "assets" / "skills"
        expected_names = sorted(
            path.parent.name for path in assets_root.glob("*/SKILL.md")
        )

        declared_names = sorted(
            definition.asset_dir_name for definition in BUILTIN_SKILLS
        )

        self.assertEqual(declared_names, expected_names)

    @patch("app.lifecycle.builtin_skills.SkillRepository.get_by_name_and_scope")
    def test_existing_builtin_preserves_admin_disabled_state(
        self,
        get_by_name_and_scope: MagicMock,
    ) -> None:
        existing = SimpleNamespace(
            name="skill-creator",
            description="old",
            scope="system",
            owner_user_id="__system__",
            entry={"s3_key": "old/", "is_prefix": True},
            source={"kind": "system", "managed_by": "lifecycle", "version": "old"},
            admin_disabled=True,
        )
        get_by_name_and_scope.return_value = existing

        db = MagicMock()
        bundle = SkillBootstrapService._build_bundle(BUILTIN_SKILLS[-1])

        result = SkillBootstrapService._ensure_builtin_skill(db, bundle)

        self.assertIs(result, existing)
        self.assertTrue(existing.admin_disabled)


if __name__ == "__main__":
    unittest.main()
