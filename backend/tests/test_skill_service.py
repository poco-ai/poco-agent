import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.schemas.skill import SkillCreateRequest, SkillUpdateRequest
from app.services.skill_service import SkillService, _validate_skill_name


class TestValidateSkillName(unittest.TestCase):
    """Test _validate_skill_name helper function."""

    def test_valid_name(self) -> None:
        result = _validate_skill_name("my-skill")
        self.assertEqual(result, "my-skill")

    def test_valid_name_with_dots(self) -> None:
        result = _validate_skill_name("my.skill.v1")
        self.assertEqual(result, "my.skill.v1")

    def test_valid_name_with_underscores(self) -> None:
        result = _validate_skill_name("my_skill_123")
        self.assertEqual(result, "my_skill_123")

    def test_valid_name_with_alphanumeric(self) -> None:
        result = _validate_skill_name("skill123")
        self.assertEqual(result, "skill123")

    def test_invalid_name_with_spaces(self) -> None:
        with self.assertRaises(AppException) as ctx:
            _validate_skill_name("my skill")
        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    def test_invalid_name_with_special_chars(self) -> None:
        with self.assertRaises(AppException) as ctx:
            _validate_skill_name("my@skill!")
        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    def test_invalid_name_empty(self) -> None:
        with self.assertRaises(AppException) as ctx:
            _validate_skill_name("")
        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    def test_invalid_name_whitespace_only(self) -> None:
        with self.assertRaises(AppException) as ctx:
            _validate_skill_name("   ")
        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    def test_invalid_name_single_dot(self) -> None:
        with self.assertRaises(AppException) as ctx:
            _validate_skill_name(".")
        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    def test_invalid_name_double_dot(self) -> None:
        with self.assertRaises(AppException) as ctx:
            _validate_skill_name("..")
        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    def test_name_is_trimmed(self) -> None:
        result = _validate_skill_name("  my-skill  ")
        self.assertEqual(result, "my-skill")

    def test_invalid_name_none(self) -> None:
        with self.assertRaises(AppException) as ctx:
            _validate_skill_name(None)  # type: ignore
        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)


class TestSkillServiceIsPrefixEntry(unittest.TestCase):
    """Test _is_prefix_entry static method."""

    def test_bool_true(self) -> None:
        entry = {"is_prefix": True}
        result = SkillService._is_prefix_entry(entry, "some/key")
        self.assertTrue(result)

    def test_bool_false(self) -> None:
        entry = {"is_prefix": False}
        result = SkillService._is_prefix_entry(entry, "some/key")
        self.assertFalse(result)

    def test_string_true(self) -> None:
        entry = {"is_prefix": "true"}
        result = SkillService._is_prefix_entry(entry, "some/key")
        self.assertTrue(result)

    def test_string_1(self) -> None:
        entry = {"is_prefix": "1"}
        result = SkillService._is_prefix_entry(entry, "some/key")
        self.assertTrue(result)

    def test_string_yes(self) -> None:
        entry = {"is_prefix": "yes"}
        result = SkillService._is_prefix_entry(entry, "some/key")
        self.assertTrue(result)

    def test_string_on(self) -> None:
        entry = {"is_prefix": "on"}
        result = SkillService._is_prefix_entry(entry, "some/key")
        self.assertTrue(result)

    def test_string_false(self) -> None:
        entry = {"is_prefix": "false"}
        result = SkillService._is_prefix_entry(entry, "some/key")
        self.assertFalse(result)

    def test_string_0(self) -> None:
        entry = {"is_prefix": "0"}
        result = SkillService._is_prefix_entry(entry, "some/key")
        self.assertFalse(result)

    def test_no_is_prefix_key_with_trailing_slash(self) -> None:
        entry = {}
        result = SkillService._is_prefix_entry(entry, "skills/user/")
        self.assertTrue(result)

    def test_no_is_prefix_key_without_trailing_slash(self) -> None:
        entry = {}
        result = SkillService._is_prefix_entry(entry, "skills/user/file.md")
        self.assertFalse(result)


class TestSkillServiceListSkills(unittest.TestCase):
    """Test list_skills method."""

    def setUp(self) -> None:
        self.db = MagicMock()
        self.service = SkillService()
        self.user_id = "user-123"

    def _make_skill(self, **kwargs) -> MagicMock:
        skill = MagicMock()
        skill.id = kwargs.get("id", 1)
        skill.name = kwargs.get("name", "test-skill")
        skill.description = kwargs.get("description", "Test skill")
        skill.entry = kwargs.get("entry", {})
        skill.scope = kwargs.get("scope", "user")
        skill.owner_user_id = kwargs.get("owner_user_id", self.user_id)
        skill.created_at = kwargs.get("created_at", datetime.now())
        skill.updated_at = kwargs.get("updated_at", datetime.now())
        skill.source = kwargs.get("source", {"kind": "manual"})
        return skill

    @patch("app.services.skill_service.SkillRepository")
    @patch("app.services.skill_service.infer_capability_source")
    def test_list_skills_empty(
        self, mock_infer: MagicMock, mock_repo: MagicMock
    ) -> None:
        mock_repo.list_visible.return_value = []
        mock_infer.return_value = {"kind": "manual"}

        result = self.service.list_skills(self.db, self.user_id)

        self.assertEqual(result, [])
        mock_repo.list_visible.assert_called_once_with(self.db, user_id=self.user_id)

    @patch("app.services.skill_service.SkillRepository")
    @patch("app.services.skill_service.infer_capability_source")
    def test_list_skills_with_skills(
        self, mock_infer: MagicMock, mock_repo: MagicMock
    ) -> None:
        skill = self._make_skill()
        mock_repo.list_visible.return_value = [skill]
        mock_infer.return_value = {"kind": "manual"}

        result = self.service.list_skills(self.db, self.user_id)

        self.assertEqual(len(result), 1)
        mock_repo.list_visible.assert_called_once()


class TestSkillServiceGetSkill(unittest.TestCase):
    """Test get_skill method."""

    def setUp(self) -> None:
        self.db = MagicMock()
        self.service = SkillService()
        self.user_id = "user-123"
        self.skill_id = 1

    def _make_skill(self, **kwargs) -> MagicMock:
        skill = MagicMock()
        skill.id = kwargs.get("id", self.skill_id)
        skill.name = kwargs.get("name", "test-skill")
        skill.description = kwargs.get("description", "Test skill")
        skill.entry = kwargs.get("entry", {})
        skill.scope = kwargs.get("scope", "user")
        skill.owner_user_id = kwargs.get("owner_user_id", self.user_id)
        skill.created_at = kwargs.get("created_at", datetime.now())
        skill.updated_at = kwargs.get("updated_at", datetime.now())
        skill.source = kwargs.get("source", {"kind": "manual"})
        return skill

    @patch("app.services.skill_service.SkillRepository")
    @patch("app.services.skill_service.infer_capability_source")
    def test_get_skill_found(self, mock_infer: MagicMock, mock_repo: MagicMock) -> None:
        skill = self._make_skill()
        mock_repo.get_by_id.return_value = skill
        mock_infer.return_value = {"kind": "manual"}

        self.service.get_skill(self.db, self.user_id, self.skill_id)

        mock_repo.get_by_id.assert_called_once_with(self.db, self.skill_id)

    @patch("app.services.skill_service.SkillRepository")
    def test_get_skill_not_found(self, mock_repo: MagicMock) -> None:
        mock_repo.get_by_id.return_value = None

        with self.assertRaises(AppException) as ctx:
            self.service.get_skill(self.db, self.user_id, self.skill_id)

        self.assertEqual(ctx.exception.error_code, ErrorCode.SKILL_NOT_FOUND)

    @patch("app.services.skill_service.SkillRepository")
    def test_get_skill_wrong_owner(self, mock_repo: MagicMock) -> None:
        skill = self._make_skill(owner_user_id="other-user", scope="user")
        mock_repo.get_by_id.return_value = skill

        with self.assertRaises(AppException) as ctx:
            self.service.get_skill(self.db, self.user_id, self.skill_id)

        self.assertEqual(ctx.exception.error_code, ErrorCode.SKILL_NOT_FOUND)

    @patch("app.services.skill_service.SkillRepository")
    @patch("app.services.skill_service.infer_capability_source")
    def test_get_skill_system_skill(
        self, mock_infer: MagicMock, mock_repo: MagicMock
    ) -> None:
        skill = self._make_skill(scope="system", owner_user_id="admin")
        mock_repo.get_by_id.return_value = skill
        mock_infer.return_value = {"kind": "system"}

        self.service.get_skill(self.db, self.user_id, self.skill_id)

        # System skills are visible to all users
        mock_repo.get_by_id.assert_called_once()


class TestSkillServiceListSkillFiles(unittest.TestCase):
    """Test list_skill_files method."""

    def setUp(self) -> None:
        self.db = MagicMock()
        self.storage_service = MagicMock()
        self.service = SkillService(storage_service=self.storage_service)
        self.user_id = "user-123"
        self.skill_id = 1

    def _make_skill(self, **kwargs) -> MagicMock:
        skill = MagicMock()
        skill.id = kwargs.get("id", self.skill_id)
        skill.name = kwargs.get("name", "test-skill")
        skill.description = kwargs.get("description", "Test skill")
        skill.entry = kwargs.get("entry", {})
        skill.scope = kwargs.get("scope", "user")
        skill.owner_user_id = kwargs.get("owner_user_id", self.user_id)
        skill.created_at = kwargs.get("created_at", datetime.now())
        skill.updated_at = kwargs.get("updated_at", datetime.now())
        skill.source = kwargs.get("source", {"kind": "manual"})
        return skill

    @patch("app.services.skill_service.SkillRepository")
    def test_list_skill_files_no_entry(self, mock_repo: MagicMock) -> None:
        skill = self._make_skill(entry=None)
        mock_repo.get_by_id.return_value = skill

        result = self.service.list_skill_files(self.db, self.user_id, self.skill_id)

        self.assertEqual(result, [])

    @patch("app.services.skill_service.SkillRepository")
    def test_list_skill_files_empty_entry(self, mock_repo: MagicMock) -> None:
        skill = self._make_skill(entry={})
        mock_repo.get_by_id.return_value = skill

        result = self.service.list_skill_files(self.db, self.user_id, self.skill_id)

        self.assertEqual(result, [])

    @patch("app.services.skill_service.SkillRepository")
    def test_list_skill_files_no_s3_key(self, mock_repo: MagicMock) -> None:
        skill = self._make_skill(entry={"other": "value"})
        mock_repo.get_by_id.return_value = skill

        result = self.service.list_skill_files(self.db, self.user_id, self.skill_id)

        self.assertEqual(result, [])

    @patch("app.services.skill_service.SkillRepository")
    def test_list_skill_files_empty_s3_key(self, mock_repo: MagicMock) -> None:
        skill = self._make_skill(entry={"s3_key": ""})
        mock_repo.get_by_id.return_value = skill

        result = self.service.list_skill_files(self.db, self.user_id, self.skill_id)

        self.assertEqual(result, [])

    @patch("app.services.skill_service.SkillRepository")
    def test_list_skill_files_skill_not_found(self, mock_repo: MagicMock) -> None:
        mock_repo.get_by_id.return_value = None

        with self.assertRaises(AppException) as ctx:
            self.service.list_skill_files(self.db, self.user_id, self.skill_id)

        self.assertEqual(ctx.exception.error_code, ErrorCode.SKILL_NOT_FOUND)


class TestSkillServiceCreateSkill(unittest.TestCase):
    """Test create_skill method."""

    def setUp(self) -> None:
        self.db = MagicMock()
        self.service = SkillService()
        self.user_id = "user-123"

    @patch("app.services.skill_service.SkillRepository")
    @patch("app.services.skill_service.infer_capability_source")
    def test_create_skill_success(
        self, mock_infer: MagicMock, mock_repo: MagicMock
    ) -> None:
        mock_repo.get_by_name.return_value = None
        mock_infer.return_value = {"kind": "manual"}

        request = SkillCreateRequest(
            name="new-skill",
            entry={"key": "value"},
            description="New skill",
            scope="user",
        )

        # Mock db.refresh to set attributes
        def mock_refresh(obj):
            obj.id = 1
            obj.created_at = datetime.now()
            obj.updated_at = datetime.now()

        self.db.refresh.side_effect = mock_refresh

        result = self.service.create_skill(self.db, self.user_id, request)

        mock_repo.get_by_name.assert_called_once()
        mock_repo.create.assert_called_once()
        self.db.commit.assert_called_once()
        self.assertEqual(result.name, "new-skill")
        self.assertEqual(result.manifest_version, "v1")
        self.assertEqual(result.lifecycle_state, "active")
        self.assertEqual(result.manifest["name"], "new-skill")
        self.assertEqual(result.manifest["entry"], {"key": "value"})

    @patch("app.services.skill_service.SkillRepository")
    def test_create_skill_already_exists(self, mock_repo: MagicMock) -> None:
        existing = MagicMock()
        mock_repo.get_by_name.return_value = existing

        request = SkillCreateRequest(
            name="existing-skill",
            entry={},
        )

        with self.assertRaises(AppException) as ctx:
            self.service.create_skill(self.db, self.user_id, request)

        self.assertEqual(ctx.exception.error_code, ErrorCode.SKILL_ALREADY_EXISTS)

    @patch("app.services.skill_service.SkillRepository")
    def test_create_skill_invalid_name(self, mock_repo: MagicMock) -> None:
        request = SkillCreateRequest(
            name="invalid name!",
            entry={},
        )

        with self.assertRaises(AppException) as ctx:
            self.service.create_skill(self.db, self.user_id, request)

        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    @patch("app.services.skill_service.SkillRepository")
    @patch("app.services.skill_service.infer_capability_source")
    def test_create_skill_default_scope(
        self, mock_infer: MagicMock, mock_repo: MagicMock
    ) -> None:
        mock_repo.get_by_name.return_value = None
        mock_infer.return_value = {"kind": "manual"}

        request = SkillCreateRequest(
            name="new-skill",
            entry={},
        )

        # Mock db.refresh to set attributes
        def mock_refresh(obj):
            obj.id = 1
            obj.created_at = datetime.now()
            obj.updated_at = datetime.now()

        self.db.refresh.side_effect = mock_refresh

        self.service.create_skill(self.db, self.user_id, request)

        # Check that scope defaults to "user"
        call_args = mock_repo.create.call_args
        skill = call_args[0][1]
        self.assertEqual(skill.scope, "user")
        self.assertEqual(skill.manifest_version, "v1")
        self.assertEqual(skill.lifecycle_state, "active")
        self.assertEqual(skill.manifest["name"], "new-skill")

    @patch("app.services.skill_service.SkillRepository")
    @patch("app.services.skill_service.infer_capability_source")
    def test_create_skill_strips_description(
        self, mock_infer: MagicMock, mock_repo: MagicMock
    ) -> None:
        mock_repo.get_by_name.return_value = None
        mock_infer.return_value = {"kind": "manual"}

        request = SkillCreateRequest(
            name="new-skill",
            entry={},
            description="  trimmed description  ",
        )

        # Mock db.refresh to set attributes
        def mock_refresh(obj):
            obj.id = 1
            obj.created_at = datetime.now()
            obj.updated_at = datetime.now()

        self.db.refresh.side_effect = mock_refresh

        self.service.create_skill(self.db, self.user_id, request)

        call_args = mock_repo.create.call_args
        skill = call_args[0][1]
        self.assertEqual(skill.description, "trimmed description")


class TestSkillServiceUpdateSkill(unittest.TestCase):
    """Test update_skill method."""

    def setUp(self) -> None:
        self.db = MagicMock()
        self.service = SkillService()
        self.user_id = "user-123"
        self.skill_id = 1

    def _make_skill(self, **kwargs) -> MagicMock:
        skill = MagicMock()
        skill.id = kwargs.get("id", self.skill_id)
        skill.name = kwargs.get("name", "test-skill")
        skill.description = kwargs.get("description", "Test skill")
        skill.entry = kwargs.get("entry", {})
        skill.scope = kwargs.get("scope", "user")
        skill.owner_user_id = kwargs.get("owner_user_id", self.user_id)
        skill.created_at = kwargs.get("created_at", datetime.now())
        skill.updated_at = kwargs.get("updated_at", datetime.now())
        skill.source = kwargs.get("source", {"kind": "manual"})
        return skill

    @patch("app.services.skill_service.SkillRepository")
    def test_update_skill_not_found(self, mock_repo: MagicMock) -> None:
        mock_repo.get_by_id.return_value = None

        request = SkillUpdateRequest(name="new-name")

        with self.assertRaises(AppException) as ctx:
            self.service.update_skill(self.db, self.user_id, self.skill_id, request)

        self.assertEqual(ctx.exception.error_code, ErrorCode.SKILL_NOT_FOUND)

    @patch("app.services.skill_service.SkillRepository")
    def test_update_skill_system_forbidden(self, mock_repo: MagicMock) -> None:
        skill = self._make_skill(scope="system")
        mock_repo.get_by_id.return_value = skill

        request = SkillUpdateRequest(name="new-name")

        with self.assertRaises(AppException) as ctx:
            self.service.update_skill(self.db, self.user_id, self.skill_id, request)

        self.assertEqual(ctx.exception.error_code, ErrorCode.SKILL_MODIFY_FORBIDDEN)

    @patch("app.services.skill_service.SkillRepository")
    def test_update_skill_wrong_owner(self, mock_repo: MagicMock) -> None:
        skill = self._make_skill(owner_user_id="other-user")
        mock_repo.get_by_id.return_value = skill

        request = SkillUpdateRequest(name="new-name")

        with self.assertRaises(AppException) as ctx:
            self.service.update_skill(self.db, self.user_id, self.skill_id, request)

        self.assertEqual(ctx.exception.error_code, ErrorCode.FORBIDDEN)

    @patch("app.services.skill_service.SkillRepository")
    @patch("app.services.skill_service.infer_capability_source")
    def test_update_skill_name_success(
        self, mock_infer: MagicMock, mock_repo: MagicMock
    ) -> None:
        skill = self._make_skill()
        mock_repo.get_by_id.return_value = skill
        mock_repo.get_by_name.return_value = None
        mock_infer.return_value = {"kind": "manual"}

        request = SkillUpdateRequest(name="new-name")

        self.service.update_skill(self.db, self.user_id, self.skill_id, request)

        mock_repo.get_by_name.assert_called_once()
        self.db.commit.assert_called_once()

    @patch("app.services.skill_service.SkillRepository")
    def test_update_skill_name_already_exists(self, mock_repo: MagicMock) -> None:
        skill = self._make_skill()
        existing = MagicMock()
        mock_repo.get_by_id.return_value = skill
        mock_repo.get_by_name.return_value = existing

        request = SkillUpdateRequest(name="existing-name")

        with self.assertRaises(AppException) as ctx:
            self.service.update_skill(self.db, self.user_id, self.skill_id, request)

        self.assertEqual(ctx.exception.error_code, ErrorCode.SKILL_ALREADY_EXISTS)

    @patch("app.services.skill_service.SkillRepository")
    @patch("app.services.skill_service.infer_capability_source")
    def test_update_skill_description(
        self, mock_infer: MagicMock, mock_repo: MagicMock
    ) -> None:
        skill = self._make_skill()
        mock_repo.get_by_id.return_value = skill
        mock_infer.return_value = {"kind": "manual"}

        request = SkillUpdateRequest(description="New description")

        self.service.update_skill(self.db, self.user_id, self.skill_id, request)

        self.db.commit.assert_called_once()

    @patch("app.services.skill_service.SkillRepository")
    @patch("app.services.skill_service.infer_capability_source")
    def test_update_skill_entry(
        self, mock_infer: MagicMock, mock_repo: MagicMock
    ) -> None:
        skill = self._make_skill()
        mock_repo.get_by_id.return_value = skill
        mock_infer.return_value = {"kind": "manual"}

        request = SkillUpdateRequest(entry={"new": "entry"})

        self.service.update_skill(self.db, self.user_id, self.skill_id, request)

        self.db.commit.assert_called_once()

    @patch("app.services.skill_service.SkillRepository")
    @patch("app.services.skill_service.infer_capability_source")
    def test_update_skill_scope(
        self, mock_infer: MagicMock, mock_repo: MagicMock
    ) -> None:
        skill = self._make_skill()
        mock_repo.get_by_id.return_value = skill
        mock_infer.return_value = {"kind": "manual"}

        request = SkillUpdateRequest(scope="project")

        self.service.update_skill(self.db, self.user_id, self.skill_id, request)

        self.db.commit.assert_called_once()


class TestSkillServiceDeleteSkill(unittest.TestCase):
    """Test delete_skill method."""

    def setUp(self) -> None:
        self.db = MagicMock()
        self.service = SkillService()
        self.user_id = "user-123"
        self.skill_id = 1

    def _make_skill(self, **kwargs) -> MagicMock:
        skill = MagicMock()
        skill.id = kwargs.get("id", self.skill_id)
        skill.name = kwargs.get("name", "test-skill")
        skill.scope = kwargs.get("scope", "user")
        skill.owner_user_id = kwargs.get("owner_user_id", self.user_id)
        return skill

    @patch("app.services.skill_service.SkillRepository")
    def test_delete_skill_success(self, mock_repo: MagicMock) -> None:
        skill = self._make_skill()
        mock_repo.get_by_id.return_value = skill

        self.service.delete_skill(self.db, self.user_id, self.skill_id)

        mock_repo.delete.assert_called_once_with(self.db, skill)
        self.db.commit.assert_called_once()

    @patch("app.services.skill_service.SkillRepository")
    def test_delete_skill_not_found(self, mock_repo: MagicMock) -> None:
        mock_repo.get_by_id.return_value = None

        with self.assertRaises(AppException) as ctx:
            self.service.delete_skill(self.db, self.user_id, self.skill_id)

        self.assertEqual(ctx.exception.error_code, ErrorCode.SKILL_NOT_FOUND)

    @patch("app.services.skill_service.SkillRepository")
    def test_delete_skill_system_forbidden(self, mock_repo: MagicMock) -> None:
        skill = self._make_skill(scope="system")
        mock_repo.get_by_id.return_value = skill

        with self.assertRaises(AppException) as ctx:
            self.service.delete_skill(self.db, self.user_id, self.skill_id)

        self.assertEqual(ctx.exception.error_code, ErrorCode.SKILL_MODIFY_FORBIDDEN)

    @patch("app.services.skill_service.SkillRepository")
    def test_delete_skill_wrong_owner(self, mock_repo: MagicMock) -> None:
        skill = self._make_skill(owner_user_id="other-user")
        mock_repo.get_by_id.return_value = skill

        with self.assertRaises(AppException) as ctx:
            self.service.delete_skill(self.db, self.user_id, self.skill_id)

        self.assertEqual(ctx.exception.error_code, ErrorCode.FORBIDDEN)


class TestSkillServiceStorageService(unittest.TestCase):
    """Test _storage_service method."""

    def test_storage_service_injected(self) -> None:
        mock_storage = MagicMock()
        service = SkillService(storage_service=mock_storage)

        result = service._storage_service()

        self.assertEqual(result, mock_storage)

    def test_storage_service_lazy_init(self) -> None:
        service = SkillService(storage_service=None)

        with patch("app.services.skill_service.S3StorageService") as mock_storage_cls:
            mock_storage_cls.return_value = MagicMock()
            service._storage_service()

            mock_storage_cls.assert_called_once()

    def test_storage_service_cached(self) -> None:
        service = SkillService(storage_service=None)

        with patch("app.services.skill_service.S3StorageService") as mock_storage_cls:
            mock_instance = MagicMock()
            mock_storage_cls.return_value = mock_instance

            # Call twice
            result1 = service._storage_service()
            result2 = service._storage_service()

            # Should only create once
            mock_storage_cls.assert_called_once()
            self.assertEqual(result1, result2)


class TestSkillServiceToResponse(unittest.TestCase):
    """Test _to_response static method."""

    def test_to_response(self) -> None:
        skill = MagicMock()
        skill.id = 1
        skill.name = "test-skill"
        skill.description = "Test description"
        skill.entry = {"key": "value"}
        skill.scope = "user"
        skill.owner_user_id = "user-123"
        skill.created_at = datetime.now()
        skill.updated_at = datetime.now()
        skill.source = {"kind": "manual"}

        with patch("app.services.skill_service.infer_capability_source") as mock_infer:
            mock_infer.return_value = {"kind": "manual"}

            result = SkillService._to_response(skill)

            self.assertEqual(result.id, 1)
            self.assertEqual(result.name, "test-skill")
            self.assertEqual(result.description, "Test description")
            mock_infer.assert_called_once()


class TestSkillServiceBuildFileNodesFromPrefix(unittest.TestCase):
    """Test _build_file_nodes_from_prefix method."""

    def setUp(self) -> None:
        self.storage_service = MagicMock()
        self.service = SkillService(storage_service=self.storage_service)

    def test_empty_prefix(self) -> None:
        result = self.service._build_file_nodes_from_prefix("")
        self.assertEqual(result, [])

    def test_whitespace_prefix(self) -> None:
        result = self.service._build_file_nodes_from_prefix("   ")
        self.assertEqual(result, [])

    @patch("app.services.skill_service.build_workspace_file_nodes")
    @patch("app.services.skill_service.build_nodes_from_file_entries")
    def test_no_objects(
        self, mock_build_entries: MagicMock, mock_build_workspace: MagicMock
    ) -> None:
        self.storage_service.list_objects.return_value = []

        result = self.service._build_file_nodes_from_prefix("skills/user/skill")

        self.assertEqual(result, [])
        self.storage_service.list_objects.assert_called_once()

    @patch("app.services.skill_service.build_workspace_file_nodes")
    @patch("app.services.skill_service.build_nodes_from_file_entries")
    def test_with_objects(
        self, mock_build_entries: MagicMock, mock_build_workspace: MagicMock
    ) -> None:
        self.storage_service.list_objects.return_value = [
            "skills/user/skill/file1.md",
            "skills/user/skill/file2.py",
        ]
        self.storage_service.presign_get.return_value = "https://presigned.url"
        mock_build_entries.return_value = [{"path": "file1.md"}]
        mock_build_workspace.return_value = [MagicMock()]

        self.service._build_file_nodes_from_prefix("skills/user/skill")

        self.storage_service.list_objects.assert_called_once()
        self.assertEqual(self.storage_service.presign_get.call_count, 2)
        mock_build_entries.assert_called_once()
        mock_build_workspace.assert_called_once()

    @patch("app.services.skill_service.build_workspace_file_nodes")
    @patch("app.services.skill_service.build_nodes_from_file_entries")
    def test_skips_directories(
        self, mock_build_entries: MagicMock, mock_build_workspace: MagicMock
    ) -> None:
        self.storage_service.list_objects.return_value = [
            "skills/user/skill/subdir/",
            "skills/user/skill/file.md",
        ]
        self.storage_service.presign_get.return_value = "https://presigned.url"
        mock_build_entries.return_value = [{"path": "file.md"}]
        mock_build_workspace.return_value = [MagicMock()]

        self.service._build_file_nodes_from_prefix("skills/user/skill")

        # Only one file (not the directory)
        self.assertEqual(self.storage_service.presign_get.call_count, 1)


class TestSkillServiceBuildFileNodesFromObject(unittest.TestCase):
    """Test _build_file_nodes_from_object method."""

    def setUp(self) -> None:
        self.storage_service = MagicMock()
        self.service = SkillService(storage_service=self.storage_service)

    def test_object_not_exists(self) -> None:
        self.storage_service.exists.return_value = False

        result = self.service._build_file_nodes_from_object("skills/user/skill.md")

        self.assertEqual(result, [])
        self.storage_service.exists.assert_called_once()

    @patch("app.services.skill_service.build_workspace_file_nodes")
    @patch("app.services.skill_service.build_nodes_from_file_entries")
    def test_object_exists(
        self, mock_build_entries: MagicMock, mock_build_workspace: MagicMock
    ) -> None:
        self.storage_service.exists.return_value = True
        self.storage_service.presign_get.return_value = "https://presigned.url"
        mock_build_entries.return_value = [{"path": "skill.md"}]
        mock_build_workspace.return_value = [MagicMock()]

        self.service._build_file_nodes_from_object("skills/user/skill.md")

        self.storage_service.exists.assert_called_once()
        self.storage_service.presign_get.assert_called_once()
        mock_build_entries.assert_called_once()
        mock_build_workspace.assert_called_once()


class TestSkillServiceVersionSkillAssets(unittest.TestCase):
    """Test _version_skill_assets method."""

    def setUp(self) -> None:
        self.storage_service = MagicMock()
        self.service = SkillService(storage_service=self.storage_service)
        self.user_id = "user-123"

    def _make_skill(self, **kwargs) -> MagicMock:
        skill = MagicMock()
        skill.id = kwargs.get("id", 1)
        skill.name = kwargs.get("name", "test-skill")
        skill.description = kwargs.get("description", "Test skill")
        skill.entry = kwargs.get(
            "entry", {"s3_key": "skills/user/skill/", "is_prefix": True}
        )
        skill.scope = kwargs.get("scope", "user")
        skill.source = kwargs.get("source", {"kind": "manual"})
        return skill

    def test_system_skill_returns_none(self) -> None:
        skill = self._make_skill(scope="system")

        result = self.service._version_skill_assets(
            skill=skill,
            user_id=self.user_id,
            target_name="new-name",
            target_description="New desc",
        )

        self.assertIsNone(result)

    def test_no_entry_returns_none(self) -> None:
        skill = self._make_skill(entry=None)

        result = self.service._version_skill_assets(
            skill=skill,
            user_id=self.user_id,
            target_name="new-name",
            target_description="New desc",
        )

        self.assertIsNone(result)

    def test_no_s3_key_returns_none(self) -> None:
        skill = self._make_skill(entry={})

        result = self.service._version_skill_assets(
            skill=skill,
            user_id=self.user_id,
            target_name="new-name",
            target_description="New desc",
        )

        self.assertIsNone(result)

    def test_same_name_and_description_returns_none(self) -> None:
        skill = self._make_skill(name="test-skill", description="Test skill")

        result = self.service._version_skill_assets(
            skill=skill,
            user_id=self.user_id,
            target_name="test-skill",
            target_description="Test skill",
        )

        self.assertIsNone(result)

    def test_not_prefix_entry_returns_none(self) -> None:
        skill = self._make_skill(
            entry={"s3_key": "skills/user/skill.md", "is_prefix": False}
        )

        result = self.service._version_skill_assets(
            skill=skill,
            user_id=self.user_id,
            target_name="new-name",
            target_description="New desc",
        )

        self.assertIsNone(result)

    @patch("app.services.skill_service.uuid")
    def test_version_assets_success(self, mock_uuid: MagicMock) -> None:
        mock_uuid.uuid4.return_value = "test-uuid"
        skill = self._make_skill()
        self.storage_service.copy_prefix.return_value = 2
        self.storage_service.get_text.return_value = "---\nname: old-name\n---\nContent"
        self.storage_service.put_object = MagicMock()

        result = self.service._version_skill_assets(
            skill=skill,
            user_id=self.user_id,
            target_name="new-name",
            target_description="New desc",
        )

        self.assertIsNotNone(result)
        self.storage_service.copy_prefix.assert_called_once()
        self.storage_service.get_text.assert_called_once()
        self.storage_service.put_object.assert_called_once()

    def test_version_assets_no_files_copied(self) -> None:
        skill = self._make_skill()
        self.storage_service.copy_prefix.return_value = 0

        with self.assertRaises(AppException) as ctx:
            self.service._version_skill_assets(
                skill=skill,
                user_id=self.user_id,
                target_name="new-name",
                target_description="New desc",
            )

        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)


class TestSkillServiceListSkillFilesWithStorage(unittest.TestCase):
    """Test list_skill_files method with storage service."""

    def setUp(self) -> None:
        self.db = MagicMock()
        self.storage_service = MagicMock()
        self.service = SkillService(storage_service=self.storage_service)
        self.user_id = "user-123"
        self.skill_id = 1

    def _make_skill(self, **kwargs) -> MagicMock:
        skill = MagicMock()
        skill.id = kwargs.get("id", self.skill_id)
        skill.name = kwargs.get("name", "test-skill")
        skill.description = kwargs.get("description", "Test skill")
        skill.entry = kwargs.get("entry", {})
        skill.scope = kwargs.get("scope", "user")
        skill.owner_user_id = kwargs.get("owner_user_id", self.user_id)
        skill.created_at = kwargs.get("created_at", datetime.now())
        skill.updated_at = kwargs.get("updated_at", datetime.now())
        skill.source = kwargs.get("source", {"kind": "manual"})
        return skill

    @patch("app.services.skill_service.build_workspace_file_nodes")
    @patch("app.services.skill_service.build_nodes_from_file_entries")
    @patch("app.services.skill_service.SkillRepository")
    def test_list_skill_files_prefix_mode(
        self,
        mock_repo: MagicMock,
        mock_build_entries: MagicMock,
        mock_build_workspace: MagicMock,
    ) -> None:
        skill = self._make_skill(
            entry={"s3_key": "skills/user/skill/", "is_prefix": True}
        )
        mock_repo.get_by_id.return_value = skill
        self.storage_service.list_objects.return_value = ["skills/user/skill/file.md"]
        self.storage_service.presign_get.return_value = "https://url"
        mock_build_entries.return_value = [{"path": "file.md"}]
        mock_build_workspace.return_value = [MagicMock()]

        self.service.list_skill_files(self.db, self.user_id, self.skill_id)

        self.storage_service.list_objects.assert_called_once()
        mock_build_workspace.assert_called_once()

    @patch("app.services.skill_service.build_workspace_file_nodes")
    @patch("app.services.skill_service.build_nodes_from_file_entries")
    @patch("app.services.skill_service.SkillRepository")
    def test_list_skill_files_object_mode(
        self,
        mock_repo: MagicMock,
        mock_build_entries: MagicMock,
        mock_build_workspace: MagicMock,
    ) -> None:
        skill = self._make_skill(
            entry={"s3_key": "skills/user/skill.md", "is_prefix": False}
        )
        mock_repo.get_by_id.return_value = skill
        self.storage_service.exists.return_value = True
        self.storage_service.presign_get.return_value = "https://url"
        mock_build_entries.return_value = [{"path": "skill.md"}]
        mock_build_workspace.return_value = [MagicMock()]

        self.service.list_skill_files(self.db, self.user_id, self.skill_id)

        self.storage_service.exists.assert_called_once()
        mock_build_workspace.assert_called_once()


class TestSkillServiceEdgeCases(unittest.TestCase):
    """Test edge cases for missing coverage."""

    def setUp(self) -> None:
        self.db = MagicMock()
        self.storage_service = MagicMock()
        self.service = SkillService(storage_service=self.storage_service)
        self.user_id = "user-123"
        self.skill_id = 1

    def _make_skill(self, **kwargs) -> MagicMock:
        skill = MagicMock()
        skill.id = kwargs.get("id", self.skill_id)
        skill.name = kwargs.get("name", "test-skill")
        skill.description = kwargs.get("description", "Test skill")
        skill.entry = kwargs.get(
            "entry", {"s3_key": "skills/user/skill/", "is_prefix": True}
        )
        skill.scope = kwargs.get("scope", "user")
        skill.owner_user_id = kwargs.get("owner_user_id", self.user_id)
        skill.created_at = kwargs.get("created_at", datetime.now())
        skill.updated_at = kwargs.get("updated_at", datetime.now())
        skill.source = kwargs.get("source", {"kind": "manual"})
        return skill

    @patch("app.services.skill_service.build_workspace_file_nodes")
    @patch("app.services.skill_service.build_nodes_from_file_entries")
    @patch("app.services.skill_service.normalize_manifest_path")
    def test_build_file_nodes_from_prefix_skips_invalid_path(
        self,
        mock_normalize: MagicMock,
        mock_build_entries: MagicMock,
        mock_build_workspace: MagicMock,
    ) -> None:
        mock_normalize.side_effect = lambda p: None if p == "invalid" else p
        self.storage_service.list_objects.return_value = [
            "skills/user/skill/invalid",
            "skills/user/skill/valid.md",
        ]
        self.storage_service.presign_get.return_value = "https://url"
        mock_build_entries.return_value = [{"path": "valid.md"}]
        mock_build_workspace.return_value = [MagicMock()]

        self.service._build_file_nodes_from_prefix("skills/user/skill")

        # Only one presign_get call (for valid.md, not for invalid)
        self.assertEqual(self.storage_service.presign_get.call_count, 1)

    @patch("app.services.skill_service.normalize_manifest_path")
    def test_build_file_nodes_from_object_empty_normalized(
        self, mock_normalize: MagicMock
    ) -> None:
        mock_normalize.return_value = None
        self.storage_service.exists.return_value = True

        result = self.service._build_file_nodes_from_object("skills/user/skill.md")

        self.assertEqual(result, [])

    def test_version_assets_empty_source_prefix(self) -> None:
        skill = self._make_skill(entry={"s3_key": "/", "is_prefix": True})

        result = self.service._version_skill_assets(
            skill=skill,
            user_id=self.user_id,
            target_name="new-name",
            target_description="New desc",
        )

        self.assertIsNone(result)

    @patch("app.services.skill_service.infer_capability_source")
    @patch("app.services.skill_service.SkillRepository")
    def test_update_skill_with_versioned_entry(
        self, mock_repo: MagicMock, mock_infer: MagicMock
    ) -> None:
        skill = self._make_skill()
        mock_repo.get_by_id.return_value = skill
        mock_repo.get_by_name.return_value = None
        mock_infer.return_value = {"kind": "manual"}

        # Mock version_skill_assets to return a new entry
        with patch.object(
            self.service,
            "_version_skill_assets",
            return_value={"s3_key": "new/path/", "is_prefix": True},
        ):
            request = SkillUpdateRequest(name="new-name")

            def mock_refresh(obj):
                obj.id = 1
                obj.created_at = datetime.now()
                obj.updated_at = datetime.now()

            self.db.refresh.side_effect = mock_refresh

            self.service.update_skill(self.db, self.user_id, self.skill_id, request)

            self.assertEqual(skill.entry["s3_key"], "new/path/")

    @patch("app.services.skill_service.infer_capability_source")
    @patch("app.services.skill_service.SkillRepository")
    def test_update_skill_with_versioned_entry_none(
        self, mock_repo: MagicMock, mock_infer: MagicMock
    ) -> None:
        skill = self._make_skill()
        mock_repo.get_by_id.return_value = skill
        mock_repo.get_by_name.return_value = None
        mock_infer.return_value = {"kind": "manual"}

        # Mock version_skill_assets to return None
        with patch.object(self.service, "_version_skill_assets", return_value=None):
            request = SkillUpdateRequest(name="new-name")

            def mock_refresh(obj):
                obj.id = 1
                obj.created_at = datetime.now()
                obj.updated_at = datetime.now()

            self.db.refresh.side_effect = mock_refresh

            self.service.update_skill(self.db, self.user_id, self.skill_id, request)

            # Entry should remain unchanged
            self.assertEqual(skill.entry["s3_key"], "skills/user/skill/")


if __name__ == "__main__":
    unittest.main()
