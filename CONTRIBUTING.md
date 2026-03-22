# Poco Contribution Guide (PR & Development Standards)

This document describes the contribution process for the Poco repository and the development standards that must be followed when submitting code.

与仓库治理、发布、Docker、CI/CD、分支策略相关的正式规则，请同时参考：

- [仓库治理草案](docs/repository-governance.md)

## 1. 标准贡献流程

1. 先同步最新代码并从 `main` 创建分支。
2. 在单一主题分支中开发，避免把不相关改动放在同一个 PR。
3. 如改动涉及治理、发布、Docker、CI/CD 或仓库自动化，先阅读治理文档再修改。
4. 本地完成自检（见“提交前检查”）。
5. 推送分支并发起 PR 到 `main`。
6. 维护者进行 Review，提出修改意见。
7. 修改后继续 push 到同一分支，直到 Review 通过并由维护者合并。

## 2. Branch and Commit Standards

It is recommended to use semantic branch names:

- `feat/<short-description>`
- `fix/<short-description>`
- `refactor/<short-description>`
- `docs/<short-description>`
- `chore/<short-description>`

推荐保持短分支工作流，不直接向 `main` 推送日常改动。

提交信息建议遵循 Conventional Commits（与仓库现有历史一致）：

- `feat: ...`
- `fix: ...`
- `refactor: ...`
- `docs: ...`
- `chore: ...`

Recommendations:

- Each commit should focus on one logical point.
- Avoid mixing refactoring, formatting, and feature changes in the same commit.

## 3. PR 标题与合并建议

建议 PR 标题使用 Conventional Commits：

```text
<type>(<optional-scope>): <summary>
```

推荐 `type`：

- `feat`
- `fix`
- `docs`
- `refactor`
- `test`
- `build`
- `ci`
- `chore`
- `perf`
- `revert`

当前仓库已通过 GitHub Actions 对 PR 标题进行校验，因此建议在创建 PR 前先自行确认标题格式。

推荐 `scope`：

- `repo`
- `backend`
- `executor`
- `executor-manager`
- `frontend`
- `im`
- `docker`
- `docs`
- `ci`

建议优先使用 **squash merge**，保证 `main` 历史保持清晰、聚焦。

## 4. Review 路由与标签

- 核心目录当前已由 [CODEOWNERS](.github/CODEOWNERS) 覆盖。
- 文档类变更当前会通过 labeler 自动标记为 `documentation`。
- 其他路径级 label 规则会在仓库 labels 体系补齐后逐步扩展。

## 5. 提交前检查

Run in the repository root:

```bash
pre-commit run --all-files
```

If you modified the frontend, also run:

```bash
cd frontend
pnpm lint
pnpm build
```

If you modified Python services (`backend`/`executor`/`executor_manager`), please install dependencies and verify the service can start:

```bash
cd <service>
uv sync
uv run python -m app.main
```

If you modified database models, handle migrations as follows (in the `backend` directory):

```bash
uv run -m alembic revision --autogenerate -m "description"
uv run -m alembic upgrade head
```

Then manually verify the auto-generated migration meets expectations.

## 6. PR 描述建议模板

It is recommended to include at least the following in your PR description:

- Background and goals of the changes
- Main changes
- Affected areas (frontend/backend/executor/executor_manager)
- Local verification commands and results
- If UI changes: provide screenshots or recordings
- If database changes: provide migration and rollback instructions
- If breaking changes: clearly state upgrade considerations

仓库现在提供了默认 PR 模板：

- [PR 模板](.github/pull_request_template.md)

## 7. 开发规范

### 5.1 General Standards

- 不提交密钥、令牌、私有配置或任何敏感信息。
- 新增功能时，同步更新相关文档（README、docs 或 API 文档）。
- 保持改动最小化，优先修复根因，不做无关重构。
- 修改仓库治理、发布、Docker、CI/CD、版本策略时，必须同步更新相关文档。

### 5.2 Python (Backend Services)

- Python version: `3.12+`
- Must write complete type annotations, prefer built-in generics: `list[T]`, `dict[str, Any]`, `X | None`.
- Code comments must be in English; Docstrings follow Google style.

Backend layering standards (`backend`):

- `repositories/` - Database CRUD only, no business logic.
- `services/` - Business orchestration and transaction management.
- `services/` returns SQLAlchemy Model or Pydantic Schema, not raw `dict[str, Any]`.
- Database sessions are created via FastAPI dependency injection at the API layer, then passed to services/repositories.

Exception handling standards (`backend`):

- Business errors use `AppException`.
- HTTP semantic errors use `HTTPException`.
- Do not catch generic `Exception` and wrap it as `HTTPException(500, ...)`.

### 5.3 Frontend (Next.js)

- Use Tailwind CSS v4 with design variables (`frontend/app/globals.css`).
- Do not hardcode colors, shadows, or border-radius; prefer design tokens (e.g., `var(--primary)`, `var(--shadow-md)`, `var(--radius)`).
- All user-facing text must go through i18n; do not write hardcoded strings.
- i18n related paths:
  - `frontend/lib/i18n/client.ts`
  - `frontend/lib/i18n/settings.ts`
  - `frontend/lib/i18n/locales/*/translation.json`

## 8. Review 与合并标准

Usually ready to merge when:

- Change goals are clear, PR description is complete.
- Local checks pass, and verification steps are reproducible.
- Code follows layering and style standards.
- Necessary documentation is updated.
- Review comments are addressed or consensus is reached.

最终合并由仓库维护者执行。

## 9. 发布与治理说明

- release 当前以 `main` 上的 tag 为入口。
- Docker 镜像发布当前由 GitHub Actions 在 `v*` tag 上执行。
- 涉及分支策略、发布策略、Docker 行为、CI/CD 自动化、仓库规则的改动，请以 [仓库治理草案](docs/repository-governance.md) 为准，并同步更新相关文档。
