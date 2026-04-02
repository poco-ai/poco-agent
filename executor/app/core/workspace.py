import hashlib
import logging
import os
import shutil
import stat
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from app.schemas.request import TaskConfig
from app.utils.git.operations import (
    GitCommandError,
    GitError,
    clone,
    fetch,
    init_repository,
    is_repository,
    checkout,
    sparse_checkout_init,
    sparse_checkout_set,
    worktree_add,
    worktree_prune,
    worktree_remove,
)

logger = logging.getLogger(__name__)

DEFAULT_GIT_EXCLUDES = [
    # VCS metadata
    ".git/",
    ".hg/",
    ".svn/",
    # OS / editor junk
    ".DS_Store",
    "__pycache__/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    # Common dependency/build outputs
    "node_modules/",
    ".venv/",
    "venv/",
    ".next/",
    "dist/",
    "build/",
    # Agent/runtime artifacts
    ".claude_data/",
    ".claude/",
    "inputs/",
]


class WorkspaceManager:
    def __init__(self, mount_path: str = "/workspace"):
        self.root_path = Path(mount_path)
        self.work_path = self.root_path
        self.claude_config_path = self.root_path / ".claude"
        self.inputs_root = self.root_path / "inputs"

        self.persistent_claude_data = self.root_path / ".claude_data"
        self.system_claude_home = Path.home() / ".claude"
        self._git_askpass_path: str | None = None
        self._worktree_paths: list[Path] = []  # Track created worktrees for cleanup

    async def prepare(self, config: TaskConfig):
        if not self.root_path.exists():
            self.root_path.mkdir(parents=True, exist_ok=True)

        await self._setup_session_persistence()
        self.work_path = self._prepare_repository(config)
        self._ensure_inputs_dir(self.work_path)
        self._ensure_git_excludes(self.work_path)

    async def _setup_session_persistence(self):
        self.persistent_claude_data.mkdir(exist_ok=True)

        if self.system_claude_home.exists() or self.system_claude_home.is_symlink():
            if self.system_claude_home.is_symlink():
                self.system_claude_home.unlink()
            else:
                shutil.rmtree(self.system_claude_home)

        self.system_claude_home.symlink_to(self.persistent_claude_data)

    async def cleanup(self):
        # Restore system ~/.claude if it was symlinked
        if self.system_claude_home.is_symlink():
            self.system_claude_home.unlink()
        # Best-effort cleanup for temporary askpass helper.
        if self._git_askpass_path:
            try:
                Path(self._git_askpass_path).unlink(missing_ok=True)
            except Exception:
                pass
            self._git_askpass_path = None

        # Clean up worktrees created during this session
        for wt_path in self._worktree_paths:
            try:
                if wt_path.exists():
                    worktree_remove(wt_path, force=True)
            except Exception as exc:
                logger.warning(f"Failed to remove worktree {wt_path}: {exc}")
        self._worktree_paths.clear()

        # Prune stale worktree references in main repos
        cache_dir = self.root_path / ".cache" / "repos"
        if cache_dir.exists():
            for main_repo in cache_dir.iterdir():
                if main_repo.is_dir() and is_repository(main_repo):
                    try:
                        worktree_prune(cwd=main_repo)
                    except Exception:
                        pass

    def _prepare_repository(self, config: TaskConfig) -> Path:
        strategy = (getattr(config, "workspace_strategy", None) or "clone").strip()
        if strategy == "worktree":
            try:
                return self._prepare_worktree(config)
            except Exception as exc:
                logger.warning(
                    "workspace_strategy_worktree_fallback_clone",
                    extra={"error": str(exc)},
                )
                return self._prepare_repository_via_clone(config)
        if strategy in {"sparse-clone", "sparse-worktree"}:
            try:
                return self._prepare_sparse_checkout(config)
            except Exception as exc:
                logger.warning(
                    "workspace_strategy_sparse_fallback_clone",
                    extra={"error": str(exc)},
                )
                return self._prepare_repository_via_clone(config)
        return self._prepare_repository_via_clone(config)

    def _prepare_repository_via_clone(self, config: TaskConfig) -> Path:
        repo_url = (config.repo_url or "").strip()
        if repo_url:
            return self._ensure_cloned_repo(
                repo_url,
                config.git_branch,
                git_token=(config.git_token or "").strip() or None,
            )

        self._ensure_git_repo(self.root_path)
        return self.root_path

    def _prepare_worktree(self, config: TaskConfig) -> Path:
        """Prepare a worktree from a cached main repository.

        Workflow:
        1. Ensure main repo exists (clone --bare if needed)
        2. Fetch target branch
        3. Create worktree pointing to that branch
        """
        repo_url = (config.repo_url or "").strip()
        if not repo_url:
            return self._prepare_repository_via_clone(config)

        # 1. Ensure main repo exists
        main_repo = self._ensure_main_repo(
            repo_url,
            git_token=(config.git_token or "").strip() or None,
        )

        # 2. Fetch target branch
        git_env = self._build_git_env(repo_url, config.git_token)
        branch = config.git_branch or "main"
        try:
            fetch(remote="origin", branch=branch, cwd=main_repo, env=git_env)
        except (GitCommandError, GitError) as exc:
            logger.warning(f"Failed to fetch branch {branch}: {exc}")
            # Try without specifying branch (fetch all)
            fetch(remote="origin", cwd=main_repo, env=git_env)

        # 3. Create unique worktree path
        repo_hash = self._get_repo_hash(repo_url)
        session_id = getattr(config, "session_id", None) or "default"
        worktree_path = (
            self.root_path / "worktrees" / repo_hash / str(session_id)
        )
        worktree_path.parent.mkdir(parents=True, exist_ok=True)

        # 4. Create worktree
        try:
            worktree_add(worktree_path, branch, cwd=main_repo, force=True)
        except (GitCommandError, GitError) as exc:
            # If branch doesn't exist locally, try creating it from remote
            logger.warning(f"Worktree add failed, trying to create branch: {exc}")
            # Fallback to clone strategy
            raise RuntimeError(f"Failed to create worktree: {exc}") from exc

        self._worktree_paths.append(worktree_path)
        return worktree_path

    def _prepare_sparse_checkout(self, config: TaskConfig) -> Path:
        """Prepare a sparse checkout repository.

        Workflow:
        1. Clone repository (shallow if possible)
        2. Initialize sparse checkout
        3. Set sparse paths
        """
        repo_url = (config.repo_url or "").strip()
        if not repo_url:
            return self._prepare_repository_via_clone(config)

        repo_path = self._derive_repo_path(repo_url)
        git_env = self._build_git_env(repo_url, config.git_token)

        # 1. Clone if not exists
        if not repo_path.exists() or not is_repository(repo_path):
            try:
                clone(
                    repo_url,
                    path=repo_path,
                    branch=config.git_branch,
                    depth=1,
                    env=git_env,
                )
            except (GitCommandError, GitError, OSError) as exc:
                detail = str(exc)
                if len(detail) > 2000:
                    detail = detail[:2000] + "…"
                raise RuntimeError(
                    f"Failed to clone repository for sparse checkout: {repo_url}. {detail}"
                ) from exc
        else:
            # Repo exists, just checkout branch
            self._checkout_branch(repo_path, config.git_branch, env=git_env)

        # 2. Initialize sparse checkout
        try:
            sparse_checkout_init(cwd=repo_path, cone=True)
        except (GitCommandError, GitError) as exc:
            logger.warning(f"Failed to init sparse checkout: {exc}")
            # Continue without sparse - still return valid repo
            return repo_path

        # 3. Set sparse paths
        sparse_paths = config.workspace_sparse_paths or []
        if sparse_paths:
            try:
                sparse_checkout_set(sparse_paths, cwd=repo_path)
            except (GitCommandError, GitError) as exc:
                logger.warning(f"Failed to set sparse paths: {exc}")

        return repo_path

    def _ensure_cloned_repo(
        self,
        repo_url: str,
        branch: str | None,
        *,
        git_token: str | None,
    ) -> Path:
        repo_path = self._derive_repo_path(repo_url)
        git_env = self._build_git_env(repo_url, git_token)

        if repo_path.exists() and is_repository(repo_path):
            self._checkout_branch(repo_path, branch, env=git_env)
            return repo_path

        if repo_path.exists() and not is_repository(repo_path):
            raise RuntimeError(
                f"Target path exists but is not a git repository: {repo_path}"
            )

        try:
            return clone(repo_url, path=repo_path, branch=branch, env=git_env)
        except (GitCommandError, GitError, OSError) as exc:
            detail = str(exc)
            # Keep the error message compact for the UI.
            if len(detail) > 2000:
                detail = detail[:2000] + "…"
            raise RuntimeError(
                f"Failed to clone repository: {repo_url}. {detail}"
            ) from exc

    def _build_git_env(self, repo_url: str, git_token: str | None) -> dict[str, str]:
        """Build a per-command env map for git operations.

        Notes:
        - The token is injected by Executor Manager at runtime and must never be persisted.
        - We only apply the token to https://github.com/* URLs to avoid credential leakage.
        """
        env: dict[str, str] = {"GIT_TERMINAL_PROMPT": "0"}
        if not git_token:
            return env

        try:
            parsed = urlparse(repo_url)
        except Exception:
            return env

        host = (parsed.netloc or "").strip().lower()
        if parsed.scheme not in ("http", "https") or host not in {
            "github.com",
            "www.github.com",
        }:
            return env

        askpass = self._ensure_git_askpass()
        env.update(
            {
                "GIT_ASKPASS": askpass,
                # Used by the askpass script.
                "POCO_GIT_USERNAME": "x-access-token",
                "POCO_GIT_TOKEN": git_token,
            }
        )
        return env

    def _ensure_git_askpass(self) -> str:
        """Create a reusable askpass helper script (no secrets embedded)."""
        if self._git_askpass_path and Path(self._git_askpass_path).exists():
            return self._git_askpass_path

        script = """#!/bin/sh
prompt=\"$1\"
case \"$prompt\" in
  *Username*) echo \"${POCO_GIT_USERNAME:-x-access-token}\" ;;
  *) echo \"${POCO_GIT_TOKEN:-}\" ;;
esac
"""
        fd, path = tempfile.mkstemp(prefix="poco-git-askpass-", text=True)
        os.close(fd)
        p = Path(path)
        p.write_text(script, encoding="utf-8")
        p.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        self._git_askpass_path = path
        return path

    def _derive_repo_path(self, repo_url: str) -> Path:
        clean = repo_url.split("?", 1)[0].split("#", 1)[0].rstrip("/")
        name = clean.split("/")[-1] if clean else "repo"
        if name.endswith(".git"):
            name = name[: -len(".git")]
        if not name or name in (".", ".."):
            name = "repo"
        return self.root_path / name

    @staticmethod
    def _ensure_git_repo(path: Path) -> None:
        if is_repository(path):
            return
        try:
            init_repository(path)
        except Exception as exc:
            logger.warning(f"Failed to init git repository at {path}: {exc}")

    @staticmethod
    def _checkout_branch(
        path: Path, branch: str | None, *, env: dict[str, str] | None = None
    ) -> None:
        if not branch:
            return
        try:
            fetch(remote="origin", branch=branch, cwd=path, env=env)
            checkout(branch, cwd=path)
        except (GitCommandError, GitError, OSError) as exc:
            detail = str(exc)
            if len(detail) > 2000:
                detail = detail[:2000] + "…"
            raise RuntimeError(
                f"Failed to checkout branch '{branch}' for repo at {path}. {detail}"
            ) from exc

    def _ensure_git_excludes(self, repo_path: Path) -> None:
        if not is_repository(repo_path):
            return

        extra = os.environ.get("WORKSPACE_GIT_IGNORE", "")
        patterns = list(DEFAULT_GIT_EXCLUDES)
        if extra:
            for raw in extra.replace(",", "\n").splitlines():
                value = raw.strip()
                if value:
                    patterns.append(value)

        if not patterns:
            return

        exclude_path = repo_path / ".git" / "info" / "exclude"
        exclude_path.parent.mkdir(parents=True, exist_ok=True)
        existing: set[str] = set()
        if exclude_path.exists():
            try:
                existing = {
                    line.strip()
                    for line in exclude_path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                }
            except Exception as exc:
                logger.warning(f"Failed to read git exclude file {exclude_path}: {exc}")
                existing = set()

        to_add = [p for p in patterns if p not in existing]
        if not to_add:
            return

        try:
            content = ""
            if exclude_path.exists():
                content = exclude_path.read_text(encoding="utf-8")
                if content and not content.endswith("\n"):
                    content += "\n"
            content += "\n".join(to_add) + "\n"
            exclude_path.write_text(content, encoding="utf-8")
        except Exception as exc:
            logger.warning(f"Failed to update git exclude file {exclude_path}: {exc}")

    def _ensure_inputs_dir(self, repo_path: Path) -> None:
        try:
            self.inputs_root.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.warning(
                f"Failed to create inputs directory {self.inputs_root}: {exc}"
            )
            return

        if repo_path == self.root_path:
            return

        link_path = repo_path / "inputs"
        if link_path.exists():
            return
        try:
            link_path.symlink_to(self.inputs_root)
        except Exception as exc:
            logger.warning(f"Failed to link inputs directory {link_path}: {exc}")

    # =========================================================================
    # Worktree / Sparse Checkout Helpers
    # =========================================================================

    def _get_repo_hash(self, repo_url: str) -> str:
        """Generate a unique hash for a repository URL."""
        clean = repo_url.split("?", 1)[0].split("#", 1)[0].rstrip("/")
        return hashlib.sha256(clean.encode("utf-8")).hexdigest()[:16]

    def _get_main_repo_path(self, repo_url: str) -> Path:
        """Get the path to the cached main repository (bare repo for worktrees)."""
        repo_hash = self._get_repo_hash(repo_url)
        return self.root_path / ".cache" / "repos" / repo_hash

    def _ensure_main_repo(self, repo_url: str, git_token: str | None) -> Path:
        """Ensure a bare main repository exists for worktree creation.

        Returns the path to the main repository.
        """
        main_repo = self._get_main_repo_path(repo_url)
        git_env = self._build_git_env(repo_url, git_token)

        if main_repo.exists() and is_repository(main_repo):
            # Already exists, just fetch latest
            try:
                fetch(remote="origin", cwd=main_repo, env=git_env)
            except Exception as exc:
                logger.warning(f"Failed to fetch main repo: {exc}")
            return main_repo

        # Clone as bare repository (better for worktrees)
        main_repo.parent.mkdir(parents=True, exist_ok=True)

        try:
            clone(
                repo_url,
                path=main_repo,
                bare=True,
                env=git_env,
            )
        except (GitCommandError, GitError, OSError) as exc:
            detail = str(exc)
            if len(detail) > 2000:
                detail = detail[:2000] + "…"
            raise RuntimeError(
                f"Failed to clone main repository: {repo_url}. {detail}"
            ) from exc

        return main_repo
