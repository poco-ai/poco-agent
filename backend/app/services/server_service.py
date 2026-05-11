import re
import uuid

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.server import Server
from app.models.server_channel import ServerChannel
from app.models.server_channel_member import ServerChannelMember
from app.models.server_member import ServerMember
from app.models.user import User
from app.repositories.server_channel_repository import (
    ServerChannelMemberRepository,
    ServerChannelRepository,
)
from app.repositories.server_member_repository import ServerMemberRepository
from app.repositories.server_repository import ServerRepository
from app.schemas.server import (
    ServerCreateRequest,
    ServerOwnershipTransferRequest,
    ServerResponse,
)
from app.services.server_member_service import require_server_owner


class ServerService:
    @staticmethod
    def _slugify(value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
        return normalized or "server"

    @classmethod
    def _unique_slug(cls, db: Session, base_slug: str) -> str:
        slug = base_slug
        suffix = 2
        while ServerRepository.get_by_slug(db, slug) is not None:
            slug = f"{base_slug}-{suffix}"
            suffix += 1
        return slug

    @classmethod
    def _personal_server_name(cls, current_user: User) -> str:
        display_name = (current_user.display_name or "").strip()
        if display_name:
            return f"{display_name}'s Server"
        return "Personal Server"

    @classmethod
    def _personal_server_slug(cls, current_user: User) -> str:
        return cls._slugify(f"personal-{current_user.id}")

    @staticmethod
    def _build_server_response(server: Server) -> ServerResponse:
        return ServerResponse.model_validate(server)

    @staticmethod
    def _create_owner_channel(
        db: Session,
        *,
        server: Server,
        current_user: User,
        name: str,
        slug: str,
        visibility: str,
        system_channel_type: str,
    ) -> ServerChannel:
        channel = ServerChannelRepository.create(
            db,
            ServerChannel(
                server=server,
                name=name,
                slug=slug,
                conversation_type="channel",
                visibility=visibility,
                system_channel_type=system_channel_type,
                created_by=current_user.id,
            ),
        )
        ServerChannelMemberRepository.create(
            db,
            ServerChannelMember(
                channel=channel,
                user_id=current_user.id,
                role="owner",
                status="active",
            ),
        )
        return channel

    def ensure_personal_server(self, db: Session, current_user: User) -> Server:
        server = ServerRepository.get_personal_by_owner(db, current_user.id)
        if server is not None:
            return server

        server = ServerRepository.create(
            db,
            Server(
                name=self._personal_server_name(current_user),
                slug=self._unique_slug(db, self._personal_server_slug(current_user)),
                kind="personal",
                owner_user_id=current_user.id,
            ),
        )
        ServerMemberRepository.create(
            db,
            ServerMember(
                server=server,
                user_id=current_user.id,
                role="owner",
                invited_by=None,
                status="active",
            ),
        )
        self._create_owner_channel(
            db,
            server=server,
            current_user=current_user,
            name="Personal",
            slug="personal",
            visibility="private",
            system_channel_type="personal",
        )
        db.commit()
        db.refresh(server)
        return server

    def list_servers(self, db: Session, current_user: User) -> list[ServerResponse]:
        self.ensure_personal_server(db, current_user)
        servers = ServerRepository.list_by_user(db, current_user.id)
        return [self._build_server_response(item) for item in servers]

    def create_server(
        self,
        db: Session,
        current_user: User,
        request: ServerCreateRequest,
    ) -> ServerResponse:
        name = request.name.strip()
        if not name:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Server name cannot be empty",
            )

        self.ensure_personal_server(db, current_user)
        server = ServerRepository.create(
            db,
            Server(
                name=name,
                slug=self._unique_slug(db, self._slugify(name)),
                kind="shared",
                owner_user_id=current_user.id,
            ),
        )
        ServerMemberRepository.create(
            db,
            ServerMember(
                server=server,
                user_id=current_user.id,
                role="owner",
                invited_by=None,
                status="active",
            ),
        )
        self._create_owner_channel(
            db,
            server=server,
            current_user=current_user,
            name="Public",
            slug="public",
            visibility="public",
            system_channel_type="public",
        )
        db.commit()
        db.refresh(server)
        return self._build_server_response(server)

    def transfer_ownership(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        request: ServerOwnershipTransferRequest,
    ) -> ServerResponse:
        require_server_owner(db, server_id, current_user.id)
        server = ServerRepository.get_by_id(db, server_id)
        if server is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Server not found: {server_id}",
            )
        if server.kind == "personal":
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Personal server ownership cannot be transferred",
            )

        next_owner = ServerMemberRepository.get_by_server_and_user(
            db,
            server_id,
            request.new_owner_user_id,
        )
        if next_owner is None or next_owner.status != "active":
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="New owner must be an active server member",
            )

        current_owner = ServerMemberRepository.get_by_server_and_user(
            db,
            server_id,
            current_user.id,
        )
        if current_owner is not None:
            current_owner.role = "admin"
        next_owner.role = "owner"
        server.owner_user_id = request.new_owner_user_id
        db.commit()
        db.refresh(server)
        return self._build_server_response(server)

    def delete_server(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
    ) -> None:
        require_server_owner(db, server_id, current_user.id)
        server = ServerRepository.get_by_id(db, server_id)
        if server is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Server not found: {server_id}",
            )
        if server.kind == "personal":
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Personal server cannot be deleted",
            )
        server.is_deleted = True
        db.commit()
