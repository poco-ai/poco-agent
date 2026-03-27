from dataclasses import dataclass
from typing import cast

import httpx
from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.core.settings import get_settings
from app.repositories.mcp_server_repository import McpServerRepository
from app.repositories.skill_repository import SkillRepository
from app.repositories.user_mcp_install_repository import UserMcpInstallRepository
from app.repositories.user_skill_install_repository import UserSkillInstallRepository
from app.schemas.capability_recommendation import (
    CapabilityRecommendationItem,
    CapabilityRecommendationResponse,
    CapabilityRecommendationType,
)


@dataclass(slots=True)
class _CapabilityCandidate:
    type: CapabilityRecommendationType
    id: int
    name: str
    description: str | None
    default_enabled: bool
    document: str


class CapabilityRecommendationService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _resolve_api_key(self) -> str:
        api_key = (self.settings.siliconflow_api_key or "").strip()
        if not api_key:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="SILICONFLOW_API_KEY is required for capability recommendations",
            )
        return api_key

    def _resolve_rerank_url(self) -> str:
        base_url = self.settings.siliconflow_base_url.strip().rstrip("/")
        if not base_url:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="SILICONFLOW_BASE_URL is required for capability recommendations",
            )
        if base_url.endswith("/rerank"):
            return base_url
        return f"{base_url}/rerank"

    @staticmethod
    def _clean_text(value: object) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = value.strip()
        return cleaned or None

    def _build_skill_source_text(self, source: object) -> str | None:
        if not isinstance(source, dict):
            return None

        source_dict = cast(dict[str, object], source)
        repo = self._clean_text(source_dict.get("repo"))
        if repo:
            return repo

        filename = self._clean_text(source_dict.get("filename"))
        if filename:
            return filename

        kind = self._clean_text(source_dict.get("kind"))
        return kind

    def _build_document(
        self,
        *,
        capability_type: CapabilityRecommendationType,
        name: str,
        description: str | None,
        source_text: str | None = None,
    ) -> str:
        lines = [
            f"Type: {'MCP server' if capability_type == 'mcp' else 'Skill'}",
            f"Name: {name}",
        ]
        if description:
            lines.append(f"Description: {description}")
        if source_text:
            lines.append(f"Source: {source_text}")
        return "\n".join(lines)

    def _build_candidates(
        self, db: Session, user_id: str
    ) -> list[_CapabilityCandidate]:
        candidates: list[_CapabilityCandidate] = []

        mcp_installs = {
            install.server_id: install.enabled
            for install in UserMcpInstallRepository.list_by_user(db, user_id)
        }
        for server in McpServerRepository.list_visible(db, user_id=user_id):
            default_enabled = mcp_installs.get(server.id)
            if default_enabled is None:
                continue
            candidates.append(
                _CapabilityCandidate(
                    type="mcp",
                    id=server.id,
                    name=server.name,
                    description=self._clean_text(server.description),
                    default_enabled=default_enabled,
                    document=self._build_document(
                        capability_type="mcp",
                        name=server.name,
                        description=self._clean_text(server.description),
                        source_text=server.scope,
                    ),
                )
            )

        skill_installs = {
            install.skill_id: install.enabled
            for install in UserSkillInstallRepository.list_by_user(db, user_id)
        }
        for skill in SkillRepository.list_visible(db, user_id=user_id):
            default_enabled = skill_installs.get(skill.id)
            if default_enabled is None:
                continue
            candidates.append(
                _CapabilityCandidate(
                    type="skill",
                    id=skill.id,
                    name=skill.name,
                    description=self._clean_text(skill.description),
                    default_enabled=default_enabled,
                    document=self._build_document(
                        capability_type="skill",
                        name=skill.name,
                        description=self._clean_text(skill.description),
                        source_text=self._build_skill_source_text(skill.source),
                    ),
                )
            )

        return candidates

    @staticmethod
    def _extract_upstream_error_message(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            payload = None

        if isinstance(payload, dict):
            message = payload.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()
            error = payload.get("error")
            if isinstance(error, dict):
                detail = error.get("message")
                if isinstance(detail, str) and detail.strip():
                    return detail.strip()

        text = response.text.strip()
        return text or "Capability rerank request failed"

    async def recommend(
        self,
        db: Session,
        *,
        user_id: str,
        query: str,
        limit: int = 3,
    ) -> CapabilityRecommendationResponse:
        clean_query = (query or "").strip()
        if not clean_query:
            return CapabilityRecommendationResponse(query="", items=[])

        candidates = self._build_candidates(db, user_id)
        if not candidates:
            return CapabilityRecommendationResponse(query=clean_query, items=[])

        api_key = self._resolve_api_key()
        target_url = self._resolve_rerank_url()

        payload = {
            "model": self.settings.siliconflow_rerank_model.strip(),
            "query": clean_query,
            "documents": [candidate.document for candidate in candidates],
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.settings.siliconflow_timeout_seconds
            ) as client:
                response = await client.post(target_url, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="Capability recommendation request timed out",
                details={"provider": "siliconflow"},
            ) from exc
        except httpx.HTTPError as exc:
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="Failed to reach capability recommendation provider",
                details={"provider": "siliconflow", "error": str(exc)},
            ) from exc

        if response.status_code >= 400:
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message=self._extract_upstream_error_message(response),
                details={
                    "provider": "siliconflow",
                    "status_code": response.status_code,
                },
            )

        try:
            upstream_payload = response.json()
        except ValueError as exc:
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="Capability recommendation provider returned invalid JSON",
                details={"provider": "siliconflow"},
            ) from exc

        raw_results = (
            upstream_payload.get("results")
            if isinstance(upstream_payload, dict)
            else None
        )
        if not isinstance(raw_results, list):
            return CapabilityRecommendationResponse(query=clean_query, items=[])

        items: list[CapabilityRecommendationItem] = []
        for raw_item in raw_results:
            if len(items) >= limit:
                break
            if not isinstance(raw_item, dict):
                continue
            raw_index = raw_item.get("index")
            if not isinstance(raw_index, int):
                continue
            if raw_index < 0 or raw_index >= len(candidates):
                continue

            score = raw_item.get("relevance_score")
            if isinstance(score, int):
                score = float(score)
            if not isinstance(score, float):
                score = 0.0

            candidate = candidates[raw_index]
            items.append(
                CapabilityRecommendationItem(
                    type=candidate.type,
                    id=candidate.id,
                    name=candidate.name,
                    description=candidate.description,
                    score=score,
                    default_enabled=candidate.default_enabled,
                )
            )

        return CapabilityRecommendationResponse(query=clean_query, items=items)
