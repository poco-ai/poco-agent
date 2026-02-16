from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.repositories.message_repository import MessageRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.run_repository import RunRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.sub_agent_repository import SubAgentRepository
from app.repositories.user_mcp_install_repository import UserMcpInstallRepository
from app.repositories.user_plugin_install_repository import UserPluginInstallRepository
from app.repositories.user_skill_install_repository import UserSkillInstallRepository
from app.schemas.session import TaskConfig
from app.schemas.task import TaskEnqueueRequest, TaskEnqueueResponse


class TaskService:
    """Service layer for task enqueue operations."""

    @staticmethod
    def _validate_and_normalize_model(config: dict) -> None:
        """Validate `model` override and normalize config in-place.

        Rules:
        - `model` unset/empty -> removed (use DEFAULT_MODEL)
        - `model` equals settings.default_model -> removed (treat as default; do not pin)
        - otherwise `model` must be in settings.model_list
        """
        if not isinstance(config, dict):
            return

        if "model" not in config:
            return

        raw = config.get("model")
        if raw is None:
            # Explicit null clears a previously pinned model.
            config.pop("model", None)
            return

        if not isinstance(raw, str):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="model must be a string or null",
            )

        value = raw.strip()
        if not value:
            config.pop("model", None)
            return

        settings = get_settings()
        default_model = (settings.default_model or "").strip()
        if value == default_model:
            # Treat selecting the default as "inherit", so the session follows future
            # default_model changes instead of pinning the old value.
            config.pop("model", None)
            return

        allowed = {m.strip() for m in (settings.model_list or []) if (m or "").strip()}
        if value not in allowed:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"Invalid model: {value}",
            )

        config["model"] = value

    @staticmethod
    def _apply_project_repo_defaults(config: dict | None, project) -> dict | None:
        """Fill repo context from project defaults when not explicitly provided by the caller."""
        if not isinstance(config, dict) or not project:
            return config

        project_repo = (getattr(project, "repo_url", None) or "").strip()
        if not project_repo:
            return config

        updated = dict(config)

        repo_key_present = "repo_url" in updated
        repo_val = (updated.get("repo_url") or "").strip() if repo_key_present else ""

        # Only inject project defaults when the caller did not explicitly specify repo_url.
        if not repo_key_present:
            updated["repo_url"] = project_repo
            # Fill defaults only when we use the project's repo_url.
            if "git_branch" not in updated:
                branch = (getattr(project, "git_branch", None) or "").strip()
                if branch:
                    updated["git_branch"] = branch
            if "git_token_env_key" not in updated:
                token_key = (getattr(project, "git_token_env_key", None) or "").strip()
                if token_key:
                    updated["git_token_env_key"] = token_key
            return updated

        # If repo_url is explicitly set (including explicit null/empty), do not override.
        if not repo_val:
            return updated

        # If the caller uses the same repo_url as the project, we can safely fill missing
        # branch/token defaults from the project.
        if repo_val == project_repo:
            if "git_branch" not in updated:
                branch = (getattr(project, "git_branch", None) or "").strip()
                if branch:
                    updated["git_branch"] = branch
            if "git_token_env_key" not in updated:
                token_key = (getattr(project, "git_token_env_key", None) or "").strip()
                if token_key:
                    updated["git_token_env_key"] = token_key

        return updated

    def _normalize_scheduled_at(
        self, scheduled_at: datetime, timezone_name: str | None
    ) -> datetime:
        if scheduled_at.tzinfo is None:
            tz_raw = (timezone_name or "").strip()
            if tz_raw:
                try:
                    tz = ZoneInfo(tz_raw)
                except Exception as e:
                    raise AppException(
                        error_code=ErrorCode.BAD_REQUEST,
                        message=f"Invalid timezone: {tz_raw}",
                    ) from e
                scheduled_at = scheduled_at.replace(tzinfo=tz)
            else:
                scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
        return scheduled_at.astimezone(timezone.utc)

    def _resolve_schedule(
        self, request: TaskEnqueueRequest
    ) -> tuple[str, datetime | None]:
        """Resolve run schedule metadata.

        Note: Actual scheduling rules (e.g., when "nightly" runs) are owned by Executor Manager.
        Backend only stores schedule metadata for queue filtering.
        """
        schedule_mode = request.schedule_mode.strip() if request.schedule_mode else ""
        if not schedule_mode:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="schedule_mode cannot be empty",
            )
        scheduled_at = (
            self._normalize_scheduled_at(request.scheduled_at, request.timezone)
            if request.scheduled_at is not None
            else None
        )

        if schedule_mode == "scheduled":
            if scheduled_at is None:
                raise AppException(
                    error_code=ErrorCode.BAD_REQUEST,
                    message="scheduled_at is required when schedule_mode=scheduled",
                )
            return schedule_mode, scheduled_at

        if schedule_mode == "immediate":
            # Backward-compat: if caller only provides scheduled_at, treat it as "scheduled".
            if scheduled_at is not None:
                return "scheduled", scheduled_at
            return schedule_mode, None

        if schedule_mode == "nightly":
            if scheduled_at is not None:
                raise AppException(
                    error_code=ErrorCode.BAD_REQUEST,
                    message="scheduled_at cannot be provided when schedule_mode=nightly",
                )
            return schedule_mode, None

        return schedule_mode, scheduled_at

    def enqueue_task(
        self, db: Session, user_id: str, request: TaskEnqueueRequest
    ) -> TaskEnqueueResponse:
        """Enqueue a new run for a session (create session if needed)."""
        base_config: dict | None = None
        project_id = request.project_id
        project = None
        if project_id is not None:
            project = ProjectRepository.get_by_id(db, project_id)
            if not project or project.user_id != user_id:
                raise AppException(
                    error_code=ErrorCode.PROJECT_NOT_FOUND,
                    message=f"Project not found: {project_id}",
                )
        if request.session_id:
            db_session = SessionRepository.get_by_id(db, request.session_id)
            if not db_session:
                raise AppException(
                    error_code=ErrorCode.NOT_FOUND,
                    message=f"Session not found: {request.session_id}",
                )
            if db_session.user_id != user_id:
                raise AppException(
                    error_code=ErrorCode.FORBIDDEN,
                    message="Session does not belong to the user",
                )
            # Clear previous execution state so the UI doesn't show stale file changes
            # while a new run is queued/starting.
            db_session.state_patch = {}
            if project_id is not None and db_session.project_id != project_id:
                raise AppException(
                    error_code=ErrorCode.BAD_REQUEST,
                    message="project_id does not match the session",
                )
            base_config = db_session.config_snapshot or {}
            merged_config = self._build_config_snapshot(
                db, user_id, request.config, base_config=base_config
            )
            merged_config = self._apply_project_repo_defaults(merged_config, project)
        else:
            base_config = {}
            merged_config = self._build_config_snapshot(
                db, user_id, request.config, base_config=base_config
            )
            merged_config = self._apply_project_repo_defaults(merged_config, project)
            config_dict = merged_config
            if project_id is not None:
                # Validation is done upfront; keep this check for backward compat with older codepaths.
                _ = project
            db_session = SessionRepository.create(
                session_db=db,
                user_id=user_id,
                config=config_dict,
                project_id=project_id,
                kind="chat",
            )
            db.flush()
        if merged_config is not None:
            db_session.config_snapshot = merged_config

        prompt = request.prompt.strip()
        if not prompt:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Prompt cannot be empty",
            )

        permission_mode = (request.permission_mode or "default").strip()
        if not permission_mode:
            permission_mode = "default"
        if permission_mode not in {
            "default",
            "acceptEdits",
            "plan",
            "bypassPermissions",
        }:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"Invalid permission_mode: {permission_mode}",
            )

        user_message_content = {
            "_type": "UserMessage",
            "content": [{"_type": "TextBlock", "text": prompt}],
        }

        db_message = MessageRepository.create(
            session_db=db,
            session_id=db_session.id,
            role="user",
            content=user_message_content,
            text_preview=prompt[:500],
        )
        db.flush()

        # Keep session-level config snapshots free of input_files.
        # input_files are treated as per-run inputs and stored only in the run snapshot.
        run_config_snapshot = dict(merged_config or {})
        if request.config is not None and request.config.input_files:
            run_config_snapshot["input_files"] = [
                f.model_dump(mode="json") for f in request.config.input_files
            ]

        schedule_mode, scheduled_at = self._resolve_schedule(request)

        db_run = RunRepository.create(
            session_db=db,
            session_id=db_session.id,
            user_message_id=db_message.id,
            permission_mode=permission_mode,
            schedule_mode=schedule_mode,
            scheduled_at=scheduled_at,
            config_snapshot=run_config_snapshot,
        )

        db_session.status = "pending"

        db.commit()
        db.refresh(db_session)
        db.refresh(db_run)

        return TaskEnqueueResponse(
            session_id=db_session.id,
            run_id=db_run.id,
            status=db_run.status,
        )

    def _build_config_snapshot(
        self,
        db: Session,
        user_id: str,
        task_config: TaskConfig | None,
        *,
        base_config: dict | None = None,
    ) -> dict | None:
        merged_base: dict = dict(base_config or {})
        # Never persist full MCP server configs inside session/run snapshots.
        # They may contain sensitive values and are not needed for the UI.
        merged_base.pop("mcp_config", None)
        # Legacy field (no longer used after switching to skill_ids).
        merged_base.pop("skill_files", None)
        # Legacy field (not used; plugins are tracked via plugin_ids).
        merged_base.pop("plugin_files", None)
        # input_files are treated as per-run inputs and should not be persisted into the session-level config snapshot.
        merged_base.pop("input_files", None)

        base_mcp_server_ids = self._normalize_mcp_server_ids(
            merged_base.get("mcp_server_ids")
        )
        base_skill_ids = self._normalize_skill_ids(merged_base.get("skill_ids"))
        base_plugin_ids = self._normalize_plugin_ids(merged_base.get("plugin_ids"))

        mcp_toggles: dict[str, bool] | None = None
        skill_toggles: dict[str, bool] | None = None
        plugin_toggles: dict[str, bool] | None = None
        if task_config is not None:
            # Only merge fields explicitly provided by the caller to avoid
            # overriding existing session config with schema defaults.
            request_config = task_config.model_dump(exclude_unset=True)
            # input_files are per-run and should not be merged into session config.
            request_config.pop("input_files", None)
            # Extract mcp_config toggles before merging (don't merge as dict)
            mcp_toggles = request_config.pop("mcp_config", None)
            # Extract skill_config toggles before merging (don't merge as dict)
            skill_toggles = request_config.pop("skill_config", None)
            # Extract plugin_config toggles before merging (don't merge as dict)
            plugin_toggles = request_config.pop("plugin_config", None)
            merged_base = self._merge_config_map(merged_base, request_config)

        # Validate and normalize `model` after merging base + overrides.
        self._validate_and_normalize_model(merged_base)

        if mcp_toggles is not None:
            merged_base["mcp_server_ids"] = (
                self._build_user_mcp_server_ids_with_toggles(db, user_id, mcp_toggles)
            )
        elif base_mcp_server_ids is not None:
            merged_base["mcp_server_ids"] = base_mcp_server_ids
        else:
            merged_base["mcp_server_ids"] = self._build_user_mcp_server_ids_defaults(
                db, user_id
            )

        if skill_toggles is not None:
            merged_base["skill_ids"] = self._build_user_skill_ids_with_toggles(
                db, user_id, skill_toggles
            )
        elif base_skill_ids is not None:
            merged_base["skill_ids"] = base_skill_ids
        else:
            merged_base["skill_ids"] = self._build_user_skill_ids_defaults(db, user_id)

        if plugin_toggles is not None:
            merged_base["plugin_ids"] = self._build_user_plugin_ids_with_toggles(
                db, user_id, plugin_toggles
            )
        elif base_plugin_ids is not None:
            merged_base["plugin_ids"] = base_plugin_ids
        else:
            merged_base["plugin_ids"] = self._build_user_plugin_ids_defaults(
                db, user_id
            )

        selected_subagent_ids = self._normalize_subagent_ids(
            merged_base.get("subagent_ids")
        )
        if selected_subagent_ids is not None:
            merged_base["subagent_ids"] = selected_subagent_ids
        else:
            merged_base["subagent_ids"] = self._build_user_subagent_ids_defaults(
                db, user_id
            )
        return merged_base or None

    @staticmethod
    def _merge_config_map(defaults: dict, overrides: dict) -> dict:
        if not overrides:
            return dict(defaults)
        merged: dict = dict(defaults)
        for key, value in overrides.items():
            if value is None:
                merged.pop(key, None)
                continue
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = {**merged[key], **value}
            else:
                merged[key] = value
        return merged

    @staticmethod
    def _normalize_mcp_server_ids(value: object) -> list[int] | None:
        if not isinstance(value, list):
            return None
        result: list[int] = []
        for item in value:
            if isinstance(item, int):
                result.append(item)
                continue
            if isinstance(item, str):
                item = item.strip()
                if not item:
                    continue
                try:
                    result.append(int(item))
                except ValueError:
                    continue
        return result

    @staticmethod
    def _normalize_skill_ids(value: object) -> list[int] | None:
        if not isinstance(value, list):
            return None
        result: list[int] = []
        for item in value:
            if isinstance(item, int):
                result.append(item)
                continue
            if isinstance(item, str):
                item = item.strip()
                if not item:
                    continue
                try:
                    result.append(int(item))
                except ValueError:
                    continue
        return result

    @staticmethod
    def _normalize_subagent_ids(value: object) -> list[int] | None:
        if not isinstance(value, list):
            return None
        result: list[int] = []
        for item in value:
            if isinstance(item, int):
                result.append(item)
                continue
            if isinstance(item, str):
                item = item.strip()
                if not item:
                    continue
                try:
                    result.append(int(item))
                except ValueError:
                    continue
        return result

    @staticmethod
    def _normalize_plugin_ids(value: object) -> list[int] | None:
        if not isinstance(value, list):
            return None
        result: list[int] = []
        for item in value:
            if isinstance(item, int):
                result.append(item)
                continue
            if isinstance(item, str):
                item = item.strip()
                if not item:
                    continue
                try:
                    result.append(int(item))
                except ValueError:
                    continue
        return result

    def _build_user_mcp_server_ids_defaults(
        self, db: Session, user_id: str
    ) -> list[int]:
        """Return enabled MCP server ids from user's installations."""
        result: list[int] = []
        installs = UserMcpInstallRepository.list_by_user(db, user_id)
        for install in installs:
            if install.enabled:
                result.append(install.server_id)
        return result

    def _build_user_subagent_ids_defaults(self, db: Session, user_id: str) -> list[int]:
        """Return enabled subagent ids for the user."""
        result: list[int] = []
        items = SubAgentRepository.list_enabled_by_user(db, user_id=user_id)
        for subagent in items:
            result.append(subagent.id)
        return result

    def _build_user_mcp_server_ids_with_toggles(
        self, db: Session, user_id: str, toggles: dict[str, bool]
    ) -> list[int]:
        """Return enabled MCP server ids from user's installations with task-level toggles."""
        result: list[int] = []
        installs = UserMcpInstallRepository.list_by_user(db, user_id)
        for install in installs:
            if str(install.server_id) in toggles:
                if toggles[str(install.server_id)]:
                    result.append(install.server_id)
                continue
            if install.enabled:
                result.append(install.server_id)
        return result

    def _build_user_skill_ids_defaults(self, db: Session, user_id: str) -> list[int]:
        """Return enabled skill ids from user's installations."""
        result: list[int] = []
        installs = UserSkillInstallRepository.list_by_user(db, user_id)
        for install in installs:
            if install.enabled:
                result.append(install.skill_id)
        return result

    def _build_user_skill_ids_with_toggles(
        self, db: Session, user_id: str, toggles: dict[str, bool]
    ) -> list[int]:
        """Return enabled skill ids from user's installations with task-level toggles."""
        result: list[int] = []
        installs = UserSkillInstallRepository.list_by_user(db, user_id)
        for install in installs:
            if str(install.skill_id) in toggles:
                if toggles[str(install.skill_id)]:
                    result.append(install.skill_id)
                continue
            if install.enabled:
                result.append(install.skill_id)
        return result

    def _build_user_plugin_ids_defaults(self, db: Session, user_id: str) -> list[int]:
        """Return enabled plugin ids from user's installations."""
        result: list[int] = []
        installs = UserPluginInstallRepository.list_by_user(db, user_id)
        for install in installs:
            if install.enabled:
                result.append(install.plugin_id)
        return result

    def _build_user_plugin_ids_with_toggles(
        self, db: Session, user_id: str, toggles: dict[str, bool]
    ) -> list[int]:
        """Return enabled plugin ids from user's installations with task-level toggles."""
        result: list[int] = []
        installs = UserPluginInstallRepository.list_by_user(db, user_id)
        for install in installs:
            if str(install.plugin_id) in toggles:
                if toggles[str(install.plugin_id)]:
                    result.append(install.plugin_id)
                continue
            if install.enabled:
                result.append(install.plugin_id)
        return result
