from datetime import UTC, datetime
import unittest
from typing import cast
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.sql.schema import Table

from app.models import Base
from app.models.agent_message import AgentMessage
from app.models.agent_run import AgentRun
from app.models.agent_scheduled_task import AgentScheduledTask
from app.models.agent_session import AgentSession
from app.models.tool_execution import ToolExecution
from app.repositories.tool_execution_repository import ToolExecutionRepository

TEST_TABLES = [
    cast(Table, AgentSession.__table__),
    cast(Table, AgentMessage.__table__),
    cast(Table, AgentScheduledTask.__table__),
    cast(Table, AgentRun.__table__),
    cast(Table, ToolExecution.__table__),
]


class ToolExecutionRepositoryIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine, tables=TEST_TABLES)
        self.session_factory = sessionmaker(bind=self.engine, autoflush=False)
        self.db: Session = self.session_factory()

        self.session_id = uuid4()
        self.run_id_1 = uuid4()
        self.run_id_2 = uuid4()
        now = datetime.now(UTC)

        agent_session = AgentSession(
            id=self.session_id,
            user_id="user-1",
            status="running",
            kind="chat",
            created_at=now,
            updated_at=now,
        )
        self.db.add(agent_session)

        message_1 = AgentMessage(
            id=1,
            session_id=self.session_id,
            role="user",
            content={"content": []},
            text_preview="message 1",
            created_at=now,
            updated_at=now,
        )
        message_2 = AgentMessage(
            id=2,
            session_id=self.session_id,
            role="assistant",
            content={"content": []},
            text_preview="message 2",
            created_at=now,
            updated_at=now,
        )
        self.db.add_all([message_1, message_2])

        run_1 = AgentRun(
            id=self.run_id_1,
            session_id=self.session_id,
            user_message_id=1,
            status="completed",
            permission_mode="default",
            progress=100,
            schedule_mode="immediate",
            attempts=1,
            scheduled_at=now,
            created_at=now,
            updated_at=now,
        )
        run_2 = AgentRun(
            id=self.run_id_2,
            session_id=self.session_id,
            user_message_id=1,
            status="completed",
            permission_mode="default",
            progress=100,
            schedule_mode="immediate",
            attempts=1,
            scheduled_at=now,
            created_at=now,
            updated_at=now,
        )
        self.db.add_all([run_1, run_2])
        self.db.flush()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine, tables=list(reversed(TEST_TABLES)))
        self.engine.dispose()

    def _add_tool_execution(
        self,
        *,
        run_id,
        tool_name: str,
        message_id: int = 1,
    ) -> None:
        now = datetime.now(UTC)
        self.db.add(
            ToolExecution(
                id=uuid4(),
                session_id=self.session_id,
                run_id=run_id,
                message_id=message_id,
                tool_use_id=str(uuid4()),
                tool_name=tool_name,
                tool_input={},
                tool_output={},
                is_error=False,
                duration_ms=10,
                created_at=now,
                updated_at=now,
            )
        )

    def test_count_by_run_ids_counts_only_replayable_tools(self) -> None:
        self._add_tool_execution(run_id=self.run_id_1, tool_name="bash")
        self._add_tool_execution(
            run_id=self.run_id_1,
            tool_name="mcp____poco_playwright__browser_click",
        )
        self._add_tool_execution(run_id=self.run_id_1, tool_name="Read")
        self._add_tool_execution(run_id=self.run_id_1, tool_name="unknown_tool")
        self._add_tool_execution(run_id=self.run_id_2, tool_name="glob")
        self._add_tool_execution(run_id=self.run_id_2, tool_name="custom_tool")
        self._add_tool_execution(run_id=None, tool_name="bash", message_id=2)
        self.db.commit()

        result = ToolExecutionRepository.count_by_run_ids(
            self.db,
            [self.run_id_1, self.run_id_2],
        )

        self.assertEqual(
            result,
            {
                self.run_id_1: 3,
                self.run_id_2: 1,
            },
        )

    def test_count_by_run_ids_supports_normalized_generic_tool_names(self) -> None:
        self._add_tool_execution(run_id=self.run_id_1, tool_name="write")
        self._add_tool_execution(run_id=self.run_id_1, tool_name="r_e-a d")
        self._add_tool_execution(run_id=self.run_id_1, tool_name="g-r_e p")
        self._add_tool_execution(run_id=self.run_id_1, tool_name=" edit ")
        self.db.commit()

        result = ToolExecutionRepository.count_by_run_ids(self.db, [self.run_id_1])

        self.assertEqual(result, {self.run_id_1: 4})


if __name__ == "__main__":
    unittest.main()
