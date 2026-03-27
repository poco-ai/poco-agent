import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.lifecycle.builtin_skills import BUILTIN_SKILLS, SkillBootstrapService


class BuiltinOfficeSkillsTests(unittest.TestCase):
    def test_office_skills_are_registered(self) -> None:
        registered_names = {definition.name for definition in BUILTIN_SKILLS}

        self.assertTrue(
            {
                "office-assistant",
                "docx",
                "xlsx",
                "pdf",
                "pptx",
            }.issubset(registered_names)
        )

    def test_registered_builtin_skills_have_markdown_assets(self) -> None:
        for definition in BUILTIN_SKILLS:
            with self.subTest(skill=definition.name):
                self.assertTrue(definition.asset_dir.is_dir())
                self.assertTrue((definition.asset_dir / "SKILL.md").is_file())
                bundle = SkillBootstrapService._build_bundle(definition)
                self.assertEqual(bundle.definition.name, definition.name)
                self.assertTrue(bundle.description)


if __name__ == "__main__":
    unittest.main()
