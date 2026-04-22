import unittest
from unittest.mock import patch

from app.hooks.workspace import WorkspaceHook
from app.schemas.enums import FileStatus
from app.utils.git.operations import GitStatus


class WorkspaceHookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.hook = WorkspaceHook()

    @patch("app.hooks.workspace.diff")
    @patch("app.hooks.workspace.get_numstat_total")
    @patch("app.hooks.workspace.has_commits")
    def test_collect_file_changes_uses_head_net_diff_without_double_counting(
        self,
        has_commits,
        get_numstat_total,
        diff,
    ) -> None:
        has_commits.return_value = True
        get_numstat_total.side_effect = [
            (4, 1),
            (0, 3),
        ]
        diff.side_effect = [
            "diff --git a/src/a.py b/src/a.py",
            "diff --git a/src/deleted.py b/src/deleted.py",
        ]
        git_status = GitStatus(
            branch="main",
            staged=["src/a.py"],
            modified=["src/a.py"],
            deleted=["src/deleted.py"],
        )

        changes = self.hook._collect_file_changes(git_status, "/tmp/workspace")
        changes_by_path = {change.path: change for change in changes}

        self.assertEqual(len(changes), 2)
        self.assertEqual(changes_by_path["src/a.py"].added_lines, 4)
        self.assertEqual(changes_by_path["src/a.py"].deleted_lines, 1)
        self.assertEqual(changes_by_path["src/a.py"].status, FileStatus.MODIFIED)
        self.assertEqual(
            changes_by_path["src/deleted.py"].status,
            FileStatus.DELETED,
        )
        self.assertEqual(
            get_numstat_total.call_count,
            2,
        )

    @patch("app.hooks.workspace.diff")
    @patch("app.hooks.workspace.get_numstat")
    @patch("app.hooks.workspace.has_commits")
    def test_collect_file_changes_merges_staged_and_unstaged_when_no_head_exists(
        self,
        has_commits,
        get_numstat,
        diff,
    ) -> None:
        has_commits.return_value = False
        get_numstat.side_effect = [
            {"src/new.py": (2, 0)},
            {"src/new.py": (3, 1)},
        ]
        diff.side_effect = [
            "unstaged diff",
            "staged diff",
        ]
        git_status = GitStatus(
            branch="main",
            staged=["src/new.py"],
            modified=["src/new.py"],
        )

        changes = self.hook._collect_file_changes(git_status, "/tmp/workspace")

        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].path, "src/new.py")
        self.assertEqual(changes[0].added_lines, 5)
        self.assertEqual(changes[0].deleted_lines, 1)
        self.assertEqual(changes[0].diff, "unstaged diff\nstaged diff")

    @patch("app.hooks.workspace.has_commits")
    def test_collect_file_changes_overlays_renamed_status_and_old_path(
        self,
        has_commits,
    ) -> None:
        has_commits.return_value = True
        git_status = GitStatus(
            branch="main",
            renamed=[("src/old.py", "src/new.py")],
        )

        with (
            patch("app.hooks.workspace.get_numstat_total", return_value=(1, 1)),
            patch("app.hooks.workspace.diff", return_value="rename diff"),
        ):
            changes = self.hook._collect_file_changes(git_status, "/tmp/workspace")

        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].path, "src/new.py")
        self.assertEqual(changes[0].status, FileStatus.RENAMED)
        self.assertEqual(changes[0].old_path, "src/old.py")
        self.assertEqual(changes[0].added_lines, 1)
        self.assertEqual(changes[0].deleted_lines, 1)


if __name__ == "__main__":
    unittest.main()
