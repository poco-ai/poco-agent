import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.core.deps import get_current_user_id
from app.models.user_session import UserSession


class AuthDepsTests(unittest.TestCase):
    def _request_with_cookie(self, session_token: str | None = None) -> MagicMock:
        request = MagicMock()
        request.cookies = {}
        if session_token is not None:
            request.cookies["poco_session"] = session_token
        return request

    def test_get_current_user_id_uses_local_user_when_auth_mode_is_disabled(self) -> None:
        request = self._request_with_cookie()
        settings = SimpleNamespace(
            auth_cookie_name="poco_session",
            auth_mode="disabled",
            internal_api_token="internal-token",
        )
        local_user = SimpleNamespace(id="local-user")

        with (
            patch("app.core.deps.get_settings", return_value=settings),
            patch.object(
                get_current_user_id.__globals__["auth_service"],
                "get_or_create_local_user",
                return_value=local_user,
            ) as get_or_create_local_user,
        ):
            user_id = get_current_user_id(
                request,
                db=MagicMock(),
                authorization=None,
                x_user_id=None,
                x_internal_token=None,
            )

        get_or_create_local_user.assert_called_once()
        self.assertEqual(user_id, "local-user")

    def test_get_current_user_id_ignores_stale_cookie_when_auth_mode_is_disabled(
        self,
    ) -> None:
        request = self._request_with_cookie("stale-token")
        settings = SimpleNamespace(
            auth_cookie_name="poco_session",
            auth_mode="disabled",
            internal_api_token="internal-token",
        )
        local_user = SimpleNamespace(id="local-user")

        with (
            patch("app.core.deps.get_settings", return_value=settings),
            patch.object(
                get_current_user_id.__globals__["auth_service"],
                "authenticate_session_token",
                return_value=None,
            ) as authenticate_session_token,
            patch.object(
                get_current_user_id.__globals__["auth_service"],
                "get_or_create_local_user",
                return_value=local_user,
            ) as get_or_create_local_user,
        ):
            user_id = get_current_user_id(
                request,
                db=MagicMock(),
                authorization=None,
                x_user_id=None,
                x_internal_token=None,
            )

        authenticate_session_token.assert_called_once()
        get_or_create_local_user.assert_called_once()
        self.assertEqual(user_id, "local-user")

    def test_get_current_user_id_rejects_missing_auth_when_oauth_is_required(
        self,
    ) -> None:
        request = self._request_with_cookie()
        settings = SimpleNamespace(
            auth_cookie_name="poco_session",
            auth_mode="oauth_required",
            internal_api_token="internal-token",
        )

        with patch("app.core.deps.get_settings", return_value=settings):
            with self.assertRaises(HTTPException) as context:
                get_current_user_id(
                    request,
                    db=MagicMock(),
                    authorization=None,
                    x_user_id=None,
                    x_internal_token=None,
                )

        self.assertEqual(context.exception.status_code, 401)

    def test_get_current_user_id_returns_authenticated_session_user(self) -> None:
        request = self._request_with_cookie("valid-token")
        settings = SimpleNamespace(
            auth_cookie_name="poco_session",
            auth_mode="oauth_required",
            internal_api_token="internal-token",
        )
        session = UserSession(
            id="session-1",
            user_id="user-123",
            session_token_hash="hash",
            expires_at=None,
            revoked_at=None,
            ip_address=None,
            user_agent=None,
        )

        with (
            patch("app.core.deps.get_settings", return_value=settings),
            patch.object(
                get_current_user_id.__globals__["auth_service"],
                "authenticate_session_token",
                return_value=session,
            ) as authenticate_session_token,
        ):
            user_id = get_current_user_id(
                request,
                db=MagicMock(),
                authorization=None,
                x_user_id=None,
                x_internal_token=None,
            )

        authenticate_session_token.assert_called_once()
        self.assertEqual(user_id, "user-123")


if __name__ == "__main__":
    unittest.main()
