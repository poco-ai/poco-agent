import uuid
from unittest.mock import MagicMock, call, patch

from sqlalchemy.exc import IntegrityError

from app.services.mcp_connection_service import McpConnectionService


def test_record_transition_allows_direct_staged_from_none() -> None:
    db = MagicMock()
    service = McpConnectionService()

    with patch(
        "app.services.mcp_connection_service.AgentRunMcpConnectionRepository"
    ) as mock_repo:
        mock_repo.get_by_run_and_server_name.return_value = None

        service.record_transition(
            db,
            run_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            server_name="filesystem",
            to_state="staged",
            event_source="executor_manager",
        )

        mock_repo.create.assert_called_once()
        db.flush.assert_called()


def test_record_transition_same_state_duplicate_is_noop() -> None:
    db = MagicMock()
    existing = MagicMock()
    existing.state = "staged"
    service = McpConnectionService()

    with patch(
        "app.services.mcp_connection_service.AgentRunMcpConnectionRepository"
    ) as mock_repo, patch("app.services.mcp_connection_service.logger") as mock_logger:
        mock_repo.get_by_run_and_server_name.return_value = existing

        service.record_transition(
            db,
            run_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            server_name="filesystem",
            to_state="staged",
            event_source="executor_manager",
        )

        mock_logger.warning.assert_not_called()
        db.add.assert_not_called()


def test_record_transition_recovers_from_create_race() -> None:
    db = MagicMock()
    reloaded = MagicMock()
    reloaded.state = "requested"
    service = McpConnectionService()

    with patch(
        "app.services.mcp_connection_service.AgentRunMcpConnectionRepository"
    ) as mock_repo:
        mock_repo.get_by_run_and_server_name.side_effect = [None, reloaded]
        mock_repo.create.side_effect = IntegrityError("insert", {}, Exception("boom"))

        service.record_transition(
            db,
            run_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            server_name="filesystem",
            to_state="staged",
            event_source="executor_manager",
        )

        db.begin_nested.assert_called_once()
        assert reloaded.state == "staged"
        db.add.assert_called_once()
