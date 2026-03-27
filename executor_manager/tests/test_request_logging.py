"""Tests for app/core/middleware/request_logging.py."""

import logging
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware


class TestRequestLoggingMiddleware(unittest.TestCase):
    """Test RequestLoggingMiddleware."""

    def setUp(self) -> None:
        # Reset logging state
        self.logger = logging.getLogger("app.http")
        self.original_handlers = self.logger.handlers[:]
        self.logger.handlers.clear()

    def tearDown(self) -> None:
        self.logger.handlers = self.original_handlers

    def test_skips_configured_paths(self) -> None:
        """Test middleware skips logging for configured paths."""
        from app.core.middleware.request_logging import RequestLoggingMiddleware

        app = FastAPI()
        middleware = RequestLoggingMiddleware(
            app, skip_paths={"/health", "/docs", "/openapi.json"}
        )

        # Verify skip_paths is set correctly
        assert "/health" in middleware._skip_paths
        assert "/docs" in middleware._skip_paths
        assert "/openapi.json" in middleware._skip_paths

    def test_skips_health_endpoint(self) -> None:
        """Test middleware skips /health endpoint."""
        from app.core.middleware.request_logging import RequestLoggingMiddleware

        app = FastAPI()

        @app.get("/health")
        def health():
            return {"status": "ok"}

        # Add middleware
        app.add_middleware(
            BaseHTTPMiddleware,
            dispatch=RequestLoggingMiddleware(app).dispatch,
        )

        with patch.object(
            RequestLoggingMiddleware,
            "__init__",
            lambda self, app, **kw: object.__init__(self),
        ):
            client = TestClient(app)
            response = client.get("/health")
            assert response.status_code == 200

    def test_logs_request_with_long_user_agent(self) -> None:
        """Test middleware truncates long user-agent strings."""
        from app.core.middleware.request_logging import RequestLoggingMiddleware

        app = FastAPI()

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        # Create a very long user-agent string
        long_ua = "Mozilla/5.0 " + "x" * 200

        middleware = RequestLoggingMiddleware(app)
        app.add_middleware(
            BaseHTTPMiddleware,
            dispatch=middleware.dispatch,
        )

        # Capture log output
        with patch("app.core.middleware.request_logging.logger") as mock_logger:
            client = TestClient(app)
            response = client.get("/test", headers={"user-agent": long_ua})

            assert response.status_code == 200
            # Verify log was called
            mock_logger.log.assert_called_once()
            call_args = mock_logger.log.call_args
            extra = call_args.kwargs.get("extra", {})
            user_agent = extra.get("user_agent", "")
            # Check truncation happened
            assert "...(truncated)" in user_agent or len(user_agent) <= 120

    def test_logs_request_with_normal_user_agent(self) -> None:
        """Test middleware logs normal user-agent without truncation."""
        from app.core.middleware.request_logging import RequestLoggingMiddleware

        app = FastAPI()

        @app.get("/api/test")
        def test_endpoint():
            return {"status": "ok"}

        middleware = RequestLoggingMiddleware(app)
        app.add_middleware(
            BaseHTTPMiddleware,
            dispatch=middleware.dispatch,
        )

        normal_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

        with patch("app.core.middleware.request_logging.logger") as mock_logger:
            client = TestClient(app)
            response = client.get("/api/test", headers={"user-agent": normal_ua})

            assert response.status_code == 200
            mock_logger.log.assert_called_once()
            call_args = mock_logger.log.call_args
            extra = call_args.kwargs.get("extra", {})
            assert extra.get("user_agent") == normal_ua

    def test_logs_different_status_codes_with_correct_level(self) -> None:
        """Test middleware uses correct log level for different status codes."""
        from app.core.middleware.request_logging import RequestLoggingMiddleware

        app = FastAPI()

        @app.get("/error")
        def error_endpoint():
            from fastapi import HTTPException

            raise HTTPException(status_code=500, detail="Server error")

        middleware = RequestLoggingMiddleware(app)
        app.add_middleware(
            BaseHTTPMiddleware,
            dispatch=middleware.dispatch,
        )

        with patch("app.core.middleware.request_logging.logger") as mock_logger:
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/error")

            assert response.status_code == 500
            mock_logger.log.assert_called_once()
            call_args = mock_logger.log.call_args
            level = call_args.args[0]
            assert level == logging.ERROR


if __name__ == "__main__":
    unittest.main()
