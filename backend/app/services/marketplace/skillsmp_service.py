from datetime import datetime
from typing import Any
from pathlib import PurePosixPath
from urllib.parse import quote, urlparse

import httpx

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.core.settings import get_settings
from app.schemas.skill_import import SkillImportCandidate
from app.schemas.skill_marketplace import (
    SkillsMpRecommendationSection,
    SkillsMpRecommendationsResponse,
    SkillsMpSearchResponse,
    SkillsMpSkillItem,
)


class SkillsMpService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _resolve_base_url(self) -> str:
        base_url = self.settings.skillsmp_base_url.strip().rstrip("/")
        if not base_url:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="SKILLSMP_BASE_URL is required for SkillsMP marketplace",
            )
        return base_url

    def _resolve_api_key(self) -> str:
        api_key = self.settings.skillsmp_api_key.strip()
        if not api_key:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="SKILLSMP_API_KEY is required for SkillsMP marketplace",
            )
        return api_key

    @staticmethod
    def _clean_text(value: object) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = value.strip()
        return cleaned or None

    @staticmethod
    def _coerce_int(value: object, *, default: int = 0) -> int:
        if isinstance(value, bool):
            return default
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return default
            try:
                return int(float(stripped))
            except ValueError:
                return default
        return default

    @classmethod
    def _coerce_int_from_keys(
        cls, data: dict[str, Any], *keys: str, default: int = 0
    ) -> int:
        for key in keys:
            if key in data:
                return cls._coerce_int(data.get(key), default=default)
        return default

    @staticmethod
    def _coerce_bool(value: object) -> bool | None:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes"}:
                return True
            if lowered in {"false", "0", "no"}:
                return False
        return None

    @staticmethod
    def _coerce_tags(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        tags: list[str] = []
        for item in value:
            if not isinstance(item, str):
                continue
            cleaned = item.strip()
            if cleaned:
                tags.append(cleaned)
        return tags

    @classmethod
    def _coerce_datetime(cls, value: object) -> datetime | None:
        cleaned = cls._clean_text(value)
        if not cleaned:
            return None
        normalized = cleaned.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None

    @staticmethod
    def _extract_upstream_error_message(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            payload = None

        if isinstance(payload, dict):
            for key in ("message", "error", "detail"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
                if isinstance(value, dict):
                    nested = value.get("message")
                    if isinstance(nested, str) and nested.strip():
                        return nested.strip()

        text = response.text.strip()
        return text or "SkillsMP request failed"

    def _build_detail_url(self, external_id: str) -> str:
        return f"{self._resolve_base_url()}/skills/{quote(external_id, safe='')}"

    @classmethod
    def _normalize_relative_skill_path(cls, value: str | None) -> str | None:
        cleaned = cls._clean_text(value)
        if not cleaned:
            return None
        path = PurePosixPath(cleaned.strip("/"))
        if path.name.lower() == "skill.md":
            path = path.parent
        normalized = path.as_posix()
        if normalized in {"", "."}:
            return "."
        return normalized

    @classmethod
    def _extract_repo_root(cls, github_url: str) -> str:
        cleaned = cls._clean_text(github_url)
        if not cleaned:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="SkillsMP item github_url cannot be empty",
            )
        parsed = urlparse(cleaned)
        if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != "github.com":
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="SkillsMP item github_url must point to github.com",
            )
        segments = [segment for segment in parsed.path.strip("/").split("/") if segment]
        if len(segments) < 2:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="SkillsMP item github_url must include owner and repo",
            )
        owner = segments[0]
        repo = segments[1].removesuffix(".git")
        return f"https://github.com/{owner}/{repo}"

    def build_import_github_url(self, item: SkillsMpSkillItem) -> str:
        cleaned_github_url = self._clean_text(item.github_url)
        if not cleaned_github_url:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Selected SkillsMP item does not include github_url",
            )

        parsed = urlparse(cleaned_github_url)
        if "/tree/" in parsed.path or "/blob/" in parsed.path:
            return cleaned_github_url

        branch = self._clean_text(item.branch)
        relative_skill_path = self._normalize_relative_skill_path(item.relative_skill_path)
        if not branch or "/" in branch:
            return cleaned_github_url

        repo_root = self._extract_repo_root(cleaned_github_url)
        encoded_parts = [quote(part, safe="") for part in branch.split("/")]
        if relative_skill_path and relative_skill_path != ".":
            encoded_parts.extend(
                quote(part, safe="") for part in PurePosixPath(relative_skill_path).parts
            )
        return f"{repo_root}/tree/{'/'.join(encoded_parts)}"

    def build_import_source(self, item: SkillsMpSkillItem) -> dict[str, Any]:
        external_id = self._clean_text(item.external_id)
        if not external_id:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Selected SkillsMP item does not include external_id",
            )
        source: dict[str, Any] = {
            "kind": "marketplace",
            "market": "skillsmp",
            "external_id": external_id,
            "url": self._build_detail_url(external_id),
        }
        try:
            source["repo"] = self._extract_repo_root(item.github_url or "").replace(
                "https://github.com/", "", 1
            )
        except AppException:
            pass
        branch = self._clean_text(item.branch)
        if branch:
            source["ref"] = branch
        return source

    def match_preselected_relative_path(
        self,
        candidates: list[SkillImportCandidate],
        relative_skill_path: str | None,
    ) -> str | None:
        normalized_target = self._normalize_relative_skill_path(relative_skill_path)
        if not normalized_target:
            return None

        exact_match: str | None = None
        suffix_matches: list[str] = []
        target_parts = PurePosixPath(normalized_target).parts

        for candidate in candidates:
            normalized_candidate = self._normalize_relative_skill_path(
                candidate.relative_path
            )
            if not normalized_candidate:
                continue
            if normalized_candidate == normalized_target:
                exact_match = candidate.relative_path
                break

            candidate_parts = PurePosixPath(normalized_candidate).parts
            if len(candidate_parts) <= len(target_parts) and target_parts[
                -len(candidate_parts) :
            ] == candidate_parts:
                suffix_matches.append(candidate.relative_path)

        if exact_match is not None:
            return exact_match
        if len(suffix_matches) == 1:
            return suffix_matches[0]
        return None

    def _map_skill_item(self, raw_item: object) -> SkillsMpSkillItem | None:
        if not isinstance(raw_item, dict):
            return None

        external_id = self._clean_text(raw_item.get("id"))
        name = self._clean_text(raw_item.get("name"))
        if not external_id or not name:
            return None

        return SkillsMpSkillItem(
            external_id=external_id,
            name=name,
            description=self._clean_text(raw_item.get("description")),
            author=self._clean_text(raw_item.get("author")),
            author_avatar_url=self._clean_text(raw_item.get("authorAvatar")),
            github_url=self._clean_text(raw_item.get("githubUrl")),
            branch=self._clean_text(raw_item.get("branch")),
            relative_skill_path=self._clean_text(raw_item.get("path")),
            stars=self._coerce_int(raw_item.get("stars")),
            forks=self._coerce_int(raw_item.get("forks")),
            updated_at=self._coerce_datetime(raw_item.get("updatedAt")),
            skillsmp_url=self._build_detail_url(external_id),
            tags=self._coerce_tags(raw_item.get("tags")),
        )

    def _build_search_response(
        self,
        payload: dict[str, Any],
        *,
        page: int,
        page_size: int,
    ) -> SkillsMpSearchResponse:
        payload_data = payload.get("data") if isinstance(payload.get("data"), dict) else {}

        raw_items = payload_data.get("skills", payload.get("skills"))
        if not isinstance(raw_items, list):
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="SkillsMP returned an invalid skills payload",
                details={"provider": "skillsmp"},
            )

        items = [
            item
            for item in (self._map_skill_item(raw_item) for raw_item in raw_items)
            if item is not None
        ]

        pagination = payload_data.get("pagination", payload.get("pagination"))
        pagination_data = pagination if isinstance(pagination, dict) else {}

        resolved_page = self._coerce_int_from_keys(
            pagination_data, "page", "currentPage", default=page
        )
        resolved_page_size = self._coerce_int_from_keys(
            pagination_data,
            "limit",
            "pageSize",
            "page_size",
            "perPage",
            default=page_size,
        )
        total = self._coerce_int_from_keys(
            pagination_data, "total", "totalCount", "count", default=len(items)
        )
        total_pages = self._coerce_int_from_keys(
            pagination_data, "totalPages", "total_pages", default=0
        )
        if total_pages <= 0 and resolved_page_size > 0 and total > 0:
            total_pages = (total + resolved_page_size - 1) // resolved_page_size
        has_next = self._coerce_bool(
            pagination_data.get("hasNext", pagination_data.get("has_next"))
        )
        if has_next is None:
            has_next = total_pages > 0 and resolved_page < total_pages

        return SkillsMpSearchResponse(
            items=items,
            page=max(resolved_page, 1),
            page_size=max(resolved_page_size, 1),
            total=max(total, 0),
            total_pages=max(total_pages, 0),
            has_next=has_next,
        )

    async def _request_skills(
        self,
        *,
        page: int,
        page_size: int,
        sort_by: str,
        query: str,
        semantic: bool = False,
    ) -> SkillsMpSearchResponse:
        clean_query = self._clean_text(query)
        if not clean_query:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="SkillsMP query cannot be empty",
            )

        params: dict[str, Any] = {
            "page": page,
            "limit": page_size,
            "sortBy": sort_by,
            "q": clean_query,
        }
        endpoint = "/api/v1/skills/ai-search" if semantic else "/api/v1/skills/search"
        url = f"{self._resolve_base_url()}{endpoint}"
        timeout = httpx.Timeout(self.settings.skillsmp_timeout_seconds, connect=5.0)
        headers = {
            "Authorization": f"Bearer {self._resolve_api_key()}",
            "Accept": "application/json",
            "User-Agent": "poco-agent-skillsmp/1.0",
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, params=params, headers=headers)
        except httpx.TimeoutException as exc:
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="SkillsMP request timed out",
                details={"provider": "skillsmp"},
            ) from exc
        except httpx.HTTPError as exc:
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="Failed to reach SkillsMP",
                details={"provider": "skillsmp", "error": str(exc)},
            ) from exc

        if response.status_code >= 400:
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message=self._extract_upstream_error_message(response),
                details={
                    "provider": "skillsmp",
                    "status_code": response.status_code,
                },
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="SkillsMP returned invalid JSON",
                details={"provider": "skillsmp"},
            ) from exc

        if not isinstance(payload, dict):
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message="SkillsMP returned an invalid response payload",
                details={"provider": "skillsmp"},
            )

        return self._build_search_response(payload, page=page, page_size=page_size)

    async def search(
        self,
        *,
        query: str,
        page: int = 1,
        page_size: int = 12,
    ) -> SkillsMpSearchResponse:
        clean_query = (query or "").strip()
        if not clean_query:
            return SkillsMpSearchResponse(
                items=[],
                page=page,
                page_size=page_size,
                total=0,
                total_pages=0,
                has_next=False,
            )

        return await self._request_skills(
            page=page,
            page_size=page_size,
            sort_by="stars",
            query=clean_query,
        )

    async def list_recommendations(
        self,
        *,
        limit: int = 9,
    ) -> SkillsMpRecommendationsResponse:
        recommendation_query = self._clean_text(
            self.settings.skillsmp_recommendation_query
        )
        if not recommendation_query:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="SKILLSMP_RECOMMENDATION_QUERY cannot be empty",
            )

        popular = await self._request_skills(
            page=1,
            page_size=limit,
            sort_by="stars",
            query=recommendation_query,
        )
        recent = await self._request_skills(
            page=1,
            page_size=limit,
            sort_by="recent",
            query=recommendation_query,
        )
        return SkillsMpRecommendationsResponse(
            sections=[
                SkillsMpRecommendationSection(
                    key="popular",
                    title="Popular",
                    items=popular.items,
                ),
                SkillsMpRecommendationSection(
                    key="recent",
                    title="Recent",
                    items=recent.items,
                ),
            ]
        )
