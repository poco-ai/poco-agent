import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.core.errors.exceptions import AppException
from app.services.constants import SYSTEM_USER_ID
from app.services.skill_service import SkillService
from app.schemas.skill import SkillCreateRequest, SkillUpdateRequest


class SkillServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = MagicMock()
        self.service = SkillService()

    @patch("app.services.skill_service.SkillRepository.get_by_id")
    def test_delete_skill_rejects_builtin_system_skill(
        self,
        get_by_id: MagicMock,
    ) -> None:
        get_by_id.return_value = SimpleNamespace(
            id=1,
            name="builtin-skill",
            scope="system",
            owner_user_id="__system__",
            source={
                "kind": "system",
                "managed_by": "lifecycle",
            },
        )

        with self.assertRaises(AppException):
            self.service.delete_skill(self.db, user_id="__system__", skill_id=1)

    def test_create_skill_rejects_admin_disabled_for_user_scope(self) -> None:
        with self.assertRaises(AppException):
            self.service.create_skill(
                self.db,
                user_id="user-1",
                request=SkillCreateRequest(
                    name="user-skill",
                    description="demo",
                    scope="user",
                    entry={},
                    default_enabled=None,
                    force_enabled=None,
                    admin_disabled=True,
                ),
            )

    def test_create_skill_rejects_non_admin_system_scope(self) -> None:
        with self.assertRaises(AppException):
            self.service.create_skill(
                self.db,
                user_id="user-1",
                request=SkillCreateRequest(
                    name="system-skill",
                    description="demo",
                    scope="system",
                    entry={},
                    default_enabled=None,
                    force_enabled=None,
                    admin_disabled=False,
                ),
            )

    @patch("app.services.skill_service.SkillRepository.get_by_id")
    def test_get_skill_rejects_non_system_owned_system_scope(
        self,
        get_by_id: MagicMock,
    ) -> None:
        get_by_id.return_value = SimpleNamespace(
            id=1,
            name="system-like-skill",
            scope="system",
            owner_user_id="user-2",
            admin_disabled=False,
        )

        with self.assertRaises(AppException):
            self.service.get_skill(self.db, SYSTEM_USER_ID, 1)

    @patch("app.services.skill_service.SkillRepository.get_by_id")
    def test_update_skill_rejects_builtin_metadata_change(
        self,
        get_by_id: MagicMock,
    ) -> None:
        get_by_id.return_value = SimpleNamespace(
            id=1,
            name="builtin-skill",
            description="original",
            scope="system",
            owner_user_id="__system__",
            source={
                "kind": "system",
                "managed_by": "lifecycle",
            },
            entry={"s3_key": "builtin/skills/builtin-skill/", "is_prefix": True},
            default_enabled=False,
            force_enabled=False,
            admin_disabled=False,
        )

        with self.assertRaises(AppException):
            self.service.update_skill(
                self.db,
                user_id="__system__",
                skill_id=1,
                request=SkillUpdateRequest(
                    name="builtin-skill",
                    description="updated",
                    entry=None,
                    scope=None,
                    default_enabled=None,
                    force_enabled=None,
                    admin_disabled=None,
                ),
            )


if __name__ == "__main__":
    unittest.main()
