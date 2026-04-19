import unittest
from unittest.mock import MagicMock, patch

from app.models.user import User
from app.services.auth_service import AuthService, ProviderProfile


class AuthServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = AuthService()
        self.db = MagicMock()

    def _build_profile(
        self,
        *,
        email: str | None,
        email_verified: bool,
        provider_user_id: str = "provider-user-1",
    ) -> ProviderProfile:
        return ProviderProfile(
            provider="github",
            provider_user_id=provider_user_id,
            email=email,
            email_verified=email_verified,
            display_name="Test User",
            avatar_url="https://example.com/avatar.png",
            profile_json={"login": "test-user"},
        )

    def _build_user(self, *, user_id: str, primary_email: str | None) -> User:
        return User(
            id=user_id,
            primary_email=primary_email,
            display_name=None,
            avatar_url=None,
            status="active",
        )

    def test_auth_config_lists_supported_providers_with_feishu_enabled(self) -> None:
        settings = MagicMock(
            auth_mode="oauth_required",
            google_client_id=None,
            google_client_secret=None,
            github_client_id=None,
            github_client_secret=None,
            feishu_oauth_client_id="cli_test",
            feishu_oauth_client_secret="secret_test",
        )

        with patch("app.services.auth_service.get_settings", return_value=settings):
            config = self.service.get_auth_config()

        self.assertEqual(config.configured_providers, ["feishu"])
        self.assertEqual(
            [(provider.name, provider.enabled) for provider in config.providers],
            [
                ("google", False),
                ("github", False),
                ("feishu", True),
            ],
        )

    def test_configured_providers_include_feishu_when_credentials_exist(self) -> None:
        settings = MagicMock(
            google_client_id=None,
            google_client_secret=None,
            github_client_id=None,
            github_client_secret=None,
            feishu_oauth_client_id="cli_test",
            feishu_oauth_client_secret="secret_test",
        )

        with patch("app.services.auth_service.get_settings", return_value=settings):
            self.assertEqual(self.service.get_configured_providers(), ["feishu"])

    def test_configured_providers_ignore_blank_credentials(self) -> None:
        settings = MagicMock(
            google_client_id="   ",
            google_client_secret="secret",
            github_client_id="client",
            github_client_secret="   ",
            feishu_oauth_client_id="  ",
            feishu_oauth_client_secret="  ",
        )

        with patch("app.services.auth_service.get_settings", return_value=settings):
            self.assertEqual(self.service.get_configured_providers(), [])

    def test_extract_feishu_access_token_returns_none_when_missing(self) -> None:
        self.assertIsNone(self.service._extract_feishu_access_token({"code": 0}))

    def test_extract_feishu_access_token_accepts_supported_shapes(self) -> None:
        self.assertEqual(
            self.service._extract_feishu_access_token(
                {"access_token": " top-level-token "}
            ),
            "top-level-token",
        )
        self.assertEqual(
            self.service._extract_feishu_access_token(
                {"data": {"access_token": "data-token"}}
            ),
            "data-token",
        )
        self.assertEqual(
            self.service._extract_feishu_access_token(
                {"data": {"user_access_token": "user-token"}}
            ),
            "user-token",
        )

    def test_extract_feishu_user_data_accepts_nested_data(self) -> None:
        payload = {"code": 0, "data": {"union_id": "union-1"}}

        self.assertEqual(
            self.service._extract_feishu_user_data(payload),
            {"union_id": "union-1"},
        )

    def test_extract_feishu_user_data_accepts_flat_payload(self) -> None:
        payload = {"union_id": "union-1"}

        self.assertEqual(self.service._extract_feishu_user_data(payload), payload)

    def test_start_feishu_login_builds_authorize_url_without_scope(self) -> None:
        settings = MagicMock(
            frontend_public_url="http://localhost:3000",
            frontend_default_language="zh",
            feishu_oauth_client_id="cli_test",
            feishu_oauth_client_secret="secret_test",
            feishu_oauth_region="cn",
            feishu_oauth_scope="",
            feishu_oauth_authorize_url=None,
            feishu_oauth_token_url=None,
            feishu_oauth_userinfo_url=None,
        )
        request = MagicMock()
        request.session = {}

        with patch("app.services.auth_service.get_settings", return_value=settings):
            response = self.service._start_feishu_login(request, "/zh/home")

        self.assertEqual(response.status_code, 302)
        location = response.headers["location"]
        self.assertIn(
            "https://accounts.feishu.cn/open-apis/authen/v1/authorize?", location
        )
        self.assertIn("client_id=cli_test", location)
        self.assertIn("response_type=code", location)
        self.assertIn(
            "redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Fapi%2Fv1%2Fauth%2Ffeishu%2Fcallback",
            location,
        )
        self.assertIn("state=", location)
        self.assertNotIn("scope=", location)
        self.assertEqual(
            request.session[self.service.oauth_session_key]["provider"], "feishu"
        )
        self.assertEqual(
            request.session[self.service.oauth_session_key]["next"], "/zh/home"
        )
        self.assertTrue(request.session[self.service.oauth_session_key]["state"])

    def test_start_feishu_login_appends_scope_when_configured(self) -> None:
        settings = MagicMock(
            frontend_public_url="http://localhost:3000",
            frontend_default_language="zh",
            feishu_oauth_client_id="cli_test",
            feishu_oauth_client_secret="secret_test",
            feishu_oauth_region="global",
            feishu_oauth_scope="contact:user.email:readonly",
            feishu_oauth_authorize_url=None,
            feishu_oauth_token_url=None,
            feishu_oauth_userinfo_url=None,
        )
        request = MagicMock()
        request.session = {}

        with patch("app.services.auth_service.get_settings", return_value=settings):
            response = self.service._start_feishu_login(request, "/zh/home")

        location = response.headers["location"]
        self.assertIn(
            "https://accounts.larksuite.com/open-apis/authen/v1/authorize?", location
        )
        self.assertIn("scope=contact%3Auser.email%3Areadonly", location)

    def test_upsert_user_keeps_primary_email_unset_for_unverified_identity(
        self,
    ) -> None:
        profile = self._build_profile(
            email="User@example.com",
            email_verified=False,
        )

        with (
            patch(
                "app.services.auth_service.AuthIdentityRepository.get_by_provider_user_id",
                return_value=None,
            ),
            patch(
                "app.services.auth_service.UserRepository.get_by_email"
            ) as get_by_email,
            patch("app.services.auth_service.UserRepository.create") as create_user,
            patch(
                "app.services.auth_service.AuthIdentityRepository.create"
            ) as create_identity,
        ):
            create_user.side_effect = (
                lambda _db, *, user_id, primary_email, display_name, avatar_url, status="active": (
                    self._build_user(
                        user_id=user_id,
                        primary_email=primary_email,
                    )
                )
            )

            user = self.service._upsert_user(self.db, profile)

        get_by_email.assert_not_called()
        self.assertIsNone(create_user.call_args.kwargs["primary_email"])
        self.assertIsNone(user.primary_email)
        create_identity.assert_called_once_with(
            self.db,
            user_id=user.id,
            provider="github",
            provider_user_id="provider-user-1",
            provider_email="user@example.com",
            email_verified=False,
            profile_json={"login": "test-user"},
        )

    def test_upsert_user_promotes_primary_email_after_verified_login(self) -> None:
        profile = self._build_profile(
            email="User@example.com",
            email_verified=True,
        )
        user = self._build_user(user_id="user-1", primary_email=None)
        identity = MagicMock(
            user=user,
            provider_email=None,
            email_verified=False,
            profile_json=None,
        )

        with (
            patch(
                "app.services.auth_service.AuthIdentityRepository.get_by_provider_user_id",
                return_value=identity,
            ),
            patch(
                "app.services.auth_service.UserRepository.get_by_email"
            ) as get_by_email,
            patch("app.services.auth_service.UserRepository.create") as create_user,
            patch(
                "app.services.auth_service.AuthIdentityRepository.create"
            ) as create_identity,
        ):
            result = self.service._upsert_user(self.db, profile)

        get_by_email.assert_not_called()
        create_user.assert_not_called()
        create_identity.assert_not_called()
        self.assertIs(result, user)
        self.assertEqual(user.primary_email, "user@example.com")
        self.assertEqual(identity.provider_email, "user@example.com")
        self.assertTrue(identity.email_verified)

    def test_upsert_user_does_not_merge_unverified_email_into_existing_user(
        self,
    ) -> None:
        profile = self._build_profile(
            email="User@example.com",
            email_verified=False,
            provider_user_id="provider-user-2",
        )
        existing_user = self._build_user(
            user_id="existing-user",
            primary_email="user@example.com",
        )

        with (
            patch(
                "app.services.auth_service.AuthIdentityRepository.get_by_provider_user_id",
                return_value=None,
            ),
            patch(
                "app.services.auth_service.UserRepository.get_by_email",
                return_value=existing_user,
            ) as get_by_email,
            patch("app.services.auth_service.UserRepository.create") as create_user,
            patch("app.services.auth_service.AuthIdentityRepository.create"),
        ):
            create_user.side_effect = (
                lambda _db, *, user_id, primary_email, display_name, avatar_url, status="active": (
                    self._build_user(
                        user_id=user_id,
                        primary_email=primary_email,
                    )
                )
            )

            user = self.service._upsert_user(self.db, profile)

        get_by_email.assert_not_called()
        self.assertNotEqual(user.id, existing_user.id)
        self.assertIsNone(user.primary_email)

    def test_upsert_user_merges_verified_email_into_existing_user(self) -> None:
        profile = self._build_profile(
            email="User@example.com",
            email_verified=True,
            provider_user_id="provider-user-3",
        )
        existing_user = self._build_user(
            user_id="existing-user",
            primary_email="user@example.com",
        )

        with (
            patch(
                "app.services.auth_service.AuthIdentityRepository.get_by_provider_user_id",
                return_value=None,
            ),
            patch(
                "app.services.auth_service.UserRepository.get_by_email",
                return_value=existing_user,
            ) as get_by_email,
            patch("app.services.auth_service.UserRepository.create") as create_user,
            patch(
                "app.services.auth_service.AuthIdentityRepository.create"
            ) as create_identity,
        ):
            user = self.service._upsert_user(self.db, profile)

        get_by_email.assert_called_once_with(self.db, "user@example.com")
        create_user.assert_not_called()
        create_identity.assert_called_once_with(
            self.db,
            user_id="existing-user",
            provider="github",
            provider_user_id="provider-user-3",
            provider_email="user@example.com",
            email_verified=True,
            profile_json={"login": "test-user"},
        )
        self.assertIs(user, existing_user)


if __name__ == "__main__":
    unittest.main()
