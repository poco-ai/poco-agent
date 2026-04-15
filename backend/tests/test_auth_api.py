import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.settings import get_settings
from app.main import create_app


class AuthApiTests(unittest.TestCase):
    def setUp(self) -> None:
        get_settings.cache_clear()

    def tearDown(self) -> None:
        get_settings.cache_clear()

    def test_auth_config_returns_runtime_auth_settings(self) -> None:
        with patch.dict(
            os.environ,
            {
                "AUTH_MODE": "oauth_required",
                "WORKSPACE_FEATURES_ENABLED": "true",
                "GOOGLE_CLIENT_ID": "google-client",
                "GOOGLE_CLIENT_SECRET": "google-secret",
                "GITHUB_CLIENT_ID": "github-client",
                "GITHUB_CLIENT_SECRET": "github-secret",
                "BOOTSTRAP_ON_STARTUP": "false",
            },
            clear=False,
        ):
            app = create_app()
            client = TestClient(app)

            response = client.get("/api/v1/auth/config")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["auth_mode"], "oauth_required")
        self.assertTrue(body["data"]["login_required"])
        self.assertTrue(body["data"]["workspace_features_enabled"])
        self.assertEqual(body["data"]["providers"], ["google", "github"])


if __name__ == "__main__":
    unittest.main()
