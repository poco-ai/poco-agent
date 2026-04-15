import uuid

from sqlalchemy.orm import Session

from app.core.audit import auditable
from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.user import User
from app.models.workspace_board import WorkspaceBoard
from app.repositories.workspace_board_repository import WorkspaceBoardRepository
from app.schemas.workspace_board import (
    WorkspaceBoardCreateRequest,
    WorkspaceBoardResponse,
)
from app.services.workspace_member_service import require_workspace_member


class WorkspaceBoardService:
    @staticmethod
    def _to_response(board: WorkspaceBoard) -> WorkspaceBoardResponse:
        return WorkspaceBoardResponse.model_validate(board)

    @auditable(
        action="board.created",
        target_type="board",
        target_id=lambda _args, result: result.board_id,
        workspace_id=lambda _args, result: result.workspace_id,
        metadata_fn=lambda args, _result: {"name": args["request"].name},
    )
    def create_board(
        self,
        db: Session,
        current_user: User,
        workspace_id: uuid.UUID,
        request: WorkspaceBoardCreateRequest,
    ) -> WorkspaceBoardResponse:
        require_workspace_member(db, workspace_id, current_user.id)
        board = WorkspaceBoard(
            workspace_id=workspace_id,
            name=request.name.strip(),
            description=(request.description or "").strip() or None,
            created_by=current_user.id,
            updated_by=current_user.id,
        )
        board = WorkspaceBoardRepository.create(db, board)
        db.commit()
        db.refresh(board)
        return self._to_response(board)

    def list_boards(
        self,
        db: Session,
        current_user: User,
        workspace_id: uuid.UUID,
    ) -> list[WorkspaceBoardResponse]:
        require_workspace_member(db, workspace_id, current_user.id)
        return [
            self._to_response(board)
            for board in WorkspaceBoardRepository.list_by_workspace(db, workspace_id)
        ]

    def get_board(
        self,
        db: Session,
        current_user: User,
        board_id: uuid.UUID,
    ) -> WorkspaceBoard:
        board = WorkspaceBoardRepository.get_by_id(db, board_id)
        if board is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Workspace board not found: {board_id}",
            )
        require_workspace_member(db, board.workspace_id, current_user.id)
        return board

    @auditable(
        action="board.updated",
        target_type="board",
        target_id=lambda args, _result: args["board_id"],
        workspace_id=lambda _args, result: result.workspace_id,
        metadata_fn=lambda args, _result: args["request"].model_dump(mode="json"),
    )
    def update_board(
        self,
        db: Session,
        current_user: User,
        board_id: uuid.UUID,
        request: WorkspaceBoardCreateRequest,
    ) -> WorkspaceBoardResponse:
        board = self.get_board(db, current_user, board_id)
        board.name = request.name.strip()
        board.description = (request.description or "").strip() or None
        board.updated_by = current_user.id
        db.commit()
        db.refresh(board)
        return self._to_response(board)

    @auditable(
        action="board.deleted",
        target_type="board",
        target_id=lambda args, _result: args["board_id"],
        workspace_id=lambda _args, result: result.workspace_id,
        metadata_fn=lambda _args, result: {"name": result.name},
    )
    def delete_board(
        self,
        db: Session,
        current_user: User,
        board_id: uuid.UUID,
    ) -> WorkspaceBoardResponse:
        board = self.get_board(db, current_user, board_id)
        response = self._to_response(board)
        db.delete(board)
        db.commit()
        return response
