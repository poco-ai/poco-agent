from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from app.services.skill_config_service import SkillConfigService
from app.services.task_service import TaskService


class CapabilityResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = MagicMock()
        self.user_id = "user-1"

    @patch("app.services.task_service.SkillRepository.list_visible")
    @patch("app.services.task_service.UserSkillInstallRepository.list_by_user")
    def test_task_service_defaults_include_system_policy_skills(
        self,
        list_by_user: MagicMock,
        list_visible: MagicMock,
    ) -> None:
        service = TaskService()
        list_by_user.return_value = []
        list_visible.return_value = [
            SimpleNamespace(
                id=1,
                force_enabled=False,
                default_enabled=True,
                scope="system",
            ),
            SimpleNamespace(
                id=2,
                force_enabled=False,
                default_enabled=False,
                scope="system",
            ),
        ]

        result = service._build_user_skill_ids_defaults(self.db, self.user_id)

        self.assertEqual(result, [1])

    @patch("app.services.task_service.SkillRepository.list_visible")
    @patch("app.services.task_service.UserSkillInstallRepository.list_by_user")
    def test_task_service_toggles_can_disable_default_system_skills(
        self,
        list_by_user: MagicMock,
        list_visible: MagicMock,
    ) -> None:
        service = TaskService()
        list_by_user.return_value = []
        list_visible.return_value = [
            SimpleNamespace(
                id=1,
                force_enabled=False,
                default_enabled=True,
                scope="system",
            ),
        ]

        result = service._build_user_skill_ids_with_toggles(
            self.db,
            self.user_id,
            {"1": False},
        )

        self.assertEqual(result, [])

    @patch("app.services.skill_config_service.SkillRepository.list_visible")
    @patch("app.services.skill_config_service.SkillRepository.get_by_id")
    @patch("app.services.skill_config_service.UserSkillInstallRepository.list_by_user")
    def test_skill_config_service_uses_requested_ids_when_overrides_present(
        self,
        list_by_user: MagicMock,
        get_by_id: MagicMock,
        list_visible: MagicMock,
    ) -> None:
        service = SkillConfigService()
        list_by_user.return_value = []
        requested = SimpleNamespace(
            id=1, name="requested", scope="user", entry={"k": 1}
        )
        system_default = SimpleNamespace(
            id=2,
            name="system-default",
            scope="system",
            entry={"k": 2},
            admin_disabled=False,
            force_enabled=False,
            default_enabled=True,
        )
        system_forced = SimpleNamespace(
            id=3,
            name="system-forced",
            scope="system",
            entry={"k": 3},
            admin_disabled=False,
            force_enabled=True,
            default_enabled=False,
        )
        skill_by_id = {
            1: requested,
            2: system_default,
            3: system_forced,
        }
        get_by_id.side_effect = lambda _db, skill_id: skill_by_id.get(skill_id)
        list_visible.return_value = [system_default, system_forced]

        result = service.resolve_user_skill_files(
            db=self.db,
            user_id=self.user_id,
            skill_ids=[1],
            skill_overrides={},
        )

        self.assertEqual(
            result,
            {
                "requested": {"enabled": True, "entry": {"k": 1}},
                "system-forced": {"enabled": True, "entry": {"k": 3}},
            },
        )

    @patch("app.services.skill_config_service.SkillRepository.list_visible")
    @patch("app.services.skill_config_service.SkillRepository.get_by_id")
    @patch("app.services.skill_config_service.UserSkillInstallRepository.list_by_user")
    def test_skill_config_service_skips_admin_disabled_system_skills(
        self,
        list_by_user: MagicMock,
        get_by_id: MagicMock,
        list_visible: MagicMock,
    ) -> None:
        service = SkillConfigService()
        list_by_user.return_value = []
        disabled_system = SimpleNamespace(
            id=2,
            name="system-disabled",
            scope="system",
            entry={"k": 2},
            admin_disabled=True,
            force_enabled=False,
            default_enabled=True,
        )
        get_by_id.side_effect = lambda _db, skill_id: (
            disabled_system if skill_id == 2 else None
        )
        list_visible.return_value = []

        result = service.resolve_user_skill_files(
            db=self.db,
            user_id=self.user_id,
            skill_ids=[2],
            skill_overrides={"2": True},
        )

        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()
