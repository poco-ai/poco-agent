import unittest
from unittest.mock import MagicMock, patch

from app.models.env_var import UserEnvVar
from app.services.constants import SYSTEM_USER_ID
from app.services.env_var_service import EnvVarService


class RuntimeEnvPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = EnvVarService()
        self.db = MagicMock()

    def _make_env_var(
        self,
        *,
        user_id: str,
        scope: str,
        key: str,
        value: str,
        expose_to_runtime: bool = False,
        runtime_visibility: str = "none",
    ) -> UserEnvVar:
        return UserEnvVar(
            id=1,
            user_id=user_id,
            scope=scope,
            key=key,
            value_ciphertext=value,
            description=None,
            expose_to_runtime=expose_to_runtime,
            runtime_visibility=runtime_visibility,
        )

    @patch("app.services.env_var_service.decrypt_value")
    @patch(
        "app.services.env_var_service.RuntimeEnvPolicyService.get_policy",
        return_value=type(
            "Policy",
            (),
            {
                "mode": "opt_in",
                "allowlist_patterns": [],
                "denylist_patterns": [],
            },
        )(),
    )
    @patch("app.services.env_var_service.EnvVarRepository.list_by_user_and_scope")
    def test_runtime_env_map_includes_user_opt_in_var(
        self,
        list_by_scope: MagicMock,
        _: MagicMock,
        decrypt_value: MagicMock,
    ) -> None:
        decrypt_value.side_effect = lambda token, secret: token
        list_by_scope.side_effect = [
            [],
            [
                self._make_env_var(
                    user_id="user-1",
                    scope="user",
                    key="OPENAI_COMPATIBLE_API_KEY",
                    value="user-secret",
                    expose_to_runtime=True,
                )
            ],
        ]

        result = self.service.get_runtime_env_map(self.db, "user-1")

        self.assertEqual(result["OPENAI_COMPATIBLE_API_KEY"], "user-secret")

    @patch("app.services.env_var_service.decrypt_value")
    @patch(
        "app.services.env_var_service.RuntimeEnvPolicyService.get_policy",
        return_value=type(
            "Policy",
            (),
            {
                "mode": "opt_in",
                "allowlist_patterns": [],
                "denylist_patterns": [],
            },
        )(),
    )
    @patch("app.services.env_var_service.EnvVarRepository.list_by_user_and_scope")
    def test_runtime_env_map_excludes_non_opt_in_user_var(
        self,
        list_by_scope: MagicMock,
        _: MagicMock,
        decrypt_value: MagicMock,
    ) -> None:
        decrypt_value.side_effect = lambda token, secret: token
        list_by_scope.side_effect = [
            [],
            [
                self._make_env_var(
                    user_id="user-1",
                    scope="user",
                    key="OPENAI_COMPATIBLE_API_KEY",
                    value="user-secret",
                    expose_to_runtime=False,
                )
            ],
        ]

        result = self.service.get_runtime_env_map(self.db, "user-1")

        self.assertEqual(result, {})

    @patch("app.services.env_var_service.decrypt_value")
    @patch(
        "app.services.env_var_service.RuntimeEnvPolicyService.get_policy",
        return_value=type(
            "Policy",
            (),
            {
                "mode": "opt_in",
                "allowlist_patterns": [],
                "denylist_patterns": [],
            },
        )(),
    )
    @patch("app.services.env_var_service.EnvVarRepository.list_by_user_and_scope")
    def test_runtime_env_map_respects_admins_only_system_var(
        self,
        list_by_scope: MagicMock,
        _: MagicMock,
        decrypt_value: MagicMock,
    ) -> None:
        decrypt_value.side_effect = lambda token, secret: token
        list_by_scope.side_effect = [
            [
                self._make_env_var(
                    user_id=SYSTEM_USER_ID,
                    scope="system",
                    key="OPENAI_COMPATIBLE_MODEL",
                    value="gpt-4.1-mini",
                    runtime_visibility="admins_only",
                )
            ],
            [],
            [
                self._make_env_var(
                    user_id=SYSTEM_USER_ID,
                    scope="system",
                    key="OPENAI_COMPATIBLE_MODEL",
                    value="gpt-4.1-mini",
                    runtime_visibility="admins_only",
                )
            ],
            [],
        ]

        user_result = self.service.get_runtime_env_map(
            self.db, "user-1", requester_is_admin=False
        )
        admin_result = self.service.get_runtime_env_map(
            self.db, "user-1", requester_is_admin=True
        )

        self.assertEqual(user_result, {})
        self.assertEqual(admin_result["OPENAI_COMPATIBLE_MODEL"], "gpt-4.1-mini")

    @patch("app.services.env_var_service.decrypt_value")
    @patch(
        "app.services.env_var_service.RuntimeEnvPolicyService.get_policy",
        return_value=type(
            "Policy",
            (),
            {
                "mode": "opt_in",
                "allowlist_patterns": ["OPENAI_COMPATIBLE_*"],
                "denylist_patterns": ["OPENAI_COMPATIBLE_MODEL"],
            },
        )(),
    )
    @patch("app.services.env_var_service.EnvVarRepository.list_by_user_and_scope")
    def test_runtime_env_map_applies_allow_and_deny_patterns(
        self,
        list_by_scope: MagicMock,
        _: MagicMock,
        decrypt_value: MagicMock,
    ) -> None:
        decrypt_value.side_effect = lambda token, secret: token
        list_by_scope.side_effect = [
            [],
            [
                self._make_env_var(
                    user_id="user-1",
                    scope="user",
                    key="OPENAI_COMPATIBLE_API_KEY",
                    value="key",
                    expose_to_runtime=True,
                ),
                self._make_env_var(
                    user_id="user-1",
                    scope="user",
                    key="OPENAI_COMPATIBLE_MODEL",
                    value="model",
                    expose_to_runtime=True,
                ),
            ],
        ]

        result = self.service.get_runtime_env_map(self.db, "user-1")

        self.assertIn("OPENAI_COMPATIBLE_API_KEY", result)
        self.assertNotIn("OPENAI_COMPATIBLE_MODEL", result)

    @patch("app.services.env_var_service.decrypt_value")
    @patch(
        "app.services.env_var_service.RuntimeEnvPolicyService.get_policy",
        return_value=type(
            "Policy",
            (),
            {
                "mode": "opt_in",
                "allowlist_patterns": [],
                "denylist_patterns": [],
            },
        )(),
    )
    @patch("app.services.env_var_service.EnvVarRepository.list_by_user_and_scope")
    def test_runtime_env_map_blocks_protected_keys(
        self,
        list_by_scope: MagicMock,
        _: MagicMock,
        decrypt_value: MagicMock,
    ) -> None:
        decrypt_value.side_effect = lambda token, secret: token
        list_by_scope.side_effect = [
            [],
            [
                self._make_env_var(
                    user_id="user-1",
                    scope="user",
                    key="PATH",
                    value="/tmp/bin",
                    expose_to_runtime=True,
                )
            ],
        ]

        result = self.service.get_runtime_env_map(self.db, "user-1")

        self.assertEqual(result, {})

    @patch("app.services.env_var_service.decrypt_value")
    @patch(
        "app.services.env_var_service.RuntimeEnvPolicyService.get_policy",
        return_value=type(
            "Policy",
            (),
            {
                "mode": "opt_in",
                "allowlist_patterns": [],
                "denylist_patterns": [],
            },
        )(),
    )
    @patch("app.services.env_var_service.EnvVarRepository.list_by_user_and_scope")
    def test_runtime_env_map_user_entry_can_shadow_system_entry(
        self,
        list_by_scope: MagicMock,
        _: MagicMock,
        decrypt_value: MagicMock,
    ) -> None:
        decrypt_value.side_effect = lambda token, secret: token
        list_by_scope.side_effect = [
            [
                self._make_env_var(
                    user_id=SYSTEM_USER_ID,
                    scope="system",
                    key="OPENAI_COMPATIBLE_API_KEY",
                    value="system-secret",
                    runtime_visibility="all_users",
                )
            ],
            [
                self._make_env_var(
                    user_id="user-1",
                    scope="user",
                    key="OPENAI_COMPATIBLE_API_KEY",
                    value="user-secret",
                    expose_to_runtime=False,
                )
            ],
        ]

        result = self.service.get_runtime_env_map(self.db, "user-1")

        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()
