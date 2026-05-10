import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.core.errors.exceptions import AppException
from app.schemas.user_skill_install import UserSkillInstallBulkUpdateRequest
from app.services.user_skill_install_service import UserSkillInstallService


class UserSkillInstallServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = MagicMock()
        self.user_id = "user-1"
        self.service = UserSkillInstallService()

    @patch("app.services.user_skill_install_service.SkillRepository.get_by_id")
    @patch(
        "app.services.user_skill_install_service.UserSkillInstallRepository.get_by_id"
    )
    def test_delete_install_rejects_hidden_system_skill(
        self,
        get_install_by_id: MagicMock,
        get_skill_by_id: MagicMock,
    ) -> None:
        get_install_by_id.return_value = SimpleNamespace(
            id=10,
            user_id=self.user_id,
            skill_id=20,
        )
        get_skill_by_id.return_value = SimpleNamespace(
            id=20,
            scope="system",
            owner_user_id="__system__",
            admin_disabled=True,
        )

        with self.assertRaises(AppException):
            self.service.delete_install(self.db, self.user_id, 10)

    @patch("app.services.user_skill_install_service.SkillRepository.list_by_ids")
    @patch("app.services.user_skill_install_service.SkillRepository.get_by_id")
    @patch(
        "app.services.user_skill_install_service.UserSkillInstallRepository.bulk_set_enabled"
    )
    @patch(
        "app.services.user_skill_install_service.UserSkillInstallRepository.list_by_user"
    )
    def test_bulk_update_installs_skips_hidden_system_skills(
        self,
        list_by_user: MagicMock,
        bulk_set_enabled: MagicMock,
        get_skill_by_id: MagicMock,
        list_skills_by_ids: MagicMock,
    ) -> None:
        visible_install = SimpleNamespace(id=1, skill_id=101)
        hidden_install = SimpleNamespace(id=2, skill_id=202)
        list_by_user.return_value = [visible_install, hidden_install]
        visible_skill = SimpleNamespace(
            id=101,
            scope="system",
            owner_user_id="__system__",
            admin_disabled=False,
            force_enabled=False,
        )
        hidden_skill = SimpleNamespace(
            id=202,
            scope="system",
            owner_user_id="__system__",
            admin_disabled=True,
            force_enabled=False,
        )
        list_skills_by_ids.return_value = [visible_skill, hidden_skill]
        get_skill_by_id.side_effect = lambda _db, skill_id: {
            101: visible_skill,
            202: hidden_skill,
        }.get(skill_id)
        bulk_set_enabled.return_value = 1

        result = self.service.bulk_update_installs(
            self.db,
            self.user_id,
            UserSkillInstallBulkUpdateRequest(enabled=True, install_ids=None),
        )

        self.assertEqual(result.updated_count, 1)
        bulk_set_enabled.assert_called_once_with(
            self.db,
            user_id=self.user_id,
            enabled=True,
            install_ids=[1],
        )


if __name__ == "__main__":
    unittest.main()
