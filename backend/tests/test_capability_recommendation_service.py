import unittest
from unittest.mock import MagicMock, patch, AsyncMock

import httpx

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.services.capability_recommendation_service import (
    CapabilityRecommendationService,
    _CapabilityCandidate,
)


class TestCapabilityCandidate(unittest.TestCase):
    """Test _CapabilityCandidate dataclass."""

    def test_create(self) -> None:
        candidate = _CapabilityCandidate(
            type="mcp",
            id=1,
            name="test-server",
            description="Test server",
            default_enabled=True,
            document="Type: MCP server\nName: test-server",
        )

        self.assertEqual(candidate.type, "mcp")
        self.assertEqual(candidate.id, 1)
        self.assertEqual(candidate.name, "test-server")
        self.assertEqual(candidate.description, "Test server")
        self.assertTrue(candidate.default_enabled)


class TestCapabilityRecommendationServiceCleanText(unittest.TestCase):
    """Test _clean_text static method."""

    def test_clean_text_string(self) -> None:
        result = CapabilityRecommendationService._clean_text("  hello  ")
        self.assertEqual(result, "hello")

    def test_clean_text_empty_string(self) -> None:
        result = CapabilityRecommendationService._clean_text("")
        self.assertIsNone(result)

    def test_clean_text_whitespace_only(self) -> None:
        result = CapabilityRecommendationService._clean_text("   ")
        self.assertIsNone(result)

    def test_clean_text_non_string(self) -> None:
        result = CapabilityRecommendationService._clean_text(123)
        self.assertIsNone(result)

    def test_clean_text_none(self) -> None:
        result = CapabilityRecommendationService._clean_text(None)
        self.assertIsNone(result)


class TestCapabilityRecommendationServiceBuildSkillSourceText(unittest.TestCase):
    """Test _build_skill_source_text method."""

    def setUp(self) -> None:
        self.service = CapabilityRecommendationService()

    def test_non_dict(self) -> None:
        result = self.service._build_skill_source_text("not a dict")
        self.assertIsNone(result)

    def test_with_repo(self) -> None:
        source = {"repo": "owner/repo", "filename": "file.md"}
        result = self.service._build_skill_source_text(source)
        self.assertEqual(result, "owner/repo")

    def test_with_filename_no_repo(self) -> None:
        source = {"filename": "skill.md"}
        result = self.service._build_skill_source_text(source)
        self.assertEqual(result, "skill.md")

    def test_with_kind_only(self) -> None:
        source = {"kind": "manual"}
        result = self.service._build_skill_source_text(source)
        self.assertEqual(result, "manual")

    def test_empty_dict(self) -> None:
        result = self.service._build_skill_source_text({})
        self.assertIsNone(result)

    def test_empty_values(self) -> None:
        source = {"repo": "  ", "filename": "", "kind": None}
        result = self.service._build_skill_source_text(source)
        self.assertIsNone(result)


class TestCapabilityRecommendationServiceBuildDocument(unittest.TestCase):
    """Test _build_document method."""

    def setUp(self) -> None:
        self.service = CapabilityRecommendationService()

    def test_mcp_server(self) -> None:
        result = self.service._build_document(
            capability_type="mcp",
            name="test-server",
            description="Test description",
            source_text="system",
        )

        self.assertIn("Type: MCP server", result)
        self.assertIn("Name: test-server", result)
        self.assertIn("Description: Test description", result)
        self.assertIn("Source: system", result)

    def test_skill(self) -> None:
        result = self.service._build_document(
            capability_type="skill",
            name="test-skill",
            description="Skill description",
        )

        self.assertIn("Type: Skill", result)
        self.assertIn("Name: test-skill", result)
        self.assertIn("Description: Skill description", result)

    def test_no_description(self) -> None:
        result = self.service._build_document(
            capability_type="mcp",
            name="test-server",
            description=None,
        )

        self.assertIn("Name: test-server", result)
        self.assertNotIn("Description:", result)

    def test_no_source_text(self) -> None:
        result = self.service._build_document(
            capability_type="skill",
            name="test-skill",
            description="Description",
            source_text=None,
        )

        self.assertNotIn("Source:", result)


class TestCapabilityRecommendationServiceExtractUpstreamErrorMessage(unittest.TestCase):
    """Test _extract_upstream_error_message static method."""

    def test_message_in_payload(self) -> None:
        response = MagicMock(spec=httpx.Response)
        response.json.return_value = {"message": "Error message"}
        response.text = ""

        result = CapabilityRecommendationService._extract_upstream_error_message(
            response
        )
        self.assertEqual(result, "Error message")

    def test_error_dict_in_payload(self) -> None:
        response = MagicMock(spec=httpx.Response)
        response.json.return_value = {"error": {"message": "Error detail"}}
        response.text = ""

        result = CapabilityRecommendationService._extract_upstream_error_message(
            response
        )
        self.assertEqual(result, "Error detail")

    def test_no_json_response(self) -> None:
        response = MagicMock(spec=httpx.Response)
        response.json.side_effect = ValueError("not json")
        response.text = "Plain text error"

        result = CapabilityRecommendationService._extract_upstream_error_message(
            response
        )
        self.assertEqual(result, "Plain text error")

    def test_empty_response(self) -> None:
        response = MagicMock(spec=httpx.Response)
        response.json.side_effect = ValueError("not json")
        response.text = ""

        result = CapabilityRecommendationService._extract_upstream_error_message(
            response
        )
        self.assertEqual(result, "Capability rerank request failed")

    def test_empty_message_in_payload(self) -> None:
        response = MagicMock(spec=httpx.Response)
        response.json.return_value = {"message": "   "}
        response.text = "Fallback text"

        result = CapabilityRecommendationService._extract_upstream_error_message(
            response
        )
        self.assertEqual(result, "Fallback text")

    def test_non_dict_payload(self) -> None:
        response = MagicMock(spec=httpx.Response)
        response.json.return_value = ["not", "a", "dict"]
        response.text = "Text response"

        result = CapabilityRecommendationService._extract_upstream_error_message(
            response
        )
        self.assertEqual(result, "Text response")


class TestCapabilityRecommendationServiceResolveApiKey(unittest.TestCase):
    """Test _resolve_api_key method."""

    def test_valid_api_key(self) -> None:
        with patch(
            "app.services.capability_recommendation_service.get_settings"
        ) as mock_settings:
            settings = MagicMock()
            settings.siliconflow_api_key = "test-key"
            mock_settings.return_value = settings

            service = CapabilityRecommendationService()
            result = service._resolve_api_key()

            self.assertEqual(result, "test-key")

    def test_missing_api_key(self) -> None:
        with patch(
            "app.services.capability_recommendation_service.get_settings"
        ) as mock_settings:
            settings = MagicMock()
            settings.siliconflow_api_key = None
            mock_settings.return_value = settings

            service = CapabilityRecommendationService()

            with self.assertRaises(AppException) as ctx:
                service._resolve_api_key()

            self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    def test_empty_api_key(self) -> None:
        with patch(
            "app.services.capability_recommendation_service.get_settings"
        ) as mock_settings:
            settings = MagicMock()
            settings.siliconflow_api_key = "   "
            mock_settings.return_value = settings

            service = CapabilityRecommendationService()

            with self.assertRaises(AppException) as ctx:
                service._resolve_api_key()

            self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)


class TestCapabilityRecommendationServiceResolveRerankUrl(unittest.TestCase):
    """Test _resolve_rerank_url method."""

    def test_url_without_rerank(self) -> None:
        with patch(
            "app.services.capability_recommendation_service.get_settings"
        ) as mock_settings:
            settings = MagicMock()
            settings.siliconflow_base_url = "https://api.example.com"
            mock_settings.return_value = settings

            service = CapabilityRecommendationService()
            result = service._resolve_rerank_url()

            self.assertEqual(result, "https://api.example.com/rerank")

    def test_url_with_rerank(self) -> None:
        with patch(
            "app.services.capability_recommendation_service.get_settings"
        ) as mock_settings:
            settings = MagicMock()
            settings.siliconflow_base_url = "https://api.example.com/rerank"
            mock_settings.return_value = settings

            service = CapabilityRecommendationService()
            result = service._resolve_rerank_url()

            self.assertEqual(result, "https://api.example.com/rerank")

    def test_url_with_trailing_slash(self) -> None:
        with patch(
            "app.services.capability_recommendation_service.get_settings"
        ) as mock_settings:
            settings = MagicMock()
            settings.siliconflow_base_url = "https://api.example.com/"
            mock_settings.return_value = settings

            service = CapabilityRecommendationService()
            result = service._resolve_rerank_url()

            self.assertEqual(result, "https://api.example.com/rerank")

    def test_empty_base_url(self) -> None:
        with patch(
            "app.services.capability_recommendation_service.get_settings"
        ) as mock_settings:
            settings = MagicMock()
            settings.siliconflow_base_url = ""
            mock_settings.return_value = settings

            service = CapabilityRecommendationService()

            with self.assertRaises(AppException) as ctx:
                service._resolve_rerank_url()

            self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)


class TestCapabilityRecommendationServiceBuildCandidates(unittest.TestCase):
    """Test _build_candidates method."""

    def setUp(self) -> None:
        self.db = MagicMock()
        self.user_id = "user-123"

    def test_empty_candidates(self) -> None:
        with patch(
            "app.services.capability_recommendation_service.get_settings"
        ) as mock_settings:
            settings = MagicMock()
            settings.siliconflow_api_key = "test-key"
            mock_settings.return_value = settings

            with patch(
                "app.services.capability_recommendation_service.UserMcpInstallRepository"
            ) as mock_mcp_install:
                with patch(
                    "app.services.capability_recommendation_service.McpServerRepository"
                ) as mock_mcp_server:
                    with patch(
                        "app.services.capability_recommendation_service.UserSkillInstallRepository"
                    ) as mock_skill_install:
                        with patch(
                            "app.services.capability_recommendation_service.SkillRepository"
                        ) as mock_skill_repo:
                            mock_mcp_install.list_by_user.return_value = []
                            mock_mcp_server.list_visible.return_value = []
                            mock_skill_install.list_by_user.return_value = []
                            mock_skill_repo.list_visible.return_value = []

                            service = CapabilityRecommendationService()
                            result = service._build_candidates(self.db, self.user_id)

                            self.assertEqual(result, [])

    def test_with_mcp_candidates(self) -> None:
        with patch(
            "app.services.capability_recommendation_service.get_settings"
        ) as mock_settings:
            settings = MagicMock()
            settings.siliconflow_api_key = "test-key"
            mock_settings.return_value = settings

            with patch(
                "app.services.capability_recommendation_service.UserMcpInstallRepository"
            ) as mock_mcp_install:
                with patch(
                    "app.services.capability_recommendation_service.McpServerRepository"
                ) as mock_mcp_server:
                    with patch(
                        "app.services.capability_recommendation_service.UserSkillInstallRepository"
                    ) as mock_skill_install:
                        with patch(
                            "app.services.capability_recommendation_service.SkillRepository"
                        ) as mock_skill_repo:
                            # Mock MCP install
                            mcp_install = MagicMock()
                            mcp_install.server_id = 1
                            mcp_install.enabled = True
                            mock_mcp_install.list_by_user.return_value = [mcp_install]

                            # Mock MCP server
                            server = MagicMock()
                            server.id = 1
                            server.name = "test-server"
                            server.description = "Test description"
                            server.scope = "system"
                            mock_mcp_server.list_visible.return_value = [server]

                            # No skills
                            mock_skill_install.list_by_user.return_value = []
                            mock_skill_repo.list_visible.return_value = []

                            service = CapabilityRecommendationService()
                            result = service._build_candidates(self.db, self.user_id)

                            self.assertEqual(len(result), 1)
                            self.assertEqual(result[0].type, "mcp")
                            self.assertEqual(result[0].name, "test-server")

    def test_skips_mcp_without_install(self) -> None:
        with patch(
            "app.services.capability_recommendation_service.get_settings"
        ) as mock_settings:
            settings = MagicMock()
            settings.siliconflow_api_key = "test-key"
            mock_settings.return_value = settings

            with patch(
                "app.services.capability_recommendation_service.UserMcpInstallRepository"
            ) as mock_mcp_install:
                with patch(
                    "app.services.capability_recommendation_service.McpServerRepository"
                ) as mock_mcp_server:
                    with patch(
                        "app.services.capability_recommendation_service.UserSkillInstallRepository"
                    ) as mock_skill_install:
                        with patch(
                            "app.services.capability_recommendation_service.SkillRepository"
                        ) as mock_skill_repo:
                            # No MCP installs
                            mock_mcp_install.list_by_user.return_value = []

                            # MCP server exists
                            server = MagicMock()
                            server.id = 1
                            mock_mcp_server.list_visible.return_value = [server]

                            # No skills
                            mock_skill_install.list_by_user.return_value = []
                            mock_skill_repo.list_visible.return_value = []

                            service = CapabilityRecommendationService()
                            result = service._build_candidates(self.db, self.user_id)

                            # Should skip server without install
                            self.assertEqual(len(result), 0)

    def test_with_skill_candidates(self) -> None:
        with patch(
            "app.services.capability_recommendation_service.get_settings"
        ) as mock_settings:
            settings = MagicMock()
            settings.siliconflow_api_key = "test-key"
            mock_settings.return_value = settings

            with patch(
                "app.services.capability_recommendation_service.UserMcpInstallRepository"
            ) as mock_mcp_install:
                with patch(
                    "app.services.capability_recommendation_service.McpServerRepository"
                ) as mock_mcp_server:
                    with patch(
                        "app.services.capability_recommendation_service.UserSkillInstallRepository"
                    ) as mock_skill_install:
                        with patch(
                            "app.services.capability_recommendation_service.SkillRepository"
                        ) as mock_skill_repo:
                            # No MCP
                            mock_mcp_install.list_by_user.return_value = []
                            mock_mcp_server.list_visible.return_value = []

                            # Mock skill install
                            skill_install = MagicMock()
                            skill_install.skill_id = 1
                            skill_install.enabled = False
                            mock_skill_install.list_by_user.return_value = [
                                skill_install
                            ]

                            # Mock skill
                            skill = MagicMock()
                            skill.id = 1
                            skill.name = "test-skill"
                            skill.description = "Skill description"
                            skill.source = {"repo": "owner/repo"}
                            mock_skill_repo.list_visible.return_value = [skill]

                            service = CapabilityRecommendationService()
                            result = service._build_candidates(self.db, self.user_id)

                            self.assertEqual(len(result), 1)
                            self.assertEqual(result[0].type, "skill")
                            self.assertEqual(result[0].name, "test-skill")
                            self.assertFalse(result[0].default_enabled)


class TestCapabilityRecommendationServiceRecommend(unittest.IsolatedAsyncioTestCase):
    """Test recommend method."""

    def setUp(self) -> None:
        self.db = MagicMock()
        self.user_id = "user-123"

    async def test_empty_query(self) -> None:
        with patch(
            "app.services.capability_recommendation_service.get_settings"
        ) as mock_settings:
            settings = MagicMock()
            mock_settings.return_value = settings

            service = CapabilityRecommendationService()
            result = await service.recommend(self.db, user_id=self.user_id, query="")

            self.assertEqual(result.query, "")
            self.assertEqual(result.items, [])

    async def test_whitespace_query(self) -> None:
        with patch(
            "app.services.capability_recommendation_service.get_settings"
        ) as mock_settings:
            settings = MagicMock()
            mock_settings.return_value = settings

            service = CapabilityRecommendationService()
            result = await service.recommend(self.db, user_id=self.user_id, query="   ")

            self.assertEqual(result.query, "")
            self.assertEqual(result.items, [])

    async def test_no_candidates(self) -> None:
        with patch(
            "app.services.capability_recommendation_service.get_settings"
        ) as mock_settings:
            settings = MagicMock()
            mock_settings.return_value = settings

            with patch.object(
                CapabilityRecommendationService, "_build_candidates", return_value=[]
            ):
                service = CapabilityRecommendationService()
                result = await service.recommend(
                    self.db, user_id=self.user_id, query="test query"
                )

                self.assertEqual(result.query, "test query")
                self.assertEqual(result.items, [])


class TestCapabilityRecommendationServiceRecommendAsync(
    unittest.IsolatedAsyncioTestCase
):
    """Test recommend method async scenarios."""

    def setUp(self) -> None:
        self.db = MagicMock()
        self.user_id = "user-123"

    async def test_recommend_success(self) -> None:
        """Test successful recommendation."""
        with patch(
            "app.services.capability_recommendation_service.get_settings"
        ) as mock_settings:
            settings = MagicMock()
            settings.siliconflow_api_key = "test-key"
            settings.siliconflow_base_url = "https://api.example.com"
            settings.siliconflow_rerank_model = "model"
            settings.siliconflow_timeout_seconds = 30
            mock_settings.return_value = settings

            # Create a mock candidate
            candidate = _CapabilityCandidate(
                type="mcp",
                id=1,
                name="test-server",
                description="Test",
                default_enabled=True,
                document="Type: MCP server\nName: test-server",
            )

            with patch.object(
                CapabilityRecommendationService,
                "_build_candidates",
                return_value=[candidate],
            ):
                with patch("httpx.AsyncClient") as mock_client:
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        "results": [{"index": 0, "relevance_score": 0.9}]
                    }

                    mock_client_instance = MagicMock()
                    mock_client_instance.post = AsyncMock(return_value=mock_response)
                    mock_client_instance.__aenter__ = AsyncMock(
                        return_value=mock_client_instance
                    )
                    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
                    mock_client.return_value = mock_client_instance

                    service = CapabilityRecommendationService()
                    result = await service.recommend(
                        self.db, user_id=self.user_id, query="test query"
                    )

                    self.assertEqual(result.query, "test query")
                    self.assertEqual(len(result.items), 1)
                    self.assertEqual(result.items[0].name, "test-server")

    async def test_recommend_timeout(self) -> None:
        """Test recommendation timeout."""
        with patch(
            "app.services.capability_recommendation_service.get_settings"
        ) as mock_settings:
            settings = MagicMock()
            settings.siliconflow_api_key = "test-key"
            settings.siliconflow_base_url = "https://api.example.com"
            settings.siliconflow_rerank_model = "model"
            settings.siliconflow_timeout_seconds = 30
            mock_settings.return_value = settings

            candidate = _CapabilityCandidate(
                type="mcp",
                id=1,
                name="test-server",
                description="Test",
                default_enabled=True,
                document="Type: MCP server",
            )

            with patch.object(
                CapabilityRecommendationService,
                "_build_candidates",
                return_value=[candidate],
            ):
                with patch("httpx.AsyncClient") as mock_client:
                    mock_client_instance = MagicMock()
                    mock_client_instance.post = AsyncMock(
                        side_effect=httpx.TimeoutException("timeout")
                    )
                    mock_client_instance.__aenter__ = AsyncMock(
                        return_value=mock_client_instance
                    )
                    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
                    mock_client.return_value = mock_client_instance

                    service = CapabilityRecommendationService()

                    with self.assertRaises(AppException) as ctx:
                        await service.recommend(
                            self.db, user_id=self.user_id, query="test query"
                        )

                    self.assertEqual(
                        ctx.exception.error_code, ErrorCode.EXTERNAL_SERVICE_ERROR
                    )

    async def test_recommend_http_error(self) -> None:
        """Test recommendation HTTP error."""
        with patch(
            "app.services.capability_recommendation_service.get_settings"
        ) as mock_settings:
            settings = MagicMock()
            settings.siliconflow_api_key = "test-key"
            settings.siliconflow_base_url = "https://api.example.com"
            settings.siliconflow_rerank_model = "model"
            settings.siliconflow_timeout_seconds = 30
            mock_settings.return_value = settings

            candidate = _CapabilityCandidate(
                type="mcp",
                id=1,
                name="test-server",
                description="Test",
                default_enabled=True,
                document="Type: MCP server",
            )

            with patch.object(
                CapabilityRecommendationService,
                "_build_candidates",
                return_value=[candidate],
            ):
                with patch("httpx.AsyncClient") as mock_client:
                    mock_client_instance = MagicMock()
                    mock_client_instance.post = AsyncMock(
                        side_effect=httpx.HTTPError("connection error")
                    )
                    mock_client_instance.__aenter__ = AsyncMock(
                        return_value=mock_client_instance
                    )
                    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
                    mock_client.return_value = mock_client_instance

                    service = CapabilityRecommendationService()

                    with self.assertRaises(AppException) as ctx:
                        await service.recommend(
                            self.db, user_id=self.user_id, query="test query"
                        )

                    self.assertEqual(
                        ctx.exception.error_code, ErrorCode.EXTERNAL_SERVICE_ERROR
                    )

    async def test_recommend_api_error(self) -> None:
        """Test recommendation API error response."""
        with patch(
            "app.services.capability_recommendation_service.get_settings"
        ) as mock_settings:
            settings = MagicMock()
            settings.siliconflow_api_key = "test-key"
            settings.siliconflow_base_url = "https://api.example.com"
            settings.siliconflow_rerank_model = "model"
            settings.siliconflow_timeout_seconds = 30
            mock_settings.return_value = settings

            candidate = _CapabilityCandidate(
                type="mcp",
                id=1,
                name="test-server",
                description="Test",
                default_enabled=True,
                document="Type: MCP server",
            )

            with patch.object(
                CapabilityRecommendationService,
                "_build_candidates",
                return_value=[candidate],
            ):
                with patch("httpx.AsyncClient") as mock_client:
                    mock_response = MagicMock()
                    mock_response.status_code = 500
                    mock_response.json.return_value = {"message": "Internal error"}
                    mock_response.text = "Internal error"

                    mock_client_instance = MagicMock()
                    mock_client_instance.post = AsyncMock(return_value=mock_response)
                    mock_client_instance.__aenter__ = AsyncMock(
                        return_value=mock_client_instance
                    )
                    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
                    mock_client.return_value = mock_client_instance

                    service = CapabilityRecommendationService()

                    with self.assertRaises(AppException) as ctx:
                        await service.recommend(
                            self.db, user_id=self.user_id, query="test query"
                        )

                    self.assertEqual(
                        ctx.exception.error_code, ErrorCode.EXTERNAL_SERVICE_ERROR
                    )

    async def test_recommend_invalid_json(self) -> None:
        """Test recommendation invalid JSON response."""
        with patch(
            "app.services.capability_recommendation_service.get_settings"
        ) as mock_settings:
            settings = MagicMock()
            settings.siliconflow_api_key = "test-key"
            settings.siliconflow_base_url = "https://api.example.com"
            settings.siliconflow_rerank_model = "model"
            settings.siliconflow_timeout_seconds = 30
            mock_settings.return_value = settings

            candidate = _CapabilityCandidate(
                type="mcp",
                id=1,
                name="test-server",
                description="Test",
                default_enabled=True,
                document="Type: MCP server",
            )

            with patch.object(
                CapabilityRecommendationService,
                "_build_candidates",
                return_value=[candidate],
            ):
                with patch("httpx.AsyncClient") as mock_client:
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_response.json.side_effect = ValueError("invalid json")

                    mock_client_instance = MagicMock()
                    mock_client_instance.post = AsyncMock(return_value=mock_response)
                    mock_client_instance.__aenter__ = AsyncMock(
                        return_value=mock_client_instance
                    )
                    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
                    mock_client.return_value = mock_client_instance

                    service = CapabilityRecommendationService()

                    with self.assertRaises(AppException) as ctx:
                        await service.recommend(
                            self.db, user_id=self.user_id, query="test query"
                        )

                    self.assertEqual(
                        ctx.exception.error_code, ErrorCode.EXTERNAL_SERVICE_ERROR
                    )

    async def test_recommend_no_results(self) -> None:
        """Test recommendation with no results in response."""
        with patch(
            "app.services.capability_recommendation_service.get_settings"
        ) as mock_settings:
            settings = MagicMock()
            settings.siliconflow_api_key = "test-key"
            settings.siliconflow_base_url = "https://api.example.com"
            settings.siliconflow_rerank_model = "model"
            settings.siliconflow_timeout_seconds = 30
            mock_settings.return_value = settings

            candidate = _CapabilityCandidate(
                type="mcp",
                id=1,
                name="test-server",
                description="Test",
                default_enabled=True,
                document="Type: MCP server",
            )

            with patch.object(
                CapabilityRecommendationService,
                "_build_candidates",
                return_value=[candidate],
            ):
                with patch("httpx.AsyncClient") as mock_client:
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {}

                    mock_client_instance = MagicMock()
                    mock_client_instance.post = AsyncMock(return_value=mock_response)
                    mock_client_instance.__aenter__ = AsyncMock(
                        return_value=mock_client_instance
                    )
                    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
                    mock_client.return_value = mock_client_instance

                    service = CapabilityRecommendationService()
                    result = await service.recommend(
                        self.db, user_id=self.user_id, query="test query"
                    )

                    self.assertEqual(result.items, [])

    async def test_recommend_with_limit(self) -> None:
        """Test recommendation respects limit."""
        with patch(
            "app.services.capability_recommendation_service.get_settings"
        ) as mock_settings:
            settings = MagicMock()
            settings.siliconflow_api_key = "test-key"
            settings.siliconflow_base_url = "https://api.example.com"
            settings.siliconflow_rerank_model = "model"
            settings.siliconflow_timeout_seconds = 30
            mock_settings.return_value = settings

            candidates = [
                _CapabilityCandidate(
                    type="mcp",
                    id=i,
                    name=f"server-{i}",
                    description="Test",
                    default_enabled=True,
                    document=f"Type: MCP server\nName: server-{i}",
                )
                for i in range(5)
            ]

            with patch.object(
                CapabilityRecommendationService,
                "_build_candidates",
                return_value=candidates,
            ):
                with patch("httpx.AsyncClient") as mock_client:
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        "results": [
                            {"index": i, "relevance_score": 0.9 - i * 0.1}
                            for i in range(5)
                        ]
                    }

                    mock_client_instance = MagicMock()
                    mock_client_instance.post = AsyncMock(return_value=mock_response)
                    mock_client_instance.__aenter__ = AsyncMock(
                        return_value=mock_client_instance
                    )
                    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
                    mock_client.return_value = mock_client_instance

                    service = CapabilityRecommendationService()
                    result = await service.recommend(
                        self.db, user_id=self.user_id, query="test query", limit=2
                    )

                    self.assertEqual(len(result.items), 2)

    async def test_recommend_invalid_index(self) -> None:
        """Test recommendation handles invalid index."""
        with patch(
            "app.services.capability_recommendation_service.get_settings"
        ) as mock_settings:
            settings = MagicMock()
            settings.siliconflow_api_key = "test-key"
            settings.siliconflow_base_url = "https://api.example.com"
            settings.siliconflow_rerank_model = "model"
            settings.siliconflow_timeout_seconds = 30
            mock_settings.return_value = settings

            candidate = _CapabilityCandidate(
                type="mcp",
                id=1,
                name="test-server",
                description="Test",
                default_enabled=True,
                document="Type: MCP server",
            )

            with patch.object(
                CapabilityRecommendationService,
                "_build_candidates",
                return_value=[candidate],
            ):
                with patch("httpx.AsyncClient") as mock_client:
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        "results": [{"index": 99, "relevance_score": 0.9}]
                    }

                    mock_client_instance = MagicMock()
                    mock_client_instance.post = AsyncMock(return_value=mock_response)
                    mock_client_instance.__aenter__ = AsyncMock(
                        return_value=mock_client_instance
                    )
                    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
                    mock_client.return_value = mock_client_instance

                    service = CapabilityRecommendationService()
                    result = await service.recommend(
                        self.db, user_id=self.user_id, query="test query"
                    )

                    self.assertEqual(result.items, [])

    async def test_recommend_int_score_converted_to_float(self) -> None:
        """Test recommendation converts int score to float."""
        with patch(
            "app.services.capability_recommendation_service.get_settings"
        ) as mock_settings:
            settings = MagicMock()
            settings.siliconflow_api_key = "test-key"
            settings.siliconflow_base_url = "https://api.example.com"
            settings.siliconflow_rerank_model = "model"
            settings.siliconflow_timeout_seconds = 30
            mock_settings.return_value = settings

            candidate = _CapabilityCandidate(
                type="mcp",
                id=1,
                name="test-server",
                description="Test",
                default_enabled=True,
                document="Type: MCP server",
            )

            with patch.object(
                CapabilityRecommendationService,
                "_build_candidates",
                return_value=[candidate],
            ):
                with patch("httpx.AsyncClient") as mock_client:
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        "results": [{"index": 0, "relevance_score": 1}]
                    }

                    mock_client_instance = MagicMock()
                    mock_client_instance.post = AsyncMock(return_value=mock_response)
                    mock_client_instance.__aenter__ = AsyncMock(
                        return_value=mock_client_instance
                    )
                    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
                    mock_client.return_value = mock_client_instance

                    service = CapabilityRecommendationService()
                    result = await service.recommend(
                        self.db, user_id=self.user_id, query="test query"
                    )

                    self.assertEqual(result.items[0].score, 1.0)
                    self.assertIsInstance(result.items[0].score, float)

    async def test_recommend_invalid_score_type(self) -> None:
        """Test recommendation handles invalid score type."""
        with patch(
            "app.services.capability_recommendation_service.get_settings"
        ) as mock_settings:
            settings = MagicMock()
            settings.siliconflow_api_key = "test-key"
            settings.siliconflow_base_url = "https://api.example.com"
            settings.siliconflow_rerank_model = "model"
            settings.siliconflow_timeout_seconds = 30
            mock_settings.return_value = settings

            candidate = _CapabilityCandidate(
                type="mcp",
                id=1,
                name="test-server",
                description="Test",
                default_enabled=True,
                document="Type: MCP server",
            )

            with patch.object(
                CapabilityRecommendationService,
                "_build_candidates",
                return_value=[candidate],
            ):
                with patch("httpx.AsyncClient") as mock_client:
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        "results": [{"index": 0, "relevance_score": "invalid"}]
                    }

                    mock_client_instance = MagicMock()
                    mock_client_instance.post = AsyncMock(return_value=mock_response)
                    mock_client_instance.__aenter__ = AsyncMock(
                        return_value=mock_client_instance
                    )
                    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
                    mock_client.return_value = mock_client_instance

                    service = CapabilityRecommendationService()
                    result = await service.recommend(
                        self.db, user_id=self.user_id, query="test query"
                    )

                    self.assertEqual(result.items[0].score, 0.0)

    async def test_recommend_non_dict_item(self) -> None:
        """Test recommendation handles non-dict items in results."""
        with patch(
            "app.services.capability_recommendation_service.get_settings"
        ) as mock_settings:
            settings = MagicMock()
            settings.siliconflow_api_key = "test-key"
            settings.siliconflow_base_url = "https://api.example.com"
            settings.siliconflow_rerank_model = "model"
            settings.siliconflow_timeout_seconds = 30
            mock_settings.return_value = settings

            candidate = _CapabilityCandidate(
                type="mcp",
                id=1,
                name="test-server",
                description="Test",
                default_enabled=True,
                document="Type: MCP server",
            )

            with patch.object(
                CapabilityRecommendationService,
                "_build_candidates",
                return_value=[candidate],
            ):
                with patch("httpx.AsyncClient") as mock_client:
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        "results": ["not a dict", {"index": 0, "relevance_score": 0.9}]
                    }

                    mock_client_instance = MagicMock()
                    mock_client_instance.post = AsyncMock(return_value=mock_response)
                    mock_client_instance.__aenter__ = AsyncMock(
                        return_value=mock_client_instance
                    )
                    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
                    mock_client.return_value = mock_client_instance

                    service = CapabilityRecommendationService()
                    result = await service.recommend(
                        self.db, user_id=self.user_id, query="test query"
                    )

                    self.assertEqual(len(result.items), 1)

    async def test_recommend_non_int_index(self) -> None:
        """Test recommendation handles non-int index."""
        with patch(
            "app.services.capability_recommendation_service.get_settings"
        ) as mock_settings:
            settings = MagicMock()
            settings.siliconflow_api_key = "test-key"
            settings.siliconflow_base_url = "https://api.example.com"
            settings.siliconflow_rerank_model = "model"
            settings.siliconflow_timeout_seconds = 30
            mock_settings.return_value = settings

            candidate = _CapabilityCandidate(
                type="mcp",
                id=1,
                name="test-server",
                description="Test",
                default_enabled=True,
                document="Type: MCP server",
            )

            with patch.object(
                CapabilityRecommendationService,
                "_build_candidates",
                return_value=[candidate],
            ):
                with patch("httpx.AsyncClient") as mock_client:
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        "results": [{"index": "zero", "relevance_score": 0.9}]
                    }

                    mock_client_instance = MagicMock()
                    mock_client_instance.post = AsyncMock(return_value=mock_response)
                    mock_client_instance.__aenter__ = AsyncMock(
                        return_value=mock_client_instance
                    )
                    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
                    mock_client.return_value = mock_client_instance

                    service = CapabilityRecommendationService()
                    result = await service.recommend(
                        self.db, user_id=self.user_id, query="test query"
                    )

                    self.assertEqual(result.items, [])


class TestCapabilityRecommendationServiceBuildCandidatesMore(unittest.TestCase):
    """Test _build_candidates method edge cases."""

    def setUp(self) -> None:
        self.db = MagicMock()
        self.user_id = "user-123"

    def test_skips_skill_without_install(self) -> None:
        with patch(
            "app.services.capability_recommendation_service.get_settings"
        ) as mock_settings:
            settings = MagicMock()
            settings.siliconflow_api_key = "test-key"
            mock_settings.return_value = settings

            with patch(
                "app.services.capability_recommendation_service.UserMcpInstallRepository"
            ) as mock_mcp_install:
                with patch(
                    "app.services.capability_recommendation_service.McpServerRepository"
                ) as mock_mcp_server:
                    with patch(
                        "app.services.capability_recommendation_service.UserSkillInstallRepository"
                    ) as mock_skill_install:
                        with patch(
                            "app.services.capability_recommendation_service.SkillRepository"
                        ) as mock_skill_repo:
                            # No MCP
                            mock_mcp_install.list_by_user.return_value = []
                            mock_mcp_server.list_visible.return_value = []

                            # No skill installs
                            mock_skill_install.list_by_user.return_value = []

                            # Skill exists
                            skill = MagicMock()
                            skill.id = 1
                            mock_skill_repo.list_visible.return_value = [skill]

                            service = CapabilityRecommendationService()
                            result = service._build_candidates(self.db, self.user_id)

                            # Should skip skill without install
                            self.assertEqual(len(result), 0)


if __name__ == "__main__":
    unittest.main()
