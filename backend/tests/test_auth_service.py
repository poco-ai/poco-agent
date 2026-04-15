import unittest
from types import SimpleNamespace
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
            patch(
                "app.services.auth_service.UserRepository.create"
            ) as create_user,
            patch("app.services.auth_service.AuthIdentityRepository.create")
            as create_identity,
        ):
            create_user.side_effect = (
                lambda _db, *, user_id, primary_email, display_name, avatar_url, status="active": self._build_user(
                    user_id=user_id,
                    primary_email=primary_email,
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
            patch("app.services.auth_service.UserRepository.get_by_email")
            as get_by_email,
            patch("app.services.auth_service.UserRepository.create") as create_user,
            patch("app.services.auth_service.AuthIdentityRepository.create")
            as create_identity,
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
            patch(
                "app.services.auth_service.UserRepository.create"
            ) as create_user,
            patch("app.services.auth_service.AuthIdentityRepository.create"),
        ):
            create_user.side_effect = (
                lambda _db, *, user_id, primary_email, display_name, avatar_url, status="active": self._build_user(
                    user_id=user_id,
                    primary_email=primary_email,
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
            patch("app.services.auth_service.AuthIdentityRepository.create")
            as create_identity,
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

    def test_get_auth_config_returns_disabled_mode_without_login_requirement(
        self,
    ) -> None:
        settings = SimpleNamespace(
            auth_mode="disabled",
            workspace_features_enabled=False,
            google_client_id=None,
            google_client_secret=None,
            github_client_id=None,
            github_client_secret=None,
        )

        with patch.object(self.service, "_get_settings", return_value=settings):
            config = self.service.get_auth_config()

        self.assertEqual(config.auth_mode, "disabled")
        self.assertFalse(config.login_required)
        self.assertFalse(config.workspace_features_enabled)
        self.assertEqual(config.providers, [])

    def test_get_auth_config_returns_configured_oauth_providers(self) -> None:
        settings = SimpleNamespace(
            auth_mode="oauth_required",
            workspace_features_enabled=True,
            google_client_id="google-client",
            google_client_secret="google-secret",
            github_client_id="github-client",
            github_client_secret="github-secret",
        )

        with patch.object(self.service, "_get_settings", return_value=settings):
            config = self.service.get_auth_config()

        self.assertEqual(config.auth_mode, "oauth_required")
        self.assertTrue(config.login_required)
        self.assertTrue(config.workspace_features_enabled)
        self.assertEqual(config.providers, ["google", "github"])

    def test_get_or_create_local_user_returns_existing_user(self) -> None:
        existing_user = self._build_user(
            user_id="local-user",
            primary_email=None,
        )
        settings = SimpleNamespace(
            local_default_user_id="local-user",
            local_default_user_name="Poco Local User",
        )

        with (
            patch.object(self.service, "_get_settings", return_value=settings),
            patch(
                "app.services.auth_service.UserRepository.get_by_id",
                return_value=existing_user,
            ) as get_by_id,
            patch("app.services.auth_service.UserRepository.create") as create_user,
        ):
            user = self.service.get_or_create_local_user(self.db)

        get_by_id.assert_called_once_with(self.db, "local-user")
        create_user.assert_not_called()
        self.db.commit.assert_not_called()
        self.assertIs(user, existing_user)

    def test_get_or_create_local_user_creates_default_user_when_missing(self) -> None:
        settings = SimpleNamespace(
            local_default_user_id="local-user",
            local_default_user_name="Poco Local User",
        )
        created_user = self._build_user(
            user_id="local-user",
            primary_email=None,
        )

        with (
            patch.object(self.service, "_get_settings", return_value=settings),
            patch(
                "app.services.auth_service.UserRepository.get_by_id",
                return_value=None,
            ) as get_by_id,
            patch(
                "app.services.auth_service.UserRepository.create",
                return_value=created_user,
            ) as create_user,
        ):
            user = self.service.get_or_create_local_user(self.db)

        get_by_id.assert_called_once_with(self.db, "local-user")
        create_user.assert_called_once_with(
            self.db,
            user_id="local-user",
            primary_email=None,
            display_name="Poco Local User",
            avatar_url=None,
        )
        self.db.commit.assert_called_once()
        self.assertIs(user, created_user)


if __name__ == "__main__":
    unittest.main()
