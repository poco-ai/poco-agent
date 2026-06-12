import unittest

from app.core.engine import AgentExecutor
from app.schemas.request import InputFile, TaskConfig


class AgentExecutorInputHintTests(unittest.TestCase):
    def test_build_input_hint_maps_file_references_to_staged_inputs(self) -> None:
        executor = AgentExecutor.__new__(AgentExecutor)

        hint = executor._build_input_hint(
            TaskConfig(
                input_files=[
                    InputFile(
                        name="report.md",
                        source="uploads/session/report.md",
                        path="/inputs/report.md",
                    ),
                    InputFile(
                        name="agent.md",
                        source="workspace/session/notes/agent.md",
                        path="/inputs/notes/agent.md",
                    ),
                ],
                file_references=[
                    {
                        "id": "uploads/session/report.md:4:14",
                        "kind": "input_file",
                        "source": "uploads/session/report.md",
                        "insertedText": "#report.md",
                        "displayName": "report.md",
                    },
                    {
                        "id": "session-1:/notes/agent.md:19:28",
                        "kind": "workspace_file",
                        "sessionId": "session-1",
                        "path": "/notes/agent.md",
                        "insertedText": "#agent.md",
                        "displayName": "agent.md",
                    },
                ],
            )
        )

        self.assertIsNotNone(hint)
        assert hint is not None
        self.assertIn(
            "Input files for this run are available under inputs/", hint
        )
        self.assertIn("Referenced files in the user prompt resolve to:", hint)
        self.assertIn("- #report.md -> inputs/report.md", hint)
        self.assertIn("- #agent.md -> inputs/notes/agent.md", hint)


if __name__ == "__main__":
    unittest.main()
