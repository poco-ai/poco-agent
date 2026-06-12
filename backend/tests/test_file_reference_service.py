import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.core.errors.exceptions import AppException
from app.schemas.input_file import InputFile
from app.services.file_reference_service import FileReferenceService


class FakeStorageService:
    def __init__(self, manifest: dict) -> None:
        self.manifest = manifest

    def get_manifest(self, key: str) -> dict:
        return self.manifest


class FileReferenceServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session_id = uuid.uuid4()
        self.db = MagicMock()
        self.db_session = SimpleNamespace(
            id=self.session_id,
            workspace_export_status="ready",
            workspace_manifest_key="workspaces/user/session/manifest.json",
            workspace_files_prefix="workspaces/user/session/files",
        )

    def test_validates_workspace_reference_without_promoting_to_input(self) -> None:
        service = FileReferenceService(
            storage_service=FakeStorageService(
                {
                    "files": [
                        {
                            "path": "reports/summary.md",
                            "key": "workspaces/user/session/files/reports/summary.md",
                            "size": 42,
                            "mimeType": "text/markdown",
                        }
                    ]
                }
            )
        )

        with patch.object(
            FileReferenceService, "_collect_historical_inputs", return_value={}
        ):
            input_files, references = service.resolve_for_run(
                self.db,
                self.db_session,
                [
                    {
                        "id": "ref-1",
                        "kind": "workspace_file",
                        "sessionId": str(self.session_id),
                        "path": "/reports/summary.md",
                        "insertedText": "#summary.md",
                        "displayName": "summary.md",
                    }
                ],
                [],
                prompt="read #summary.md",
            )

        self.assertEqual(input_files, [])
        self.assertEqual(references[0]["kind"], "workspace_file")
        self.assertEqual(references[0]["path"], "/reports/summary.md")

    def test_rejects_missing_workspace_reference_path(self) -> None:
        service = FileReferenceService(storage_service=FakeStorageService({"files": []}))

        with (
            patch.object(
                FileReferenceService, "_collect_historical_inputs", return_value={}
            ),
            self.assertRaises(AppException),
        ):
            service.resolve_for_run(
                self.db,
                self.db_session,
                [
                    {
                        "id": "ref-1",
                        "kind": "workspace_file",
                        "sessionId": str(self.session_id),
                        "path": "/missing.md",
                        "insertedText": "#missing.md",
                        "displayName": "missing.md",
                    }
                ],
                [],
            )

    def test_promotes_historical_input_file_reference(self) -> None:
        historical_input = InputFile(
            name="guide.md",
            source="attachments/user/file",
            size=12,
            content_type="text/markdown",
        )
        service = FileReferenceService()

        with patch.object(
            FileReferenceService,
            "_collect_historical_inputs",
            return_value={"attachments/user/file": historical_input},
        ):
            input_files, references = service.resolve_for_run(
                self.db,
                self.db_session,
                [
                    {
                        "id": "ref-1",
                        "kind": "input_file",
                        "source": "attachments/user/file",
                        "insertedText": "#guide.md",
                        "displayName": "guide.md",
                    }
                ],
                [],
                prompt="check #guide.md",
            )

        self.assertEqual(input_files, [historical_input])
        self.assertEqual(references[0]["kind"], "input_file")


if __name__ == "__main__":
    unittest.main()
