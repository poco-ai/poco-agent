import unittest
from typing import Any

from app.utils.workspace_export import (
    build_workspace_file_nodes_from_export,
    create_workspace_preview_token,
    resolve_export_object_key,
    verify_workspace_preview_token,
)


class FakeStorageService:
    def __init__(self, manifest: dict[str, Any]) -> None:
        self.manifest = manifest
        self.presigned_keys: list[str] = []

    def get_manifest(self, key: str) -> dict[str, Any]:
        return self.manifest

    def presign_get(
        self,
        key: str,
        *,
        response_content_disposition: str | None = None,
        response_content_type: str | None = None,
    ) -> str:
        self.presigned_keys.append(key)
        return f"https://storage.test/{key}"


class WorkspaceExportUtilsTests(unittest.TestCase):
    def test_build_nodes_can_use_same_origin_file_urls(self) -> None:
        storage = FakeStorageService(
            {
                "files": [
                    {
                        "path": "deck/index.html",
                        "key": "workspaces/user/session/files/deck/index.html",
                        "mimeType": "text/html",
                    },
                    {
                        "path": "deck/slides/05-instructions.html",
                        "key": "workspaces/user/session/files/deck/slides/05-instructions.html",
                        "mimeType": "text/html",
                    },
                ]
            }
        )

        nodes = build_workspace_file_nodes_from_export(
            manifest_key="workspaces/user/session/manifest.json",
            workspace_files_prefix="workspaces/user/session/files",
            storage_service=storage,
            file_url_builder=lambda path: (
                f"/api/v1/sessions/session/workspace/raw{path}"
            ),
        )

        deck = nodes[0]
        self.assertEqual(deck.type, "folder")
        index_file = next(
            child for child in deck.children or [] if child.path == "/deck/index.html"
        )
        self.assertEqual(index_file.path, "/deck/index.html")
        self.assertEqual(
            index_file.url,
            "/api/v1/sessions/session/workspace/raw/deck/index.html",
        )
        self.assertEqual(storage.presigned_keys, [])

    def test_resolve_export_object_key_falls_back_to_workspace_prefix(self) -> None:
        self.assertEqual(
            resolve_export_object_key(
                file_entry={"path": "deck/index.html"},
                workspace_files_prefix="workspaces/user/session/files",
            ),
            "workspaces/user/session/files/deck/index.html",
        )

    def test_workspace_preview_token_is_scoped(self) -> None:
        token = create_workspace_preview_token(
            scope="session",
            scope_id="session-1",
        )

        self.assertTrue(
            verify_workspace_preview_token(
                token,
                scope="session",
                scope_id="session-1",
            )
        )
        self.assertFalse(
            verify_workspace_preview_token(
                token,
                scope="run",
                scope_id="session-1",
            )
        )


if __name__ == "__main__":
    unittest.main()
