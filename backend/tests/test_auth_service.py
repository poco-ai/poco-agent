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
