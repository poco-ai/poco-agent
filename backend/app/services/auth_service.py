import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any
from urllib.parse import urlencode, urlsplit

import httpx
from authlib.integrations.starlette_client import OAuth
from fastapi import Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.core.settings import Settings, get_settings
from app.models.user import User
from app.models.user_session import UserSession
from app.schemas.auth import AuthConfigResponse, AuthProviderName, AuthProviderStatus
from app.repositories.auth_identity_repository import AuthIdentityRepository
from app.repositories.user_repository import UserRepository
from app.repositories.user_session_repository import UserSessionRepository

GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_USER_EMAILS_URL = "https://api.github.com/user/emails"

FEISHU_CN_AUTHORIZE_URL = "https://accounts.feishu.cn/open-apis/authen/v1/authorize"
FEISHU_CN_TOKEN_URL = "https://open.feishu.cn/open-apis/authen/v2/oauth/token"
FEISHU_CN_USERINFO_URL = "https://open.feishu.cn/open-apis/authen/v1/user_info"
FEISHU_GLOBAL_AUTHORIZE_URL = (
    "https://accounts.larksuite.com/open-apis/authen/v1/authorize"
)
FEISHU_GLOBAL_TOKEN_URL = "https://open.larksuite.com/open-apis/authen/v2/oauth/token"
FEISHU_GLOBAL_USERINFO_URL = "https://open.larksuite.com/open-apis/authen/v1/user_info"

SUPPORTED_AUTH_PROVIDERS: tuple[AuthProviderName, ...] = ("google", "github", "feishu")


@dataclass(slots=True)
class ProviderProfile:
    provider: str
    provider_user_id: str
    email: str | None
    email_verified: bool
    display_name: str | None
    avatar_url: str | None
    profile_json: dict[str, Any]


@lru_cache
def get_oauth_registry() -> OAuth:
    settings = get_settings()
    oauth = OAuth()

    if settings.google_client_id and settings.google_client_secret:
        oauth.register(
            name="google",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )

    if settings.github_client_id and settings.github_client_secret:
        oauth.register(
            name="github",
            client_id=settings.github_client_id,
            client_secret=settings.github_client_secret,
            authorize_url="https://github.com/login/oauth/authorize",
            access_token_url="https://github.com/login/oauth/access_token",
            client_kwargs={"scope": "read:user user:email"},
        )

    return oauth


class AuthService:
    """Service layer for OAuth login and session management."""

    oauth_session_key = "oauth_login"

    @staticmethod
    def normalize_email(email: str | None) -> str | None:
        if email is None:
            return None
        value = email.strip().lower()
        return value or None

    @staticmethod
    def hash_session_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _get_settings(self) -> Settings:
        return get_settings()

    def _normalize_admin_emails(self) -> set[str]:
        settings = self._get_settings()
        normalized: set[str] = set()
        for item in settings.system_admin_emails or []:
            if not isinstance(item, str):
                continue
            for raw_part in item.split(","):
                value = self.normalize_email(raw_part)
                if value:
                    normalized.add(value)
        return normalized

    def _resolve_system_role(self, email: str | None) -> str:
        if self.is_single_user_mode_effective():
            return "admin"
        normalized_email = self.normalize_email(email)
        if normalized_email and normalized_email in self._normalize_admin_emails():
            return "admin"
        return "user"

    def _get_client(self, provider: str):
        client = get_oauth_registry().create_client(provider)
        if client is None:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"OAuth provider is not configured: {provider}",
            )
        return client

    def get_configured_providers(self) -> list[AuthProviderName]:
        settings = self._get_settings()
        providers: list[AuthProviderName] = []
        if (settings.google_client_id or "").strip() and (
            settings.google_client_secret or ""
        ).strip():
            providers.append("google")
        if (settings.github_client_id or "").strip() and (
            settings.github_client_secret or ""
        ).strip():
            providers.append("github")
        if (settings.feishu_oauth_client_id or "").strip() and (
            settings.feishu_oauth_client_secret or ""
        ).strip():
            providers.append("feishu")
        return providers

    def is_single_user_mode_effective(self) -> bool:
        """Return whether requests should resolve to the configured single user.

        `oauth_optional` means:
        - if at least one OAuth provider is configured, login is still required;
        - if no providers are configured, the system falls back to single-user mode.
        """
        settings = self._get_settings()
        if settings.auth_mode == "single_user":
            return True
        return (
            settings.auth_mode == "oauth_optional"
            and not self.get_configured_providers()
        )

    def is_login_required(self) -> bool:
        return not self.is_single_user_mode_effective()

    def is_setup_required(self) -> bool:
        return self.is_login_required() and not self.get_configured_providers()

    def get_auth_config(self) -> AuthConfigResponse:
        configured_providers = self.get_configured_providers()
        return AuthConfigResponse(
            mode=self._get_settings().auth_mode,
            login_required=self.is_login_required(),
            single_user_effective=self.is_single_user_mode_effective(),
            setup_required=self.is_setup_required(),
            configured_providers=configured_providers,
            providers=[
                AuthProviderStatus(
                    name=provider,
                    enabled=provider in configured_providers,
                )
                for provider in SUPPORTED_AUTH_PROVIDERS
            ],
        )

    def _default_next_path(self) -> str:
        settings = self._get_settings()
        language = (settings.frontend_default_language or "en").strip() or "en"
        return f"/{language}/home"

    def normalize_next_path(self, next_path: str | None) -> str:
        if not next_path:
            return self._default_next_path()

        value = next_path.strip()
        if not value:
            return self._default_next_path()

        if value.startswith("//"):
            return self._default_next_path()

        if value.startswith("http://") or value.startswith("https://"):
            frontend_base = self._get_settings().frontend_public_url.rstrip("/")
            if value.startswith(frontend_base + "/"):
                parsed = urlsplit(value)
                normalized = parsed.path or "/"
                if parsed.query:
                    normalized = f"{normalized}?{parsed.query}"
                return normalized
            return self._default_next_path()

        return value if value.startswith("/") else self._default_next_path()

    def _frontend_url(self, path: str) -> str:
        base_url = self._get_settings().frontend_public_url.rstrip("/")
        return f"{base_url}{path}"

    def _login_error_redirect(
        self, next_path: str | None, error_code: str
    ) -> RedirectResponse:
        target_path = self.normalize_next_path(next_path)
        path_parts = [part for part in target_path.split("/") if part]
        language = (
            path_parts[0]
            if path_parts
            else (self._get_settings().frontend_default_language or "en")
        )
        query = urlencode({"error": error_code, "next": target_path})
        return RedirectResponse(
            url=self._frontend_url(f"/{language}/login?{query}"),
            status_code=302,
        )

    def build_redirect_uri(self, provider: str) -> str:
        return self._frontend_url(f"/api/v1/auth/{provider}/callback")

    def _get_feishu_oauth_urls(self) -> tuple[str, str, str]:
        settings = self._get_settings()
        if settings.feishu_oauth_region == "global":
            authorize_url = FEISHU_GLOBAL_AUTHORIZE_URL
            token_url = FEISHU_GLOBAL_TOKEN_URL
            userinfo_url = FEISHU_GLOBAL_USERINFO_URL
        else:
            authorize_url = FEISHU_CN_AUTHORIZE_URL
            token_url = FEISHU_CN_TOKEN_URL
            userinfo_url = FEISHU_CN_USERINFO_URL
        return (
            settings.feishu_oauth_authorize_url or authorize_url,
            settings.feishu_oauth_token_url or token_url,
            settings.feishu_oauth_userinfo_url or userinfo_url,
        )

    def _get_feishu_oauth_credentials(self) -> tuple[str, str]:
        settings = self._get_settings()
        client_id = (settings.feishu_oauth_client_id or "").strip()
        client_secret = (settings.feishu_oauth_client_secret or "").strip()
        if not client_id or not client_secret:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="OAuth provider is not configured: feishu",
            )
        return client_id, client_secret

    def _build_session_expiry(self) -> datetime:
        ttl_days = max(1, self._get_settings().auth_session_ttl_days)
        return datetime.now(timezone.utc) + timedelta(days=ttl_days)

    def set_auth_cookie(self, response: Response, session_token: str) -> None:
        settings = self._get_settings()
        max_age = max(1, settings.auth_session_ttl_days) * 24 * 60 * 60
        response.set_cookie(
            key=settings.auth_cookie_name,
            value=session_token,
            httponly=True,
            secure=settings.auth_cookie_secure,
            samesite="lax",
            path="/",
            max_age=max_age,
        )

    def clear_auth_cookie(self, response: Response) -> None:
        settings = self._get_settings()
        response.delete_cookie(
            key=settings.auth_cookie_name,
            path="/",
            secure=settings.auth_cookie_secure,
            httponly=True,
            samesite="lax",
        )

    async def start_login(
        self,
        request: Request,
        provider: str,
        next_path: str | None,
    ) -> Response:
        if self.is_single_user_mode_effective():
            return RedirectResponse(
                url=self._frontend_url(self.normalize_next_path(next_path)),
                status_code=302,
            )
        if provider == "feishu":
            return self._start_feishu_login(request, next_path)
        try:
            client = self._get_client(provider)
        except AppException:
            return self._login_error_redirect(next_path, "provider_not_configured")

        normalized_next = self.normalize_next_path(next_path)
        oauth_state: dict[str, str] = {
            "provider": provider,
            "next": normalized_next,
        }
        authorize_kwargs: dict[str, str] = {}
        if provider == "google":
            nonce = secrets.token_urlsafe(16)
            oauth_state["nonce"] = nonce
            authorize_kwargs["nonce"] = nonce

        request.session[self.oauth_session_key] = oauth_state
        return await client.authorize_redirect(
            request,
            self.build_redirect_uri(provider),
            **authorize_kwargs,
        )

    def _start_feishu_login(
        self,
        request: Request,
        next_path: str | None,
    ) -> RedirectResponse:
        try:
            client_id, _ = self._get_feishu_oauth_credentials()
        except AppException:
            return self._login_error_redirect(next_path, "provider_not_configured")

        authorize_url, _, _ = self._get_feishu_oauth_urls()
        normalized_next = self.normalize_next_path(next_path)
        state = secrets.token_urlsafe(16)
        request.session[self.oauth_session_key] = {
            "provider": "feishu",
            "next": normalized_next,
            "state": state,
        }

        params = {
            "client_id": client_id,
            "redirect_uri": self.build_redirect_uri("feishu"),
            "response_type": "code",
            "state": state,
        }
        scope = self._get_settings().feishu_oauth_scope.strip()
        if scope:
            params["scope"] = scope
        return RedirectResponse(
            url=f"{authorize_url}?{urlencode(params)}",
            status_code=302,
        )

    async def handle_callback(
        self,
        request: Request,
        provider: str,
        db: Session,
    ) -> RedirectResponse:
        oauth_state = request.session.pop(self.oauth_session_key, None) or {}
        next_path = oauth_state.get("next")
        if oauth_state.get("provider") != provider:
            return self._login_error_redirect(next_path, "invalid_oauth_state")
        if provider == "feishu" and request.query_params.get(
            "state"
        ) != oauth_state.get("state"):
            return self._login_error_redirect(next_path, "invalid_oauth_state")

        try:
            if provider == "feishu":
                token = await self._exchange_feishu_token(request)
            else:
                client = self._get_client(provider)
                token = await client.authorize_access_token(request)
            profile = await self._fetch_provider_profile(provider, token)
            user = self._upsert_user(db, profile)
            session_token = self._create_user_session(db, user.id, request)
            response = RedirectResponse(
                url=self._frontend_url(self.normalize_next_path(next_path)),
                status_code=302,
            )
            self.set_auth_cookie(response, session_token)
            return response
        except Exception:
            db.rollback()
            return self._login_error_redirect(next_path, "oauth_failed")

    def _create_user_session(self, db: Session, user_id: str, request: Request) -> str:
        session_token = secrets.token_urlsafe(32)
        UserSessionRepository.create(
            db,
            session_id=UserSession.generate_id(),
            user_id=user_id,
            session_token_hash=self.hash_session_token(session_token),
            expires_at=self._build_session_expiry(),
            ip_address=request.client.host if request.client else None,
            user_agent=(request.headers.get("user-agent") or "").strip() or None,
        )
        db.commit()
        return session_token

    def _upsert_user(self, db: Session, profile: ProviderProfile) -> User:
        identity = AuthIdentityRepository.get_by_provider_user_id(
            db,
            profile.provider,
            profile.provider_user_id,
        )
        normalized_email = self.normalize_email(profile.email)
        verified_email = normalized_email if profile.email_verified else None

        if identity is not None:
            user = identity.user
            identity.provider_email = normalized_email
            identity.email_verified = profile.email_verified
            identity.profile_json = profile.profile_json
        else:
            user = None
            if verified_email:
                user = UserRepository.get_by_email(db, verified_email)
            if user is None:
                user = UserRepository.create(
                    db,
                    user_id=User.generate_id(),
                    primary_email=verified_email,
                    display_name=profile.display_name,
                    avatar_url=profile.avatar_url,
                    system_role=self._resolve_system_role(verified_email),
                )
                db.flush()
            AuthIdentityRepository.create(
                db,
                user_id=user.id,
                provider=profile.provider,
                provider_user_id=profile.provider_user_id,
                provider_email=normalized_email,
                email_verified=profile.email_verified,
                profile_json=profile.profile_json,
            )

        if verified_email and user.primary_email != verified_email:
            user.primary_email = verified_email
        resolved_system_role = self._resolve_system_role(
            verified_email or user.primary_email
        )
        if user.system_role != resolved_system_role:
            user.system_role = resolved_system_role
        if profile.display_name:
            user.display_name = profile.display_name
        if profile.avatar_url:
            user.avatar_url = profile.avatar_url
        user.status = "active"
        db.flush()
        return user

    async def _fetch_provider_profile(
        self,
        provider: str,
        token: dict[str, Any],
    ) -> ProviderProfile:
        if provider == "google":
            return await self._fetch_google_profile(token)
        if provider == "github":
            return await self._fetch_github_profile(token)
        if provider == "feishu":
            return await self._fetch_feishu_profile(token)
        raise AppException(
            error_code=ErrorCode.BAD_REQUEST,
            message=f"Unsupported OAuth provider: {provider}",
        )

    async def _fetch_google_profile(self, token: dict[str, Any]) -> ProviderProfile:
        payload = token.get("userinfo")
        if not isinstance(payload, dict):
            access_token = str(token.get("access_token") or "").strip()
            if not access_token:
                raise AppException(
                    error_code=ErrorCode.UNAUTHORIZED,
                    message="Google access token is missing",
                )
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    GOOGLE_USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()
                payload = response.json()

        provider_user_id = str(payload.get("sub") or "").strip()
        if not provider_user_id:
            raise AppException(
                error_code=ErrorCode.UNAUTHORIZED,
                message="Google user id is missing",
            )

        return ProviderProfile(
            provider="google",
            provider_user_id=provider_user_id,
            email=self.normalize_email(payload.get("email")),
            email_verified=bool(payload.get("email_verified")),
            display_name=(str(payload.get("name") or "").strip() or None),
            avatar_url=(str(payload.get("picture") or "").strip() or None),
            profile_json=payload,
        )

    async def _fetch_github_profile(self, token: dict[str, Any]) -> ProviderProfile:
        access_token = str(token.get("access_token") or "").strip()
        if not access_token:
            raise AppException(
                error_code=ErrorCode.UNAUTHORIZED,
                message="GitHub access token is missing",
            )

        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "poco-auth",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            user_response = await client.get(GITHUB_USER_URL, headers=headers)
            user_response.raise_for_status()
            user_payload = user_response.json()

            email_response = await client.get(GITHUB_USER_EMAILS_URL, headers=headers)
            email_response.raise_for_status()
            email_payload = email_response.json()

        provider_user_id = str(user_payload.get("id") or "").strip()
        if not provider_user_id:
            raise AppException(
                error_code=ErrorCode.UNAUTHORIZED,
                message="GitHub user id is missing",
            )

        selected_email, email_verified = self._select_github_email(email_payload)
        selected_email = selected_email or self.normalize_email(
            user_payload.get("email")
        )
        display_name = (
            str(user_payload.get("name") or "").strip()
            or str(user_payload.get("login") or "").strip()
            or None
        )
        avatar_url = str(user_payload.get("avatar_url") or "").strip() or None

        return ProviderProfile(
            provider="github",
            provider_user_id=provider_user_id,
            email=selected_email,
            email_verified=email_verified,
            display_name=display_name,
            avatar_url=avatar_url,
            profile_json={
                "user": user_payload,
                "emails": email_payload,
            },
        )

    @staticmethod
    def _extract_nested_dict(payload: Any, key: str) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return {}
        value = payload.get(key)
        return value if isinstance(value, dict) else {}

    def _extract_feishu_access_token(self, payload: dict[str, Any]) -> str | None:
        data = self._extract_nested_dict(payload, "data")
        token = (
            payload.get("access_token")
            or payload.get("user_access_token")
            or data.get("access_token")
            or data.get("user_access_token")
        )
        value = str(token or "").strip()
        return value or None

    async def _exchange_feishu_token(self, request: Request) -> dict[str, Any]:
        error = (request.query_params.get("error") or "").strip()
        if error:
            raise AppException(
                error_code=ErrorCode.UNAUTHORIZED,
                message=f"Feishu OAuth returned error: {error}",
            )

        code = (request.query_params.get("code") or "").strip()
        if not code:
            raise AppException(
                error_code=ErrorCode.UNAUTHORIZED,
                message="Feishu OAuth code is missing",
            )

        client_id, client_secret = self._get_feishu_oauth_credentials()
        _, token_url, _ = self._get_feishu_oauth_urls()
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                token_url,
                json={
                    "grant_type": "authorization_code",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "redirect_uri": self.build_redirect_uri("feishu"),
                },
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            payload = response.json()

        if not isinstance(payload, dict):
            raise AppException(
                error_code=ErrorCode.UNAUTHORIZED,
                message="Feishu OAuth token response is invalid",
            )
        if payload.get("code") not in (None, 0):
            raise AppException(
                error_code=ErrorCode.UNAUTHORIZED,
                message=f"Feishu OAuth token request failed: {payload.get('msg')}",
            )
        if not self._extract_feishu_access_token(payload):
            raise AppException(
                error_code=ErrorCode.UNAUTHORIZED,
                message="Feishu access token is missing",
            )
        return payload

    def _extract_feishu_user_data(self, payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return {}
        data = payload.get("data")
        return data if isinstance(data, dict) else payload

    async def _fetch_feishu_profile(self, token: dict[str, Any]) -> ProviderProfile:
        access_token = self._extract_feishu_access_token(token)
        if not access_token:
            raise AppException(
                error_code=ErrorCode.UNAUTHORIZED,
                message="Feishu access token is missing",
            )

        _, _, userinfo_url = self._get_feishu_oauth_urls()
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            payload = response.json()

        if isinstance(payload, dict) and payload.get("code") not in (None, 0):
            raise AppException(
                error_code=ErrorCode.UNAUTHORIZED,
                message=f"Feishu user info request failed: {payload.get('msg')}",
            )

        data = self._extract_feishu_user_data(payload)
        provider_user_id = (
            str(data.get("union_id") or "").strip()
            or str(data.get("open_id") or "").strip()
            or str(data.get("user_id") or "").strip()
            or str(data.get("sub") or "").strip()
        )
        if not provider_user_id:
            raise AppException(
                error_code=ErrorCode.UNAUTHORIZED,
                message="Feishu user id is missing",
            )

        email = self.normalize_email(data.get("email"))
        display_name = (
            str(data.get("name") or "").strip()
            or str(data.get("en_name") or "").strip()
            or None
        )
        avatar_url = (
            str(
                data.get("avatar_url")
                or data.get("avatar_big")
                or data.get("avatar_middle")
                or data.get("avatar_thumb")
                or ""
            ).strip()
            or None
        )

        return ProviderProfile(
            provider="feishu",
            provider_user_id=provider_user_id,
            email=email,
            email_verified=bool(
                email and self._get_settings().feishu_oauth_email_verified
            ),
            display_name=display_name,
            avatar_url=avatar_url,
            profile_json=payload if isinstance(payload, dict) else {"raw": payload},
        )

    def _select_github_email(self, payload: Any) -> tuple[str | None, bool]:
        if not isinstance(payload, list):
            return None, False

        candidates: list[dict[str, Any]] = [
            item for item in payload if isinstance(item, dict)
        ]
        ordered = sorted(
            candidates,
            key=lambda item: (
                not bool(item.get("verified")),
                not bool(item.get("primary")),
            ),
        )
        for item in ordered:
            email = self.normalize_email(item.get("email"))
            if email:
                return email, bool(item.get("verified"))
        return None, False

    def authenticate_session_token(
        self,
        db: Session,
        session_token: str,
    ) -> UserSession | None:
        value = session_token.strip()
        if not value:
            return None
        return UserSessionRepository.get_active_by_token_hash(
            db,
            self.hash_session_token(value),
            datetime.now(timezone.utc),
        )

    def ensure_single_user(self, db: Session) -> User:
        settings = self._get_settings()
        single_user_id = settings.single_user_id.strip() or "default"
        user = UserRepository.get_by_id(db, single_user_id)
        display_name = settings.single_user_name.strip() or None

        if user is None:
            user = UserRepository.create(
                db,
                user_id=single_user_id,
                primary_email=None,
                display_name=display_name,
                avatar_url=None,
                status="active",
                system_role="admin",
            )
            db.commit()
            return user

        updated = False
        if user.display_name != display_name:
            user.display_name = display_name
            updated = True
        if user.primary_email is not None:
            user.primary_email = None
            updated = True
        if user.status != "active":
            user.status = "active"
            updated = True
        if user.system_role != "admin":
            user.system_role = "admin"
            updated = True
        if updated:
            db.commit()
        return user

    def logout(self, db: Session, session_token: str | None) -> None:
        if session_token is None or not session_token.strip():
            return
        UserSessionRepository.revoke_by_token_hash(
            db,
            self.hash_session_token(session_token.strip()),
            datetime.now(timezone.utc),
        )
        db.commit()
