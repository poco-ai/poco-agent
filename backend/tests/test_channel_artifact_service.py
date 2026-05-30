import unittest
import uuid
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import UploadFile

from app.models.agent_session import AgentSession
from app.services.channel_artifact_service import ChannelArtifactService


class ChannelArtifactServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = MagicMock()
        self.service = ChannelArtifactService()
        self.session_id = uuid.uuid4()
        self.server_id = uuid.uuid4()
        self.channel_id = uuid.uuid4()
        self.agent_identity_id = uuid.uuid4()
        self.session = AgentSession(
            id=self.session_id,
            user_id="user-1",
            sdk_session_id=None,
            config_snapshot={
                "server_id": str(self.server_id),
                "channel_id": str(self.channel_id),
                "agent_identity_id": str(self.agent_identity_id),
                "agent_runtime_mode": "persistent",
            },
            workspace_files_prefix="workspaces/user-1/session/files",
            workspace_manifest_key="workspaces/user-1/session/manifest.json",
            workspace_export_status="ready",
            status="completed",
        )

    def test_sync_session_workspace_artifacts_publishes_manifest_files(self) -> None:
        manifest = {
            "files": [
                {
                    "path": "plans/rate-limit-plan.md",
                    "key": "workspaces/user-1/session/files/plans/rate-limit-plan.md",
                    "mimeType": "text/markdown",
                    "size": 1200,
                },
                {
                    "path": "notes/api-checklist.txt",
                    "key": "workspaces/user-1/session/files/notes/api-checklist.txt",
                    "mimeType": "text/plain",
                    "size": 200,
                },
            ]
        }

        with (
            patch.object(
                self.service._storage,
                "get_manifest",
                return_value=manifest,
            ),
            patch(
                "app.services.channel_artifact_service.ChannelArtifactRepository.upsert_many"
            ) as upsert_many,
        ):
            count = self.service.sync_session_workspace_artifacts(self.db, self.session)

        self.assertEqual(count, 2)
        upsert_many.assert_called_once()
        rows = upsert_many.call_args.kwargs["artifacts"]
        self.assertEqual(rows[0].channel_id, self.channel_id)
        self.assertEqual(rows[0].agent_identity_id, self.agent_identity_id)
        self.assertEqual(rows[0].logical_path, "/plans/rate-limit-plan.md")
        self.assertEqual(rows[1].display_name, "api-checklist.txt")

    def test_sync_session_workspace_artifacts_skips_private_runtime_paths(self) -> None:
        manifest = {
            "files": [
                {
                    "path": "/agent_state/MEMORY.md",
                    "key": "workspaces/user-1/session/files/agent_state/MEMORY.md",
                    "mimeType": "text/markdown",
                    "size": 1200,
                },
                {
                    "path": "/.poco-local/secrets.txt",
                    "key": "workspaces/user-1/session/files/.poco-local/secrets.txt",
                    "mimeType": "text/plain",
                    "size": 200,
                },
                {
                    "path": "plans/rate-limit-plan.md",
                    "key": "workspaces/user-1/session/files/plans/rate-limit-plan.md",
                    "mimeType": "text/markdown",
                    "size": 1200,
                },
            ]
        }

        with (
            patch.object(
                self.service._storage,
                "get_manifest",
                return_value=manifest,
            ),
            patch(
                "app.services.channel_artifact_service.ChannelArtifactRepository.upsert_many"
            ) as upsert_many,
        ):
            count = self.service.sync_session_workspace_artifacts(self.db, self.session)

        self.assertEqual(count, 1)
        rows = upsert_many.call_args.kwargs["artifacts"]
        self.assertEqual(rows[0].logical_path, "/plans/rate-limit-plan.md")

    def test_list_channel_artifact_nodes_groups_files_by_agent(self) -> None:
        artifacts = [
            SimpleNamespace(
                id=uuid.uuid4(),
                channel_id=self.channel_id,
                agent_identity_id=self.agent_identity_id,
                publisher_user_id=None,
                logical_path="/plans/rate-limit-plan.md",
                display_name="rate-limit-plan.md",
                mime_type="text/markdown",
                object_key="objects/plan.md",
                source_kind="workspace_export",
                source_session_id=self.session_id,
                size_bytes=120,
            )
        ]

        with (
            patch(
                "app.services.channel_artifact_service.ChannelArtifactRepository.list_by_channel",
                return_value=artifacts,
            ),
            patch(
                "app.services.channel_artifact_service.AgentIdentityRepository.get_by_id",
                return_value=SimpleNamespace(
                    id=self.agent_identity_id,
                    display_name="api-specialist",
                    handle="api-specialist",
                ),
            ),
            patch.object(
                self.service._storage,
                "presign_get",
                return_value="https://example.com/rate-limit-plan.md",
            ),
            patch(
                "app.services.channel_artifact_service.require_channel_member_access",
                return_value=object(),
            ),
        ):
            nodes = self.service.list_channel_artifact_nodes(
                self.db,
                current_user=SimpleNamespace(id="user-1"),
                server_id=self.server_id,
                channel_id=self.channel_id,
            )

        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].name, "api-specialist")
        agent_children = nodes[0].children
        assert agent_children is not None
        plan_children = agent_children[0].children
        assert plan_children is not None
        self.assertEqual(agent_children[0].name, "plans")
        self.assertEqual(plan_children[0].name, "rate-limit-plan.md")
        self.assertEqual(
            plan_children[0].url,
            "https://example.com/rate-limit-plan.md",
        )

    def test_list_channel_artifact_candidates_returns_flat_matches(self) -> None:
        artifact_id = uuid.uuid4()
        artifact = SimpleNamespace(
            id=artifact_id,
            channel_id=self.channel_id,
            agent_identity_id=None,
            publisher_user_id="user-1",
            logical_path="/Uploads/design.md",
            display_name="design.md",
            mime_type="text/markdown",
            source_kind="user_upload",
            source_session_id=None,
            size_bytes=128,
            is_previewable=True,
            created_at=None,
        )

        with (
            patch(
                "app.services.channel_artifact_service.require_channel_member_access",
                return_value=object(),
            ),
            patch(
                "app.services.channel_artifact_service."
                "ChannelArtifactRepository.search_by_channel",
                return_value=[artifact],
            ) as search_by_channel,
            patch(
                "app.services.channel_artifact_service.UserRepository.get_by_id",
                return_value=SimpleNamespace(
                    id="user-1",
                    display_name="Alice",
                    primary_email="alice@example.com",
                    avatar_url="https://example.com/alice.png",
                ),
            ),
        ):
            result = self.service.list_channel_artifact_candidates(
                self.db,
                current_user=SimpleNamespace(id="user-1"),
                server_id=self.server_id,
                channel_id=self.channel_id,
                query="design",
            )

        search_by_channel.assert_called_once_with(
            self.db,
            channel_id=self.channel_id,
            query="design",
            limit=20,
        )
        self.assertEqual(result[0].artifact_id, artifact_id)
        self.assertEqual(result[0].display_name, "design.md")
        self.assertEqual(result[0].logical_path, "/Uploads/design.md")
        assert result[0].publisher is not None
        self.assertEqual(result[0].publisher.label, "Alice")

    def test_upload_channel_artifact_emits_channel_event(self) -> None:
        file = UploadFile(
            filename="design.md",
            file=BytesIO(b"# Design\n"),
            headers={"content-type": "text/markdown"},
        )
        channel = SimpleNamespace(id=self.channel_id, name="Product")

        with (
            patch(
                "app.services.channel_artifact_service.require_channel_member_access",
                return_value=channel,
            ),
            patch(
                "app.services.channel_artifact_service."
                "ChannelArtifactRepository.get_by_channel_and_path",
                return_value=None,
            ),
            patch.object(self.service._storage, "upload_fileobj"),
            patch(
                "app.services.channel_artifact_service.create_channel_event_message"
            ) as create_event,
        ):
            result = self.service.upload_channel_artifact(
                self.db,
                current_user=SimpleNamespace(
                    id="user-1",
                    display_name="Alice",
                    primary_email="alice@example.com",
                ),
                server_id=self.server_id,
                channel_id=self.channel_id,
                file=file,
            )

        self.assertEqual(result.name, "design.md")
        create_event.assert_called_once()
        self.assertEqual(
            create_event.call_args.kwargs["event_type"],
            "artifact.uploaded",
        )
        self.assertEqual(
            create_event.call_args.kwargs["content"]["artifact_display_name"],
            "design.md",
        )
        self.assertEqual(
            create_event.call_args.kwargs["content"]["artifact_logical_path"],
            "/Uploads/design.md",
        )

    def test_read_runtime_artifact_returns_truncated_text(self) -> None:
        artifact_id = uuid.uuid4()
        artifact = SimpleNamespace(
            id=artifact_id,
            channel_id=self.channel_id,
            agent_identity_id=self.agent_identity_id,
            publisher_user_id=None,
            logical_path="/plans/rate-limit-plan.md",
            display_name="rate-limit-plan.md",
            mime_type="text/markdown",
            object_key="objects/plan.md",
            source_kind="workspace_export",
            source_session_id=self.session_id,
            size_bytes=12,
            is_previewable=True,
        )

        with (
            patch(
                "app.services.channel_artifact_service.SessionRepository.get_by_id",
                return_value=self.session,
            ),
            patch(
                "app.services.channel_artifact_service."
                "ServerChannelAgentMemberRepository.get_by_channel_and_agent",
                return_value=SimpleNamespace(),
            ),
            patch(
                "app.services.channel_artifact_service."
                "ChannelArtifactRepository.get_by_channel_and_path",
                return_value=artifact,
            ),
            patch.object(
                self.service._storage,
                "get_text",
                return_value="abcdef",
            ),
        ):
            result = self.service.read_runtime_artifact(
                self.db,
                session_id=self.session_id,
                logical_path="/plans/rate-limit-plan.md",
                max_bytes=3,
            )

        self.assertEqual(result.artifact.artifact_id, artifact_id)
        self.assertEqual(result.content, "abc")
        self.assertTrue(result.truncated)
        self.assertFalse(result.metadata_only)

    def test_runtime_agent_reads_artifact_published_by_another_agent(self) -> None:
        publisher_agent_id = uuid.uuid4()
        runtime_agent_id = uuid.uuid4()
        runtime_session = AgentSession(
            id=self.session_id,
            user_id="user-2",
            sdk_session_id=None,
            config_snapshot={
                "server_id": str(self.server_id),
                "channel_id": str(self.channel_id),
                "agent_identity_id": str(runtime_agent_id),
                "agent_runtime_mode": "persistent",
            },
            status="running",
        )
        artifact = SimpleNamespace(
            id=uuid.uuid4(),
            channel_id=self.channel_id,
            agent_identity_id=publisher_agent_id,
            publisher_user_id="user-1",
            logical_path="/plans/rate-limit-plan.md",
            display_name="rate-limit-plan.md",
            mime_type="text/markdown",
            object_key="objects/plan.md",
            source_kind="workspace_export",
            source_session_id=uuid.uuid4(),
            size_bytes=64,
            is_previewable=True,
        )

        with (
            patch(
                "app.services.channel_artifact_service.SessionRepository.get_by_id",
                return_value=runtime_session,
            ),
            patch(
                "app.services.channel_artifact_service."
                "ServerChannelAgentMemberRepository.get_by_channel_and_agent",
                return_value=SimpleNamespace(agent_identity_id=runtime_agent_id),
            ),
            patch(
                "app.services.channel_artifact_service."
                "ChannelArtifactRepository.list_by_channel",
                return_value=[artifact],
            ),
            patch(
                "app.services.channel_artifact_service."
                "ChannelArtifactRepository.get_by_channel_and_path",
                return_value=artifact,
            ),
            patch.object(
                self.service._storage,
                "get_text",
                return_value="# Plan\nUse token bucket limits.",
            ),
        ):
            listed = self.service.list_runtime_artifacts(
                self.db,
                session_id=self.session_id,
            )
            read = self.service.read_runtime_artifact(
                self.db,
                session_id=self.session_id,
                logical_path="/plans/rate-limit-plan.md",
            )

        self.assertEqual(len(listed.artifacts), 1)
        self.assertEqual(listed.artifacts[0].agent_identity_id, publisher_agent_id)
        self.assertEqual(read.content, "# Plan\nUse token bucket limits.")
        self.assertEqual(read.artifact.logical_path, "/plans/rate-limit-plan.md")

    def test_runtime_artifacts_require_channel_agent_membership(self) -> None:
        with (
            patch(
                "app.services.channel_artifact_service.SessionRepository.get_by_id",
                return_value=self.session,
            ),
            patch(
                "app.services.channel_artifact_service."
                "ServerChannelAgentMemberRepository.get_by_channel_and_agent",
                return_value=None,
            ),
        ):
            with self.assertRaises(Exception) as ctx:
                self.service.list_runtime_artifacts(
                    self.db,
                    session_id=self.session_id,
                )

        self.assertIn("not a member", str(ctx.exception))

    def test_read_runtime_artifact_rejects_workspace_path(self) -> None:
        with (
            patch(
                "app.services.channel_artifact_service.SessionRepository.get_by_id",
                return_value=self.session,
            ),
            patch(
                "app.services.channel_artifact_service."
                "ServerChannelAgentMemberRepository.get_by_channel_and_agent",
                return_value=SimpleNamespace(),
            ),
        ):
            with self.assertRaises(Exception) as ctx:
                self.service.read_runtime_artifact(
                    self.db,
                    session_id=self.session_id,
                    logical_path="/workspace/plans/rate-limit-plan.md",
                )

        self.assertIn("/workspace", str(ctx.exception))

    def test_search_runtime_artifacts_can_match_text_content(self) -> None:
        artifact = SimpleNamespace(
            id=uuid.uuid4(),
            channel_id=self.channel_id,
            agent_identity_id=self.agent_identity_id,
            publisher_user_id=None,
            logical_path="/plans/rate-limit-plan.md",
            display_name="rate-limit-plan.md",
            mime_type="text/markdown",
            object_key="objects/plan.md",
            source_kind="workspace_export",
            source_session_id=self.session_id,
            size_bytes=64,
            is_previewable=True,
        )

        with (
            patch(
                "app.services.channel_artifact_service.SessionRepository.get_by_id",
                return_value=self.session,
            ),
            patch(
                "app.services.channel_artifact_service."
                "ServerChannelAgentMemberRepository.get_by_channel_and_agent",
                return_value=SimpleNamespace(),
            ),
            patch(
                "app.services.channel_artifact_service.ChannelArtifactRepository.search_by_channel",
                return_value=[],
            ),
            patch(
                "app.services.channel_artifact_service.ChannelArtifactRepository.list_by_channel",
                return_value=[artifact],
            ),
            patch.object(
                self.service._storage,
                "get_text",
                return_value="Use token bucket limits.",
            ),
        ):
            result = self.service.search_runtime_artifacts(
                self.db,
                session_id=self.session_id,
                query="token bucket",
                include_content=True,
            )

        self.assertEqual(len(result.artifacts), 1)
        self.assertEqual(result.artifacts[0].logical_path, "/plans/rate-limit-plan.md")


if __name__ == "__main__":
    unittest.main()
