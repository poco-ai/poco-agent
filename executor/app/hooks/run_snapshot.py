import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from app.hooks.base import AgentHook, ExecutionContext
from app.utils.git.operations import (
    GitError,
    GitNotRepositoryError,
    add_files,
    commit,
    has_commits,
    init_repository,
    is_repository,
    set_config,
    tag_ref,
)

logger = logging.getLogger(__name__)
_LOCAL_MOUNT_EXCLUDE = ":(exclude).poco-local"


def _sanitize_ref_token(value: str) -> str:
    """Return a safe token for git ref names (keeps ASCII and replaces others)."""

    token = (value or "").strip()
    if not token:
        return "unknown"
    token = re.sub(r"[^A-Za-z0-9._-]+", "_", token)
    return token.strip("._-") or "unknown"


def _build_run_ref(run_id: str, kind: str) -> str:
    # Use slash-separated namespace for easy browsing via `git tag -l 'poco/run/*'`.
    return f"poco/run/{_sanitize_ref_token(run_id)}/{kind}"


class RunSnapshotHook(AgentHook):
    """Create git snapshots (commit + tags) per run.

    This hook is intentionally self-contained: it only interacts with the local git
    repository in the workspace, and does not depend on callback/session state.
    """

    def __init__(self, run_id: str | None = None) -> None:
        self._run_id_input = run_id
        self._resolved_run_id: str | None = None
        self._failed: bool = False
        self._error_type: str | None = None

    def _resolve_run_id(self, context: ExecutionContext) -> str:
        if self._resolved_run_id:
            return self._resolved_run_id

        if self._run_id_input and self._run_id_input.strip():
            self._resolved_run_id = self._run_id_input.strip()
            return self._resolved_run_id

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self._resolved_run_id = f"{_sanitize_ref_token(context.session_id)}_{ts}"
        return self._resolved_run_id

    @staticmethod
    def _ensure_git_ready(cwd: Path) -> None:
        """Ensure a git repository exists and is commit-ready."""

        if not is_repository(cwd):
            init_repository(cwd)

        # Make commits work reliably inside containers.
        set_config("user.name", "poco", cwd=cwd)
        set_config("user.email", "poco@local", cwd=cwd)
        set_config("commit.gpgsign", "false", cwd=cwd)

    async def on_setup(self, context: ExecutionContext) -> None:
        run_id = self._resolve_run_id(context)
        cwd = Path(context.cwd)

        try:
            self._ensure_git_ready(cwd)
        except (GitNotRepositoryError, GitError, OSError) as exc:
            logger.warning(
                "run_snapshot_setup_failed",
                extra={
                    "session_id": context.session_id,
                    "run_id": run_id,
                    "error": str(exc),
                },
            )
            return

        # Ensure HEAD exists so subsequent status/diff are relative to a concrete baseline.
        try:
            if not has_commits(cwd):
                add_files([".", _LOCAL_MOUNT_EXCLUDE], cwd=cwd, all_files=True)
                commit(
                    message="poco:init",
                    cwd=cwd,
                    allow_empty=True,
                    no_verify=True,
                )
        except Exception as exc:
            logger.warning(
                "run_snapshot_init_commit_failed",
                extra={
                    "session_id": context.session_id,
                    "run_id": run_id,
                    "error": str(exc),
                },
            )
            return

        # Tag the baseline for this run (state before any agent modifications).
        try:
            tag_ref(_build_run_ref(run_id, "base"), ref="HEAD", cwd=cwd, force=True)
        except Exception as exc:
            logger.warning(
                "run_snapshot_base_tag_failed",
                extra={
                    "session_id": context.session_id,
                    "run_id": run_id,
                    "error": str(exc),
                },
            )

    async def on_error(self, context: ExecutionContext, error: Exception) -> None:
        self._failed = True
        self._error_type = type(error).__name__

    async def on_teardown(self, context: ExecutionContext) -> None:
        run_id = self._resolve_run_id(context)
        cwd = Path(context.cwd)

        try:
            self._ensure_git_ready(cwd)
        except Exception as exc:
            logger.warning(
                "run_snapshot_teardown_git_unavailable",
                extra={
                    "session_id": context.session_id,
                    "run_id": run_id,
                    "error": str(exc),
                },
            )
            return

        status = "failed" if self._failed else "completed"
        message = f"poco:run {run_id} {status}"
        if self._failed and self._error_type:
            message = f"{message} {self._error_type}"

        try:
            add_files([".", _LOCAL_MOUNT_EXCLUDE], cwd=cwd, all_files=True)
        except Exception as exc:
            logger.warning(
                "run_snapshot_add_failed",
                extra={
                    "session_id": context.session_id,
                    "run_id": run_id,
                    "error": str(exc),
                },
            )

        commit_hash: str | None = None
        try:
            commit_hash = commit(
                message=message,
                cwd=cwd,
                allow_empty=True,
                no_verify=True,
            )
        except Exception as exc:
            logger.warning(
                "run_snapshot_commit_failed",
                extra={
                    "session_id": context.session_id,
                    "run_id": run_id,
                    "error": str(exc),
                },
            )
            return

        try:
            tag_ref(
                _build_run_ref(run_id, "result"),
                ref=commit_hash or "HEAD",
                cwd=cwd,
                force=True,
            )
        except Exception as exc:
            logger.warning(
                "run_snapshot_result_tag_failed",
                extra={
                    "session_id": context.session_id,
                    "run_id": run_id,
                    "error": str(exc),
                },
            )
