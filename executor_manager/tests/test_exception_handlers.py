"""Tests for app/core/errors/exception_handlers.py."""

import unittest

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException


class TestExceptionHandlers(unittest.TestCase):
    """Test exception handlers."""

    def test_app_exception_handler(self) -> None:
        """Test AppException handler returns correct response."""
        from app.core.errors.exception_handlers import setup_exception_handlers

        app = FastAPI()
        setup_exception_handlers(app, debug=True)

        @app.get("/test-app-exception")
        def raise_app_exception():  # noqa: F841
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message="Resource not found",
                details={"id": "123"},
            )

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test-app-exception")

        assert response.status_code == 400
        data = response.json()
        assert data["code"] == ErrorCode.NOT_FOUND.code
        assert data["message"] == "Resource not found"
        assert data["data"]["id"] == "123"

    def test_http_exception_handler_string_detail(self) -> None:
        """Test HTTPException handler with string detail."""
        from app.core.errors.exception_handlers import setup_exception_handlers

        app = FastAPI()
        setup_exception_handlers(app, debug=True)

        @app.get("/test-http-exception")
        def raise_http_exception():  # noqa: F841
            raise HTTPException(status_code=404, detail="Not found")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test-http-exception")

        assert response.status_code == 404
        data = response.json()
        assert data["code"] == 404
        assert data["message"] == "Not found"

    def test_http_exception_handler_dict_detail(self) -> None:
        """Test HTTPException handler with dict detail."""
        from app.core.errors.exception_handlers import setup_exception_handlers

        app = FastAPI()
        setup_exception_handlers(app, debug=True)

        @app.get("/test-http-exception-dict")
        def raise_http_exception():  # noqa: F841
            raise HTTPException(
                status_code=403, detail={"reason": "Forbidden", "code": "AUTH_001"}
            )

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test-http-exception-dict")

        assert response.status_code == 403
        data = response.json()
        assert data["code"] == 403
        assert data["data"]["reason"] == "Forbidden"

    def test_general_exception_handler_debug_true(self) -> None:
        """Test general exception handler with debug=True includes details."""
        from app.core.errors.exception_handlers import setup_exception_handlers

        app = FastAPI()
        setup_exception_handlers(app, debug=True)

        @app.get("/test-general-exception")
        def raise_general_exception():  # noqa: F841
            raise ValueError("Something went wrong")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test-general-exception")

        assert response.status_code == 500
        data = response.json()
        assert data["code"] == ErrorCode.INTERNAL_ERROR.code
        assert data["data"]["type"] == "ValueError"
        assert data["data"]["message"] == "Something went wrong"

    def test_general_exception_handler_debug_false(self) -> None:
        """Test general exception handler with debug=False hides details."""
        from app.core.errors.exception_handlers import setup_exception_handlers

        app = FastAPI()
        setup_exception_handlers(app, debug=False)

        @app.get("/test-general-exception-no-debug")
        def raise_general_exception():  # noqa: F841
            raise ValueError("Secret error")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test-general-exception-no-debug")

        assert response.status_code == 500
        data = response.json()
        assert data["code"] == ErrorCode.INTERNAL_ERROR.code
        assert data["data"] is None


if __name__ == "__main__":
    unittest.main()
