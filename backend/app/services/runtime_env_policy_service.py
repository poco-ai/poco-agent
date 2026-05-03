from sqlalchemy.orm import Session

from app.models.runtime_env_policy import RuntimeEnvPolicy
from app.repositories.runtime_env_policy_repository import RuntimeEnvPolicyRepository
from app.schemas.runtime_env_policy import (
    RuntimeEnvPolicyResponse,
    RuntimeEnvPolicyUpdateRequest,
)

PROTECTED_RUNTIME_ENV_KEYS = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_BASE_URL",
    "AUTH_COOKIE_NAME",
    "DATABASE_URL",
    "DEFAULT_MODEL",
    "GITHUB_CLIENT_SECRET",
    "GOOGLE_CLIENT_SECRET",
    "HOME",
    "INTERNAL_API_TOKEN",
    "LD_LIBRARY_PATH",
    "LD_PRELOAD",
    "MODEL_LIST",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "PATH",
    "PWD",
    "PYTHONPATH",
    "S3_ACCESS_KEY",
    "S3_SECRET_KEY",
    "SECRET_KEY",
)
PROTECTED_RUNTIME_ENV_PREFIXES = (
    "AUTH_",
    "POCO_",
)


class RuntimeEnvPolicyService:
    def get_policy(self, db: Session) -> RuntimeEnvPolicyResponse:
        policy = RuntimeEnvPolicyRepository.get_first(db)
        if policy is None:
            return RuntimeEnvPolicyResponse(
                mode="opt_in",
                allowlist_patterns=[],
                denylist_patterns=[],
                protected_keys=list(PROTECTED_RUNTIME_ENV_KEYS),
                protected_prefixes=list(PROTECTED_RUNTIME_ENV_PREFIXES),
                updated_at=None,
            )

        return RuntimeEnvPolicyResponse(
            mode=policy.mode,
            allowlist_patterns=self._normalize_patterns(policy.allowlist_patterns),
            denylist_patterns=self._normalize_patterns(policy.denylist_patterns),
            protected_keys=list(PROTECTED_RUNTIME_ENV_KEYS),
            protected_prefixes=list(PROTECTED_RUNTIME_ENV_PREFIXES),
            updated_at=policy.updated_at,
        )

    def update_policy(
        self,
        db: Session,
        request: RuntimeEnvPolicyUpdateRequest,
    ) -> RuntimeEnvPolicyResponse:
        policy = RuntimeEnvPolicyRepository.get_first(db)
        if policy is None:
            policy = RuntimeEnvPolicy(
                mode=request.mode,
                allowlist_patterns=self._normalize_patterns(request.allowlist_patterns),
                denylist_patterns=self._normalize_patterns(request.denylist_patterns),
            )
            RuntimeEnvPolicyRepository.create(db, policy)
        else:
            policy.mode = request.mode
            policy.allowlist_patterns = self._normalize_patterns(
                request.allowlist_patterns
            )
            policy.denylist_patterns = self._normalize_patterns(
                request.denylist_patterns
            )

        db.commit()
        db.refresh(policy)
        return self.get_policy(db)

    @staticmethod
    def _normalize_patterns(patterns: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for item in patterns:
            normalized = str(item or "").strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            result.append(normalized)
        return result
