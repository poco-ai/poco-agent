# Poco 贡献指南（PR 与开发规范）

本文档说明 Poco 仓库的贡献流程，以及提交代码时需要遵循的开发规范。

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

## 2. 分支与提交规范

建议使用语义化分支名：

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

建议：

- 单次 commit 尽量聚焦一个逻辑点。
- 避免在同一个 commit 中混入重构、格式化、功能改动三类内容。

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

## 4. 提交前检查

在仓库根目录执行：

```bash
pre-commit run --all-files
```

如果修改了前端，至少补充执行：

```bash
cd frontend
pnpm lint
pnpm build
```

如果修改了 Python 服务（`backend`/`executor`/`executor_manager`/`im`），请先安装依赖并验证服务可启动：

```bash
cd <service>
uv sync
uv run python -m app.main
```

如果修改了数据库模型，请按以下流程处理迁移（在 `backend` 目录）：

```bash
uv run -m alembic revision --autogenerate -m "description"
uv run -m alembic upgrade head
```

然后人工检查自动生成的 migration 是否符合预期。

## 5. PR 描述建议模板

建议在 PR 描述中至少包含以下信息：

- 变更背景和目标
- 主要改动点
- 影响范围（frontend/backend/executor/executor_manager/im）
- 本地验证命令与结果
- 如涉及 UI：提供截图或录屏
- 如涉及数据库：提供 migration 和回滚说明
- 如涉及破坏性变更：明确写出升级注意事项

仓库现在提供了默认 PR 模板：

- [PR 模板](.github/pull_request_template.md)

## 6. 开发规范

### 5.1 通用规范

- 不提交密钥、令牌、私有配置或任何敏感信息。
- 新增功能时，同步更新相关文档（README、docs 或 API 文档）。
- 保持改动最小化，优先修复根因，不做无关重构。
- 修改仓库治理、发布、Docker、CI/CD、版本策略时，必须同步更新相关文档。

### 5.2 Python（后端相关服务）

- Python 版本：`3.12+`。
- 必须写完整类型标注，优先使用内建泛型：`list[T]`、`dict[str, Any]`、`X | None`。
- 代码注释必须使用英文，Docstring 遵循 Google 风格。

后端分层规范（`backend`）：

- `repositories/` 只做数据库 CRUD，不放业务逻辑。
- `services/` 负责业务编排和事务管理。
- `services/` 返回 SQLAlchemy Model 或 Pydantic Schema，不返回裸 `dict[str, Any]`。
- 数据库 session 通过 FastAPI 依赖注入在 API 层创建，再传入 service/repository。

异常处理规范（`backend`）：

- 业务错误使用 `AppException`。
- HTTP 语义错误使用 `HTTPException`。
- 不要捕获通用 `Exception` 后再包装成 `HTTPException(500, ...)`。

### 5.3 前端（Next.js）

- 使用 Tailwind CSS v4 与设计变量（`frontend/app/globals.css`）。
- 不要硬编码颜色、阴影、圆角，优先使用 design token（如 `var(--primary)`、`var(--shadow-md)`、`var(--radius)`）。
- 所有面向用户的文案必须走 i18n，不写硬编码字符串。
- i18n 相关路径：
  - `frontend/lib/i18n/client.ts`
  - `frontend/lib/i18n/settings.ts`
  - `frontend/lib/i18n/locales/*/translation.json`

## 7. Review 与合并标准

通常满足以下条件后可进入合并流程：

- 改动目标清晰，PR 说明完整。
- 本地检查通过，且验证步骤可复现。
- 代码符合分层与风格规范。
- 必要文档已更新。
- Review 意见已处理或达成一致。

最终合并由仓库维护者执行。

## 8. 发布与治理说明

- release 当前以 `main` 上的 tag 为入口。
- Docker 镜像发布当前由 GitHub Actions 在 `v*` tag 上执行。
- 涉及分支策略、发布策略、Docker 行为、CI/CD 自动化、仓库规则的改动，请以 [仓库治理草案](docs/repository-governance.md) 为准，并同步更新相关文档。
