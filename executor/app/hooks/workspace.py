from datetime import datetime, timezone
from typing import Any

from app.hooks.base import AgentHook, ExecutionContext
from app.schemas.enums import FileStatus
from app.schemas.state import FileChange, WorkspaceState
from app.utils.git.operations import (
    GitNotRepositoryError,
    diff,
    get_numstat,
    get_status,
    is_repository,
    list_remotes,
    remote_url,
)


class WorkspaceHook(AgentHook):
    """Hook that monitors workspace file changes and updates state."""

    async def on_agent_response(self, context: ExecutionContext, message: Any) -> None:
        """Capture Git-tracked file changes after each agent response.

        Args:
            context: The execution context containing workspace state.
            message: The agent response message (unused).
        """
        try:
            if not is_repository(context.cwd):
                context.current_state.workspace_state = WorkspaceState()
                return

            git_status = get_status(context.cwd)
            repository = self._get_repository_url(context.cwd)
            file_changes = self._collect_file_changes(git_status, context.cwd)

            total_added = sum(fc.added_lines for fc in file_changes)
            total_deleted = sum(fc.deleted_lines for fc in file_changes)

            context.current_state.workspace_state = WorkspaceState(
                repository=repository,
                branch=git_status.branch,
                total_added_lines=total_added,
                total_deleted_lines=total_deleted,
                file_changes=file_changes,
                last_change=datetime.now(timezone.utc),
            )
        except GitNotRepositoryError:
            context.current_state.workspace_state = WorkspaceState()
        except Exception:
            context.current_state.workspace_state = WorkspaceState()

    def _collect_file_changes(self, git_status, cwd: str) -> list[FileChange]:
        """Collect file changes with diff information.

        Args:
            git_status: The Git status object.
            cwd: Current working directory.

        Returns:
            List of FileChange objects.
        """
        file_changes = []

        unstaged_numstat = get_numstat(cwd, cached=False)
        staged_numstat = get_numstat(cwd, cached=True)

        for file in git_status.modified:
            added, deleted = unstaged_numstat.get(file, (0, 0))
            diff_content = diff(file=file, cwd=cwd, cached=False)
            file_changes.append(
                FileChange(
                    path=file,
                    status=FileStatus.MODIFIED,
                    added_lines=added,
                    deleted_lines=deleted,
                    diff=diff_content or None,
                )
            )

        for file in git_status.staged:
            added, deleted = staged_numstat.get(file, (0, 0))
            diff_content = diff(file=file, cwd=cwd, cached=True)
            file_changes.append(
                FileChange(
                    path=file,
                    status=FileStatus.STAGED,
                    added_lines=added,
                    deleted_lines=deleted,
                    diff=diff_content or None,
                )
            )

        for file in git_status.deleted:
            file_changes.append(
                FileChange(
                    path=file, status=FileStatus.DELETED, added_lines=0, deleted_lines=0
                )
            )

        for old_path, new_path in git_status.renamed:
            file_changes.append(
                FileChange(
                    path=new_path,
                    status=FileStatus.RENAMED,
                    added_lines=0,
                    deleted_lines=0,
                    old_path=old_path,
                )
            )

        return file_changes

    def _get_repository_url(self, cwd: str) -> str | None:
        """Get repository URL from Git remotes.

        Tries 'origin', then 'upstream', then the first available remote.

        Args:
            cwd: Current working directory.

        Returns:
            Repository URL or None if not found.
        """
        try:
            for remote_name in ["origin", "upstream"]:
                try:
                    return remote_url(remote_name, cwd)
                except Exception:
                    continue

            remotes = list_remotes(cwd)
            if remotes:
                return remotes[0].fetch_url
        except Exception:
            pass

        return None
