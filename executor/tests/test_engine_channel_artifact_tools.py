import unittest

from app.core.engine import AgentExecutor
from app.schemas.request import TaskConfig


class AgentExecutorChannelArtifactTests(unittest.TestCase):
    def test_compose_prompt_includes_channel_artifact_contract(self) -> None:
        executor = AgentExecutor.__new__(AgentExecutor)

        prompt = executor._compose_user_prompt(
            "Review the shared plan",
            TaskConfig(
                server_id="00000000-0000-0000-0000-000000000001",
                channel_id="00000000-0000-0000-0000-000000000002",
                agent_identity_id="00000000-0000-0000-0000-000000000003",
                agent_runtime_mode="persistent",
            ),
            cwd="/workspace/demo",
        )

        self.assertIn("list_channel_artifacts", prompt)
        self.assertIn("search_channel_artifacts", prompt)
        self.assertIn("read_channel_artifact", prompt)
        self.assertIn("read_channel_artifact_text", prompt)
        self.assertIn("stage_channel_artifact_to_workspace", prompt)
        self.assertIn("not /workspace filesystem paths", prompt)

    def test_compose_prompt_omits_artifact_contract_without_channel_scope(self) -> None:
        executor = AgentExecutor.__new__(AgentExecutor)

        prompt = executor._compose_user_prompt(
            "Review the issue",
            TaskConfig(agent_runtime_mode="persistent"),
            cwd="/workspace/demo",
        )

        self.assertNotIn("list_channel_artifacts", prompt)
        self.assertNotIn("read_channel_artifact", prompt)

    def test_old_channel_artifact_mcp_injector_is_removed(self) -> None:
        self.assertFalse(hasattr(AgentExecutor, "_inject_channel_artifacts_mcp"))


if __name__ == "__main__":
    unittest.main()
