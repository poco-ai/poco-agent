from sqlalchemy.orm import Session, joinedload

from app.models.auth_identity import AuthIdentity


class AuthIdentityRepository:
    """Data access layer for auth identities."""

    @staticmethod
    def create(
        session_db: Session,
        *,
        user_id: str,
        provider: str,
        provider_user_id: str,
        provider_email: str | None,
        email_verified: bool,
        profile_json: dict | None,
    ) -> AuthIdentity:
        identity = AuthIdentity(
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_email=provider_email,
            email_verified=email_verified,
            profile_json=profile_json,
        )
        session_db.add(identity)
        return identity

    @staticmethod
    def get_by_provider_user_id(
        session_db: Session,
        provider: str,
        provider_user_id: str,
    ) -> AuthIdentity | None:
        return (
            session_db.query(AuthIdentity)
            .options(joinedload(AuthIdentity.user))
            .filter(
                AuthIdentity.provider == provider,
                AuthIdentity.provider_user_id == provider_user_id,
            )
            .first()
        )
