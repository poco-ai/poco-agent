import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.slash_command_config_service import SlashCommandConfigService


class SlashCommandConfigServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = MagicMock()
        self.user_id = "user-1"
        self.service = SlashCommandConfigService()

    @patch("app.services.slash_command_config_service.SkillRepository.list_visible")
    def test_explicit_skill_names_skip_hidden_system_skills(
        self,
        list_visible: MagicMock,
    ) -> None:
        list_visible.return_value = [
            SimpleNamespace(name="visible-skill"),
        ]

        result = self.service._resolve_skill_aliases(
            self.db,
            user_id=self.user_id,
            skill_names=["visible-skill", "hidden-skill"],
        )

        self.assertEqual(result, [("visible-skill", None)])


if __name__ == "__main__":
    unittest.main()
