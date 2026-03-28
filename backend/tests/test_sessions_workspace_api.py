import asyncio
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from app.services import storage_service as storage_service_module

from unittest.mock import MagicMock, patch
from uuid import uuid4

os.environ["S3_BUCKET"] = "test-bucket"
os.environ["S3_ENDPOINT"] = "http://example.test"
os.environ["S3_ACCESS_KEY"] = "test-access-key"
os.environ["S3_SECRET_KEY"] = "test-secret-key"

_SESSIONS_MODULE_PATH = (
    Path(__file__).resolve().parent.parent / "app" / "api" / "v1" / "sessions.py"
)
_SESSIONS_SPEC = importlib.util.spec_from_file_location(
    "backend_sessions_api_under_test",
    _SESSIONS_MODULE_PATH,
)
assert _SESSIONS_SPEC is not None and _SESSIONS_SPEC.loader is not None


class _DummyStorageService:
    def __init__(self) -> None:
        pass

    def get_manifest(self, key: str) -> dict:
        raise NotImplementedError

    def presign_get(self, *args, **kwargs) -> str:
        raise NotImplementedError


storage_service_module.S3StorageService = _DummyStorageService
sessions_api = importlib.util.module_from_spec(_SESSIONS_SPEC)
sys.modules[_SESSIONS_SPEC.name] = sessions_api
_SESSIONS_SPEC.loader.exec_module(sessions_api)


class SessionWorkspaceApiTests(unittest.TestCase):
    def test_get_session_workspace_files_returns_empty_until_export_ready(self) -> None:
        session_id = uuid4()
        db_session = SimpleNamespace(
            user_id="user-123",
            status="running",
            workspace_export_status="pending",
            workspace_manifest_key="workspaces/user/session/manifest.json",
            workspace_files_prefix="workspaces/user/session/files",
        )

        with (
            patch.object(
                sessions_api.session_service,
                "get_session",
                return_value=db_session,
            ),
            patch.object(sessions_api.storage_service, "get_manifest") as mock_manifest,
        ):
            response = asyncio.run(
                sessions_api.get_session_workspace_files(
                    session_id=session_id,
                    user_id="user-123",
                    db=MagicMock(),
                )
            )

        payload = json.loads(response.body)
        self.assertEqual(payload["data"], [])
        mock_manifest.assert_not_called()

    def test_get_session_workspace_files_builds_urls_when_export_ready(self) -> None:
        session_id = uuid4()
        db_session = SimpleNamespace(
            user_id="user-123",
            status="completed",
            workspace_export_status="ready",
            workspace_manifest_key="workspaces/user/session/manifest.json",
            workspace_files_prefix="workspaces/user/session/files",
        )
        raw_nodes = [
            {
                "id": "/outputs/report.pdf",
                "name": "report.pdf",
                "type": "file",
                "path": "/outputs/report.pdf",
            }
        ]
        manifest_files = [
            {
                "path": "/outputs/report.pdf",
                "key": "workspaces/user/session/files/outputs/report.pdf",
                "mimeType": "application/pdf",
            }
        ]
        built_nodes = [
            {
                "id": "/outputs/report.pdf",
                "name": "report.pdf",
                "type": "file",
                "path": "/outputs/report.pdf",
                "url": "https://example.test/report.pdf",
            }
        ]

        with (
            patch.object(
                sessions_api.session_service,
                "get_session",
                return_value=db_session,
            ),
            patch.object(
                sessions_api.storage_service,
                "get_manifest",
                return_value={"files": manifest_files},
            ),
            patch.object(
                sessions_api,
                "build_nodes_from_manifest",
                return_value=raw_nodes,
            ),
            patch.object(
                sessions_api,
                "extract_manifest_files",
                return_value=manifest_files,
            ),
            patch.object(
                sessions_api.storage_service,
                "presign_get",
                return_value="https://example.test/report.pdf",
            ) as mock_presign,
            patch.object(
                sessions_api,
                "build_workspace_file_nodes",
                return_value=built_nodes,
            ) as mock_build_nodes,
        ):
            response = asyncio.run(
                sessions_api.get_session_workspace_files(
                    session_id=session_id,
                    user_id="user-123",
                    db=MagicMock(),
                )
            )

        payload = json.loads(response.body)
        self.assertEqual(payload["data"], built_nodes)
        mock_presign.assert_called_once()
        mock_build_nodes.assert_called_once()

    def test_get_session_workspace_files_returns_empty_when_run_not_terminal(
        self,
    ) -> None:
        session_id = uuid4()
        db_session = SimpleNamespace(
            user_id="user-123",
            status="pending",
            workspace_export_status="ready",
            workspace_manifest_key="workspaces/user/session/manifest.json",
            workspace_files_prefix="workspaces/user/session/files",
        )

        with (
            patch.object(
                sessions_api.session_service,
                "get_session",
                return_value=db_session,
            ),
            patch.object(sessions_api.storage_service, "get_manifest") as mock_manifest,
        ):
            response = asyncio.run(
                sessions_api.get_session_workspace_files(
                    session_id=session_id,
                    user_id="user-123",
                    db=MagicMock(),
                )
            )

        payload = json.loads(response.body)
        self.assertEqual(payload["data"], [])
        mock_manifest.assert_not_called()

    def test_get_session_workspace_archive_returns_null_until_export_ready(
        self,
    ) -> None:
        session_id = uuid4()
        db_session = SimpleNamespace(
            user_id="user-123",
            status="running",
            workspace_export_status="pending",
            workspace_archive_key="workspaces/user/session/archive.zip",
        )

        with patch.object(
            sessions_api.session_service,
            "get_session",
            return_value=db_session,
        ):
            response = asyncio.run(
                sessions_api.get_session_workspace_archive(
                    session_id=session_id,
                    user_id="user-123",
                    db=MagicMock(),
                )
            )

        payload = json.loads(response.body)
        self.assertIsNone(payload["data"]["url"])

    def test_get_session_workspace_archive_returns_null_when_run_not_terminal(
        self,
    ) -> None:
        session_id = uuid4()
        db_session = SimpleNamespace(
            user_id="user-123",
            status="running",
            workspace_export_status="ready",
            workspace_archive_key="workspaces/user/session/archive.zip",
        )

        with (
            patch.object(
                sessions_api.session_service,
                "get_session",
                return_value=db_session,
            ),
            patch.object(sessions_api.storage_service, "presign_get") as mock_presign,
        ):
            response = asyncio.run(
                sessions_api.get_session_workspace_archive(
                    session_id=session_id,
                    user_id="user-123",
                    db=MagicMock(),
                )
            )

        payload = json.loads(response.body)
        self.assertIsNone(payload["data"]["url"])
        mock_presign.assert_not_called()


if __name__ == "__main__":
    unittest.main()
