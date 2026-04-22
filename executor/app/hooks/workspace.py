from datetime import datetime, timezone
from typing import Any

from app.hooks.base import AgentHook, ExecutionContext
from app.schemas.enums import FileStatus
from app.schemas.state import FileChange, WorkspaceState
from app.utils.git.operations import (
    GitNotRepositoryError,
    diff,
    get_numstat_total,
    get_numstat,
    get_status,
    has_commits,
    is_repository,
    list_remotes,
    remote_url,
)

_LOCAL_MOUNT_ROOT = ".poco-local/"


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
                file_change_count=len(file_changes),
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
        merged_changes: dict[str, FileChange] = {}
        has_head_commit = has_commits(cwd)

        if has_head_commit:
            changed_paths = {
                file
                for file in [
                    *git_status.modified,
                    *git_status.staged,
                    *git_status.deleted,
                    *(new_path for _, new_path in git_status.renamed),
                ]
                if not self._should_skip_path(file)
            }
            deleted_paths = {
                file for file in git_status.deleted if not self._should_skip_path(file)
            }
            for file in sorted(changed_paths):
                added, deleted = get_numstat_total(cwd, ref="HEAD", file=file)
                diff_content = diff(file=file, cwd=cwd, ref="HEAD")
                merged_changes[file] = FileChange(
                    path=file,
                    status=(
                        FileStatus.DELETED
                        if file in deleted_paths
                        else FileStatus.MODIFIED
                    ),
                    added_lines=added,
                    deleted_lines=deleted,
                    diff=diff_content or None,
                )
        else:
            unstaged_numstat = get_numstat(cwd, cached=False)
            staged_numstat = get_numstat(cwd, cached=True)

            for file in git_status.modified:
                if self._should_skip_path(file):
                    continue
                added, deleted = unstaged_numstat.get(file, (0, 0))
                diff_content = diff(file=file, cwd=cwd, cached=False)
                self._merge_file_change(
                    merged_changes,
                    FileChange(
                        path=file,
                        status=FileStatus.MODIFIED,
                        added_lines=added,
                        deleted_lines=deleted,
                        diff=diff_content or None,
                    ),
                )

            for file in git_status.staged:
                if self._should_skip_path(file):
                    continue
                added, deleted = staged_numstat.get(file, (0, 0))
                diff_content = diff(file=file, cwd=cwd, cached=True)
                self._merge_file_change(
                    merged_changes,
                    FileChange(
                        path=file,
                        status=FileStatus.MODIFIED,
                        added_lines=added,
                        deleted_lines=deleted,
                        diff=diff_content or None,
                    ),
                )

        for file in git_status.untracked:
            if self._should_skip_path(file):
                continue
            self._merge_file_change(
                merged_changes,
                FileChange(
                    path=file,
                    status=FileStatus.ADDED,
                    added_lines=0,
                    deleted_lines=0,
                ),
            )

        for file in git_status.deleted:
            if self._should_skip_path(file):
                continue
            self._overlay_file_change_status(
                merged_changes,
                path=file,
                status=FileStatus.DELETED,
            )

        for old_path, new_path in git_status.renamed:
            if self._should_skip_path(old_path) or self._should_skip_path(new_path):
                continue
            self._overlay_file_change_status(
                merged_changes,
                path=new_path,
                status=FileStatus.RENAMED,
                old_path=old_path,
            )

        return list(merged_changes.values())

    @staticmethod
    def _merge_file_change(
        merged_changes: dict[str, FileChange], incoming: FileChange
    ) -> None:
        existing = merged_changes.get(incoming.path)
        if existing is None:
            merged_changes[incoming.path] = incoming
            return

        merged_changes[incoming.path] = FileChange(
            path=incoming.path,
            status=WorkspaceHook._pick_status(existing.status, incoming.status),
            added_lines=(existing.added_lines or 0) + (incoming.added_lines or 0),
            deleted_lines=(existing.deleted_lines or 0) + (incoming.deleted_lines or 0),
            diff=WorkspaceHook._merge_diff(existing.diff, incoming.diff),
            old_path=existing.old_path or incoming.old_path,
        )

    @staticmethod
    def _overlay_file_change_status(
        merged_changes: dict[str, FileChange],
        *,
        path: str,
        status: FileStatus,
        old_path: str | None = None,
    ) -> None:
        existing = merged_changes.get(path)
        if existing is None:
            merged_changes[path] = FileChange(
                path=path,
                status=status,
                old_path=old_path,
            )
            return

        merged_changes[path] = FileChange(
            path=path,
            status=WorkspaceHook._pick_status(existing.status, status),
            added_lines=existing.added_lines,
            deleted_lines=existing.deleted_lines,
            diff=existing.diff,
            old_path=existing.old_path or old_path,
        )

    @staticmethod
    def _merge_diff(left: str | None, right: str | None) -> str | None:
        left_text = (left or "").strip()
        right_text = (right or "").strip()

        if not left_text and not right_text:
            return None
        if not left_text:
            return right_text
        if not right_text or left_text == right_text:
            return left_text
        return f"{left_text}\n{right_text}"

    @staticmethod
    def _pick_status(current: FileStatus, incoming: FileStatus) -> FileStatus:
        priority = {
            FileStatus.RENAMED: 4,
            FileStatus.DELETED: 3,
            FileStatus.MODIFIED: 2,
            FileStatus.STAGED: 2,
            FileStatus.ADDED: 1,
        }
        return (
            incoming
            if priority.get(incoming, 0) > priority.get(current, 0)
            else current
        )

    @staticmethod
    def _should_skip_path(path: str) -> bool:
        normalized = (path or "").strip()
        while normalized.startswith("./"):
            normalized = normalized[2:]
        normalized = normalized.lstrip("/")
        return normalized == ".poco-local" or normalized.startswith(_LOCAL_MOUNT_ROOT)

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
