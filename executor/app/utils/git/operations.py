"""
Git utility functions for common git operations.

This module provides stateless functions for git operations,
completely decoupled from the executor project.
All functions require explicit cwd parameter.
"""

import os
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


class GitError(Exception):
    """Base exception for git-related errors."""

    pass


class GitCommandError(GitError):
    """Exception raised when a git command fails."""

    command: str
    returncode: int
    stderr: str | None

    def __init__(self, command: str, returncode: int, stderr: str | None = None):
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        message = f"Git command '{command}' failed with exit code {returncode}"
        if stderr:
            message += f": {stderr}"
        super().__init__(message)


class GitNotRepositoryError(GitError):
    """Exception raised when current directory is not a git repository."""

    pass


def _looks_like_not_a_repository(stderr: str) -> bool:
    lower = stderr.lower()
    return (
        "not a git repository" in lower
        or "inside a git repository" in lower
        or "must be run in a work tree" in lower
    )


@dataclass
class GitStatus:
    """Represents git status of a repository."""

    branch: str
    staged: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    untracked: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    renamed: list[tuple[str, str]] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return bool(
            self.staged
            or self.modified
            or self.untracked
            or self.deleted
            or self.renamed
        )


@dataclass
class GitCommit:
    """Represents a git commit."""

    hash: str
    short_hash: str
    author: str
    email: str
    date: str
    message: str


@dataclass
class GitBranch:
    """Represents a git branch."""

    name: str
    is_current: bool
    is_remote: bool
    commit: str | None = None
    upstream: str | None = None


@dataclass
class GitRemote:
    """Represents a git remote."""

    name: str
    fetch_url: str
    push_url: str


def _run_git_command(
    command: list[str],
    cwd: str | Path | None = None,
    check: bool = True,
    capture_output: bool = True,
    text: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """
    Run a git command and return result.

    Args:
        command: The git command to execute (without 'git' prefix)
        cwd: Working directory for the command
        check: If True, raise exception on non-zero exit code
        capture_output: If True, capture stdout and stderr
        text: If True, return output as string
        env: Environment variables for the command

    Returns:
        subprocess.CompletedProcess: The completed process

    Raises:
        GitCommandError: If the command fails and check=True
    """
    try:
        full_command = ["git", *command]
        merged_env = {**os.environ, **(env or {})}
        # Ensure git never blocks on interactive prompts inside the executor.
        merged_env["GIT_TERMINAL_PROMPT"] = "0"

        result = subprocess.run(
            full_command,
            cwd=cwd,
            check=False,
            capture_output=capture_output,
            text=text,
            env=merged_env,
        )

        stderr = result.stderr.strip() if result.stderr else ""
        if result.returncode != 0 and _looks_like_not_a_repository(stderr):
            raise GitNotRepositoryError(stderr or "Not a git repository")

        if check and result.returncode != 0:
            raise GitCommandError(
                command=shlex.join(full_command),
                returncode=result.returncode,
                stderr=stderr or None,
            )

        return result
    except FileNotFoundError:
        raise GitError("Git is not installed or not in PATH") from None


def is_repository(cwd: str | Path | None = None) -> bool:
    """
    Check if the current directory is a git repository.

    Args:
        cwd: Working directory to check

    Returns:
        bool: True if it's a git repository, False otherwise
    """
    try:
        _run_git_command(["rev-parse", "--git-dir"], cwd=cwd, check=True)
        return True
    except (GitCommandError, GitError):
        return False


def has_commits(cwd: str | Path | None = None) -> bool:
    """
    Check whether the repository has at least one commit (i.e., HEAD exists).

    Args:
        cwd: Working directory

    Returns:
        bool: True if HEAD resolves, False otherwise
    """
    try:
        result = _run_git_command(
            ["rev-parse", "--verify", "HEAD"],
            cwd=cwd,
            check=False,
        )
        return result.returncode == 0
    except (GitNotRepositoryError, GitError):
        return False


def tag_ref(
    name: str,
    ref: str | None = None,
    cwd: str | Path | None = None,
    force: bool = False,
) -> None:
    """
    Create (or update) a lightweight tag.

    Args:
        name: Tag name
        ref: Optional git ref/commit to tag (default: HEAD)
        cwd: Working directory
        force: If True, overwrite existing tag
    """
    args = ["tag"]
    if force:
        args.append("-f")
    args.append(name)
    if ref:
        args.append(ref)
    _run_git_command(args, cwd=cwd, check=True)


def get_git_dir(cwd: str | Path | None = None) -> Path:
    """
    Get the .git directory path.

    Args:
        cwd: Working directory

    Returns:
        Path: Path to the .git directory

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    result = _run_git_command(["rev-parse", "--git-dir"], cwd=cwd, check=True)
    git_dir = result.stdout.strip()

    git_path = Path(git_dir)
    if cwd:
        cwd_path = Path(cwd)
        if not git_path.is_absolute():
            git_path = cwd_path / git_path

    return git_path.resolve()


def init_repository(path: str | Path | None = None, bare: bool = False) -> Path:
    """
    Initialize a new git repository.

    Args:
        path: Path to initialize (default: current directory)
        bare: If True, create a bare repository

    Returns:
        Path: Path to the initialized repository
    """
    repo_path = Path(path) if path else Path.cwd()
    if path:
        repo_path.mkdir(parents=True, exist_ok=True)

    args = ["init"]
    if bare:
        args.append("--bare")

    _run_git_command(args, cwd=repo_path, check=True)
    return repo_path.resolve()


def get_current_branch(cwd: str | Path | None = None) -> str:
    """
    Get the name of the current branch.

    Args:
        cwd: Working directory

    Returns:
        str: Name of the current branch

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    try:
        result = _run_git_command(
            ["symbolic-ref", "--short", "HEAD"], cwd=cwd, check=True
        )
        branch = result.stdout.strip()
        if branch:
            return branch
    except GitCommandError:
        pass

    result = _run_git_command(
        ["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd, check=True
    )
    branch = result.stdout.strip()

    if branch == "HEAD":
        try:
            result = _run_git_command(["rev-parse", "HEAD"], cwd=cwd, check=True)
            branch = result.stdout.strip()
        except GitCommandError:
            return "HEAD"

    return branch


def get_current_commit(cwd: str | Path | None = None) -> str:
    """
    Get the hash of the current commit (HEAD).

    Args:
        cwd: Working directory

    Returns:
        str: Commit hash

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    result = _run_git_command(["rev-parse", "HEAD"], cwd=cwd, check=True)
    return result.stdout.strip()


def get_short_commit(cwd: str | Path | None = None) -> str:
    """
    Get the short hash of the current commit.

    Args:
        cwd: Working directory

    Returns:
        str: Short commit hash

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    result = _run_git_command(["rev-parse", "--short", "HEAD"], cwd=cwd, check=True)
    return result.stdout.strip()


def _parse_status_porcelain_v1_z(
    output: str,
) -> tuple[list[str], list[str], list[str], list[str], list[tuple[str, str]]]:
    staged: list[str] = []
    modified: list[str] = []
    untracked: list[str] = []
    deleted: list[str] = []
    renamed: list[tuple[str, str]] = []

    staged_seen: set[str] = set()
    modified_seen: set[str] = set()
    untracked_seen: set[str] = set()
    deleted_seen: set[str] = set()
    renamed_seen: set[tuple[str, str]] = set()

    entries = output.split("\x00")
    i = 0
    while i < len(entries):
        entry = entries[i]
        if not entry:
            break

        status = entry[:2]
        path = entry[3:] if len(entry) >= 4 else ""

        if status == "??":
            if path and path not in untracked_seen:
                untracked.append(path)
                untracked_seen.add(path)
            i += 1
            continue

        index_status, worktree_status = status[0], status[1]

        if index_status in ("R", "C"):
            old_path = path
            new_path = entries[i + 1] if i + 1 < len(entries) else ""
            pair = (old_path, new_path)
            if old_path and new_path and pair not in renamed_seen:
                renamed.append(pair)
                renamed_seen.add(pair)
            i += 2
            continue

        if index_status != " ":
            if index_status == "D":
                if path and path not in deleted_seen:
                    deleted.append(path)
                    deleted_seen.add(path)
            else:
                if path and path not in staged_seen:
                    staged.append(path)
                    staged_seen.add(path)

        if worktree_status != " ":
            if worktree_status == "D":
                if path and path not in deleted_seen:
                    deleted.append(path)
                    deleted_seen.add(path)
            else:
                if path and path not in modified_seen:
                    modified.append(path)
                    modified_seen.add(path)

        i += 1

    return staged, modified, untracked, deleted, renamed


def get_status(cwd: str | Path | None = None) -> GitStatus:
    """
    Get the current git status.

    Args:
        cwd: Working directory

    Returns:
        GitStatus: Status object with information about changed files

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    branch = get_current_branch(cwd)

    result = _run_git_command(
        ["status", "--porcelain=v1", "--untracked-files=all", "-z"],
        cwd=cwd,
        check=True,
    )
    staged, modified, untracked, deleted, renamed = _parse_status_porcelain_v1_z(
        result.stdout
    )

    return GitStatus(
        branch=branch,
        staged=staged,
        modified=modified,
        untracked=untracked,
        deleted=deleted,
        renamed=renamed,
    )


def add_files(
    files: str | list[str],
    cwd: str | Path | None = None,
    update: bool = False,
    all_files: bool = False,
) -> None:
    """
    Stage files for commit.

    Args:
        files: Single file path or list of file paths
        cwd: Working directory
        update: If True, only update already tracked files
        all_files: If True, add all files (including deleted files)

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    args = ["add"]

    if update:
        args.append("-u")
    if all_files:
        args.append("-A")

    if isinstance(files, str):
        args.append(files)
    else:
        args.extend(files)

    _run_git_command(args, cwd=cwd, check=True)


def commit(
    message: str,
    cwd: str | Path | None = None,
    allow_empty: bool = False,
    amend: bool = False,
    no_verify: bool = False,
    sign_off: bool = False,
) -> str:
    """
    Create a commit.

    Args:
        message: Commit message
        cwd: Working directory
        allow_empty: If True, allow empty commits
        amend: If True, amend the previous commit
        no_verify: If True, bypass pre-commit hooks
        sign_off: If True, add Signed-off-by line

    Returns:
        str: The commit hash

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    args = ["commit", "-m", message]

    if allow_empty:
        args.append("--allow-empty")
    if amend:
        args.append("--amend")
    if no_verify:
        args.append("--no-verify")
    if sign_off:
        args.append("--signoff")

    _run_git_command(args, cwd=cwd, check=True)

    return get_current_commit(cwd)


def amend_commit(
    message: str | None = None,
    cwd: str | Path | None = None,
    no_edit: bool = False,
    no_verify: bool = False,
) -> str:
    """
    Amend the most recent commit.

    Args:
        message: New commit message (None to keep existing)
        cwd: Working directory
        no_edit: If True, don't edit the commit message
        no_verify: If True, bypass pre-commit hooks

    Returns:
        str: The amended commit hash

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    args = ["commit", "--amend"]

    if message:
        args.extend(["-m", message])
    if no_edit:
        args.append("--no-edit")
    if no_verify:
        args.append("--no-verify")

    _run_git_command(args, cwd=cwd, check=True)

    return get_current_commit(cwd)


def log(
    max_count: int | None = None,
    cwd: str | Path | None = None,
    format: str | None = None,
    author: str | None = None,
    since: str | None = None,
    until: str | None = None,
    grep: str | None = None,
) -> list[GitCommit]:
    """
    Get commit history.

    Args:
        max_count: Maximum number of commits to return
        cwd: Working directory
        format: Custom format string (default: readable format)
        author: Filter by author
        since: Show commits since this date
        until: Show commits until this date
        grep: Filter commit messages by pattern

    Returns:
        list[GitCommit]: List of commits

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    args = ["log"]

    if max_count:
        args.extend(["-n", str(max_count)])

    if format is None:
        args.extend(
            [
                "--format=%H%n%h%n%an%n%ae%n%ai%n%s%n====",
            ]
        )
    else:
        args.extend(["--format", format])

    if author:
        args.extend(["--author", author])
    if since:
        args.extend(["--since", since])
    if until:
        args.extend(["--until", until])
    if grep:
        args.extend(["--grep", grep])

    result = _run_git_command(args, cwd=cwd, check=True)

    commits: list[GitCommit] = []
    if format is None:
        blocks = result.stdout.split("====\n")
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            lines = block.split("\n")
            if len(lines) >= 6:
                commits.append(
                    GitCommit(
                        hash=lines[0],
                        short_hash=lines[1],
                        author=lines[2],
                        email=lines[3],
                        date=lines[4],
                        message="\n".join(lines[5:]),
                    )
                )

    return commits


def diff(
    file: str | None = None,
    cached: bool = False,
    ref: str | None = None,
    cwd: str | Path | None = None,
    context_lines: int | None = None,
    name_only: bool = False,
) -> str:
    """
    Show differences between commits or files.

    Args:
        file: Specific file to diff
        cached: If True, show staged changes
        ref: Optional ref to diff against (for example "HEAD")
        cwd: Working directory
        context_lines: Number of context lines
        name_only: If True, only show file names

    Returns:
        str: Diff output

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    args = ["diff"]

    if cached:
        args.append("--cached")
    if ref:
        args.append(ref)
    if context_lines:
        args.extend(["-U", str(context_lines)])
    if name_only:
        args.append("--name-only")
    if file:
        args.extend(["--", file])

    result = _run_git_command(args, cwd=cwd, check=False)
    return result.stdout


def get_numstat(
    cwd: str | Path | None = None,
    cached: bool = False,
    ref: str | None = None,
    file: str | None = None,
) -> dict[str, tuple[int, int]]:
    """
    Get the numstat for changed files (added and deleted lines per file).

    Args:
        cwd: Working directory
        cached: If True, get numstat for staged changes only
        ref: Optional ref to diff against (for example "HEAD")
        file: Optional file path to scope the diff

    Returns:
        dict: Mapping of file path to (added_lines, deleted_lines) tuple

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    args = ["diff", "--numstat"]
    if cached:
        args.append("--cached")
    if ref:
        args.append(ref)
    if file:
        args.extend(["--", file])

    result = _run_git_command(args, cwd=cwd, check=True)

    numstat = {}
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 3:
            try:
                added = int(parts[0]) if parts[0] != "-" else 0
                deleted = int(parts[1]) if parts[1] != "-" else 0
                file_path = parts[2]
                numstat[file_path] = (added, deleted)
            except ValueError:
                continue

    return numstat


def get_numstat_total(
    cwd: str | Path | None = None,
    *,
    cached: bool = False,
    ref: str | None = None,
    file: str | None = None,
) -> tuple[int, int]:
    """Get aggregated numstat totals for the current diff selection."""

    args = ["diff", "--numstat"]
    if cached:
        args.append("--cached")
    if ref:
        args.append(ref)
    if file:
        args.extend(["--", file])

    result = _run_git_command(args, cwd=cwd, check=True)

    total_added = 0
    total_deleted = 0
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        try:
            total_added += int(parts[0]) if parts[0] != "-" else 0
            total_deleted += int(parts[1]) if parts[1] != "-" else 0
        except ValueError:
            continue

    return total_added, total_deleted


def create_branch(
    name: str,
    start_point: str | None = None,
    cwd: str | Path | None = None,
) -> str:
    """
    Create a new branch.

    Args:
        name: Branch name
        start_point: Starting point (commit hash or branch name)
        cwd: Working directory

    Returns:
        str: Name of the created branch

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    args = ["branch", name]

    if start_point:
        args.append(start_point)

    _run_git_command(args, cwd=cwd, check=True)

    return name


def list_branches(
    cwd: str | Path | None = None,
    remote: bool = False,
    all_branches: bool = False,
) -> list[GitBranch]:
    """
    List branches.

    Args:
        cwd: Working directory
        remote: If True, list remote branches
        all_branches: If True, list all branches (local and remote)

    Returns:
        list[GitBranch]: List of branches

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    if remote:
        ref_prefixes = ["refs/remotes"]
    elif all_branches:
        ref_prefixes = ["refs/heads", "refs/remotes"]
    else:
        ref_prefixes = ["refs/heads"]

    fmt = "%(refname)%00%(refname:short)%00%(HEAD)%00%(objectname)%00%(upstream:short)"
    result = _run_git_command(
        ["for-each-ref", f"--format={fmt}", *ref_prefixes],
        cwd=cwd,
        check=True,
    )

    branches: list[GitBranch] = []
    for line in result.stdout.splitlines():
        parts = line.split("\x00")
        if len(parts) < 4:
            continue

        refname = parts[0]
        name = parts[1]
        is_current = parts[2] == "*"
        commit_hash = parts[3]
        upstream = parts[4] if len(parts) > 4 and parts[4] else None

        branches.append(
            GitBranch(
                name=name,
                is_current=is_current,
                is_remote=refname.startswith("refs/remotes/"),
                commit=commit_hash or None,
                upstream=upstream,
            )
        )

    return branches


def switch_branch(
    name: str,
    cwd: str | Path | None = None,
    create: bool = False,
    force: bool = False,
) -> str:
    """
    Switch to a branch.

    Args:
        name: Branch name
        cwd: Working directory
        create: If True, create and switch to new branch
        force: If True, discard local changes

    Returns:
        str: Name of the switched-to branch

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    args = ["switch"]

    if create:
        args.append("-c")
    if force:
        args.append("--force")

    args.append(name)

    _run_git_command(args, cwd=cwd, check=True)

    return name


def delete_branch(
    name: str,
    cwd: str | Path | None = None,
    force: bool = False,
) -> None:
    """
    Delete a branch.

    Args:
        name: Branch name
        cwd: Working directory
        force: If True, force delete even if not merged

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    args = ["branch"]

    if force:
        args.append("-D")
    else:
        args.append("-d")

    args.append(name)

    _run_git_command(args, cwd=cwd, check=True)


def merge_branch(
    branch: str,
    cwd: str | Path | None = None,
    message: str | None = None,
    no_ff: bool = False,
    squash: bool = False,
) -> None:
    """
    Merge a branch into the current branch.

    Args:
        branch: Branch to merge
        cwd: Working directory
        message: Merge commit message
        no_ff: If True, always create a merge commit
        squash: If True, squash all commits

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    args = ["merge"]

    if message:
        args.extend(["-m", message])
    if no_ff:
        args.append("--no-ff")
    if squash:
        args.append("--squash")

    args.append(branch)

    _run_git_command(args, cwd=cwd, check=True)


def list_remotes(cwd: str | Path | None = None) -> list[GitRemote]:
    """
    List remote repositories.

    Args:
        cwd: Working directory

    Returns:
        list[GitRemote]: List of remotes

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    result = _run_git_command(["remote", "-v"], cwd=cwd, check=True)

    remotes: dict[str, GitRemote] = {}

    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3:
            name = parts[0]
            url = parts[1]
            fetch_or_push = parts[2].rstrip(")")

            if name not in remotes:
                remotes[name] = GitRemote(name=name, fetch_url=url, push_url=url)

            if fetch_or_push == "(fetch":
                remotes[name].fetch_url = url
            elif fetch_or_push == "(push":
                remotes[name].push_url = url

    return list(remotes.values())


def add_remote(
    name: str,
    url: str,
    cwd: str | Path | None = None,
    fetch: bool = True,
) -> None:
    """
    Add a remote repository.

    Args:
        name: Remote name
        url: Remote URL
        cwd: Working directory
        fetch: If True, fetch after adding

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    args = ["remote", "add"]
    if fetch:
        args.append("-f")
    args.extend([name, url])

    _run_git_command(args, cwd=cwd, check=True)


def remove_remote(name: str, cwd: str | Path | None = None) -> None:
    """
    Remove a remote repository.

    Args:
        name: Remote name
        cwd: Working directory

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    _run_git_command(["remote", "remove", name], cwd=cwd, check=True)


def fetch(
    remote: str | None = None,
    branch: str | None = None,
    cwd: str | Path | None = None,
    all_branches: bool = False,
    prune: bool = False,
    env: dict[str, str] | None = None,
) -> None:
    """
    Fetch from remote repository.

    Args:
        remote: Remote name
        branch: Branch name
        cwd: Working directory
        all_branches: If True, fetch all remotes
        prune: If True, remove remote-tracking branches that no longer exist

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    args = ["fetch"]

    if all_branches:
        args.append("--all")
    if prune:
        args.append("--prune")

    if remote:
        args.append(remote)
        if branch:
            args.append(branch)

    _run_git_command(args, cwd=cwd, check=True, env=env)


def pull(
    remote: str | None = None,
    branch: str | None = None,
    cwd: str | Path | None = None,
    rebase: bool = False,
    fast_forward_only: bool = False,
) -> None:
    """
    Pull changes from remote repository.

    Args:
        remote: Remote name
        branch: Branch name
        cwd: Working directory
        rebase: If True, use rebase instead of merge
        fast_forward_only: If True, only fast-forward

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    args = ["pull"]

    if rebase:
        args.append("--rebase")
    if fast_forward_only:
        args.append("--ff-only")

    if remote:
        args.append(remote)
        if branch:
            args.append(branch)

    _run_git_command(args, cwd=cwd, check=True)


def push(
    remote: str = "origin",
    branch: str | None = None,
    cwd: str | Path | None = None,
    force: bool = False,
    all_branches: bool = False,
    tags: bool = False,
    set_upstream: bool = False,
) -> None:
    """
    Push changes to remote repository.

    Args:
        remote: Remote name
        branch: Branch name
        cwd: Working directory
        force: If True, force push
        all_branches: If True, push all branches
        tags: If True, push tags
        set_upstream: If True, set upstream tracking

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    args = ["push"]

    if force:
        args.append("--force")
    if all_branches:
        args.append("--all")
    if tags:
        args.append("--tags")
    if set_upstream:
        args.append("--set-upstream")

    args.append(remote)

    if branch:
        args.append(branch)

    _run_git_command(args, cwd=cwd, check=True)


def clone(
    url: str,
    path: str | Path | None = None,
    branch: str | None = None,
    depth: int | None = None,
    single_branch: bool = False,
    bare: bool = False,
    env: dict[str, str] | None = None,
) -> Path:
    """
    Clone a repository.

    Args:
        url: Repository URL
        path: Destination path
        branch: Branch to checkout
        depth: Number of commits to fetch (shallow clone)
        single_branch: If True, clone only one branch
        bare: If True, create a bare repository

    Returns:
        Path: Path to the cloned repository

    Raises:
        GitError: If clone fails
    """
    args = ["clone"]

    if branch:
        args.extend(["--branch", branch])
    if depth:
        args.extend(["--depth", str(depth)])
    if single_branch:
        args.append("--single-branch")
    if bare:
        args.append("--bare")

    args.append(url)

    if path:
        args.append(str(path))

    _run_git_command(args, check=True, env=env)

    repo_path = Path(path) if path else Path(url.split("/")[-1].replace(".git", ""))
    return repo_path.resolve()


def stash(
    message: str | None = None,
    cwd: str | Path | None = None,
    include_untracked: bool = False,
    keep_index: bool = False,
) -> str:
    """
    Stash changes.

    Args:
        message: Stash message
        cwd: Working directory
        include_untracked: If True, include untracked files
        keep_index: If True, keep staged changes

    Returns:
        str: Stash reference

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    before = list_stash(cwd)

    args = ["stash", "push"]

    if message:
        args.extend(["-m", message])
    if include_untracked:
        args.append("-u")
    if keep_index:
        args.append("-k")

    _run_git_command(args, cwd=cwd, check=True)

    after = list_stash(cwd)
    if len(after) > len(before):
        return after[0]
    return ""


def list_stash(cwd: str | Path | None = None) -> list[str]:
    """
    List stashes.

    Args:
        cwd: Working directory

    Returns:
        list[str]: List of stash references

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    result = _run_git_command(["stash", "list"], cwd=cwd, check=True)
    stashes: list[str] = []
    for line in result.stdout.splitlines():
        if line:
            parts = line.split(":")
            if parts:
                stashes.append(parts[0].strip())

    return stashes


def pop_stash(
    index: int | None = None,
    cwd: str | Path | None = None,
) -> None:
    """
    Pop a stash.

    Args:
        index: Stash index (default: latest)
        cwd: Working directory

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    args = ["stash", "pop"]

    if index is not None:
        args.append(f"stash@{{{index}}}")

    _run_git_command(args, cwd=cwd, check=True)


def drop_stash(
    index: int | None = None,
    cwd: str | Path | None = None,
) -> None:
    """
    Drop a stash.

    Args:
        index: Stash index (default: latest)
        cwd: Working directory

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    args = ["stash", "drop"]

    if index is not None:
        args.append(f"stash@{{{index}}}")

    _run_git_command(args, cwd=cwd, check=True)


def create_tag(
    name: str,
    message: str | None = None,
    cwd: str | Path | None = None,
    annotated: bool = True,
    force: bool = False,
    commit: str | None = None,
) -> str:
    """
    Create a tag.

    Args:
        name: Tag name
        message: Tag message (for annotated tags)
        cwd: Working directory
        annotated: If True, create an annotated tag
        force: If True, overwrite existing tag
        commit: Commit to tag (default: HEAD)

    Returns:
        str: Tag name

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    args = ["tag"]

    if annotated:
        args.append("-a")
        if message:
            args.extend(["-m", message])
    if force:
        args.append("--force")

    args.append(name)

    if commit:
        args.append(commit)

    _run_git_command(args, cwd=cwd, check=True)

    return name


def list_tags(
    cwd: str | Path | None = None,
    pattern: str | None = None,
) -> list[str]:
    """
    List tags.

    Args:
        cwd: Working directory
        pattern: Filter tags by pattern (e.g., "v*")

    Returns:
        list[str]: List of tag names

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    args = ["tag"]

    if pattern:
        args.append(f"--list={pattern}")

    result = _run_git_command(args, cwd=cwd, check=True)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def delete_tag(
    name: str,
    cwd: str | Path | None = None,
    remote: str | None = None,
) -> None:
    """
    Delete a tag.

    Args:
        name: Tag name
        cwd: Working directory
        remote: If provided, delete tag from remote

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    if remote:
        _ = _run_git_command(
            ["push", remote, "--delete", f"refs/tags/{name}"], cwd=cwd, check=True
        )
    else:
        _ = _run_git_command(["tag", "-d", name], cwd=cwd, check=True)


def reset(
    mode: str = "soft",
    commit: str = "HEAD",
    cwd: str | Path | None = None,
) -> None:
    """
    Reset current HEAD to the specified state.

    Args:
        mode: Reset mode: "soft", "mixed", or "hard"
        commit: Commit to reset to
        cwd: Working directory

    Raises:
        GitNotRepositoryError: If not a git repository
        GitError: If mode is invalid
    """
    if mode not in ("soft", "mixed", "hard"):
        raise GitError(f"Invalid reset mode: {mode}")

    args = ["reset", f"--{mode}", commit]

    _run_git_command(args, cwd=cwd, check=True)


def revert(
    commits: str | list[str],
    cwd: str | Path | None = None,
    no_commit: bool = False,
) -> None:
    """
    Revert commits.

    Args:
        commits: Single commit hash or list of commit hashes
        cwd: Working directory
        no_commit: If True, don't create commit

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    args = ["revert"]

    if no_commit:
        args.append("--no-commit")

    if isinstance(commits, str):
        args.append(commits)
    else:
        args.extend(commits)

    _run_git_command(args, cwd=cwd, check=True)


def rebase(
    branch: str,
    cwd: str | Path | None = None,
    interactive: bool = False,
    onto: str | None = None,
    upstream: str | None = None,
) -> None:
    """
    Rebase current branch onto another branch.

    Args:
        branch: Branch to rebase onto
        cwd: Working directory
        interactive: If True, start interactive rebase
        onto: New base commit
        upstream: Upstream branch

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    args = ["rebase"]

    if interactive:
        args.append("-i")
    if onto:
        args.extend(["--onto", onto])
    if upstream:
        args.append(upstream)
    else:
        args.append(branch)

    _run_git_command(args, cwd=cwd, check=True)


def cherry_pick(
    commits: str | list[str],
    cwd: str | Path | None = None,
    no_commit: bool = False,
) -> None:
    """
    Cherry-pick commits.

    Args:
        commits: Single commit hash or list of commit hashes
        cwd: Working directory
        no_commit: If True, don't create commit

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    args = ["cherry-pick"]

    if no_commit:
        args.append("--no-commit")

    if isinstance(commits, str):
        args.append(commits)
    else:
        args.extend(commits)

    _run_git_command(args, cwd=cwd, check=True)


def clean(
    cwd: str | Path | None = None,
    force: bool = False,
    directories: bool = False,
    dry_run: bool = False,
) -> list[str]:
    """
    Remove untracked files from the working tree.

    Args:
        cwd: Working directory
        force: If True, force remove
        directories: If True, also remove directories
        dry_run: If True, only show what would be removed

    Returns:
        list[str]: List of files that would be/can be removed

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    args = ["clean"]

    if force:
        args.append("-f")
    if directories:
        args.append("-d")
    if dry_run:
        args.append("-n")

    result = _run_git_command(args, cwd=cwd, check=True)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def checkout(
    ref: str,
    cwd: str | Path | None = None,
    create_branch: bool = False,
    force: bool = False,
) -> str:
    """
    Checkout a branch or commit.

    Args:
        ref: Branch name or commit hash
        cwd: Working directory
        create_branch: If True, create and checkout new branch
        force: If True, discard local changes

    Returns:
        str: The checked-out reference

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    args = ["checkout"]

    if create_branch:
        args.append("-b")
    if force:
        args.append("-f")

    args.append(ref)

    _run_git_command(args, cwd=cwd, check=True)

    return ref


def remote_url(name: str = "origin", cwd: str | Path | None = None) -> str:
    """
    Get the URL of a remote repository.

    Args:
        name: Remote name
        cwd: Working directory

    Returns:
        str: Remote URL

    Raises:
        GitNotRepositoryError: If not a git repository
        GitError: If remote not found
    """
    try:
        result = _run_git_command(["remote", "get-url", name], cwd=cwd, check=True)
        return result.stdout.strip()
    except GitCommandError as e:
        raise GitError(f"Remote '{name}' not found") from e


def show_file_at_commit(
    file_path: str,
    commit: str = "HEAD",
    cwd: str | Path | None = None,
) -> str:
    """
    Show file content at a specific commit.

    Args:
        file_path: Path to the file
        commit: Commit hash or reference
        cwd: Working directory

    Returns:
        str: File content

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    result = _run_git_command(["show", f"{commit}:{file_path}"], cwd=cwd, check=False)
    return result.stdout


def blame(
    file_path: str,
    line: int | None = None,
    cwd: str | Path | None = None,
) -> str:
    """
    Show who modified each line of a file.

    Args:
        file_path: Path to the file
        line: Specific line to blame
        cwd: Working directory

    Returns:
        str: Blame output

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    args = ["blame", file_path]

    if line is not None:
        args.extend(["-L", f"{line},{line}"])

    result = _run_git_command(args, cwd=cwd, check=True)
    return result.stdout


def count_commits(
    since: str | None = None,
    until: str | None = None,
    author: str | None = None,
    cwd: str | Path | None = None,
) -> int:
    """
    Count commits in the repository.

    Args:
        since: Count commits since this date
        until: Count commits until this date
        author: Filter by author
        cwd: Working directory

    Returns:
        int: Number of commits

    Raises:
        GitNotRepositoryError: If not a git repository
    """
    args = ["rev-list", "--count"]

    if since:
        args.extend(["--since", since])
    if until:
        args.extend(["--until", until])
    if author:
        args.extend(["--author", author])

    args.append("HEAD")

    result = _run_git_command(args, cwd=cwd, check=True)
    return int(result.stdout.strip())


def get_config(
    key: str,
    cwd: str | Path | None = None,
    global_config: bool = False,
) -> str:
    """
    Get a git configuration value.

    Args:
        key: Configuration key (e.g., "user.name")
        cwd: Working directory
        global_config: If True, get global config instead of local

    Returns:
        str: Configuration value

    Raises:
        GitError: If key not found
    """
    args = ["config"]

    if global_config:
        args.append("--global")
    else:
        args.append("--local")

    args.extend(["--get", key])

    try:
        result = _run_git_command(args, cwd=cwd, check=True)
        return result.stdout.strip()
    except GitCommandError:
        raise GitError(f"Configuration key '{key}' not found") from None


def set_config(
    key: str,
    value: str,
    cwd: str | Path | None = None,
    global_config: bool = False,
) -> None:
    """
    Set a git configuration value.

    Args:
        key: Configuration key
        value: Configuration value
        cwd: Working directory
        global_config: If True, set global config instead of local

    Raises:
        GitError: If setting fails
    """
    args = ["config"]

    if global_config:
        args.append("--global")
    else:
        args.append("--local")

    args.extend([key, value])

    _run_git_command(args, cwd=cwd, check=True)
