# Poco 仓库治理草案

本文档定义 Poco 仓库的代码协作、发布与自动化治理规则。当前仓库尚未把所有规则完全自动化，因此本文档分为两类内容：

- **当前已落地**：仓库里已经存在的约束、流程或自动化。
- **拟采用规则**：从当前阶段开始执行，并逐步通过 `.github/`、hooks 与文档补齐自动化。

本草案面向仓库维护者、贡献者和 AI 编程代理，作为后续完善仓库治理的基线文档。

## 0. 文档优先级

当多个文档同时涉及仓库规则时，优先级如下：

1. 本文档：仓库治理、发布与自动化准绳
2. [CONTRIBUTING.md](/D:/codespace/poco-claw/CONTRIBUTING.md)：贡献流程与提交约定
3. [AGENTS.md](/D:/codespace/poco-claw/AGENTS.md)：AI 代理执行约束
4. [README.md](/D:/codespace/poco-claw/README.md) / [README_zh.md](/D:/codespace/poco-claw/README_zh.md)：项目入口与导航

如果出现不一致，应优先修正文档而不是靠口头约定维持。

## 1. 项目阶段

当前仓库处于 **MVP 后的稳定迭代早期**。

判断依据：

- 已形成前端、后端、executor、executor-manager、IM 的多服务结构。
- 已具备 Docker 部署、基础 CI、镜像发布与贡献说明。
- 仍缺少较完整的仓库治理自动化，例如 PR 标题校验、CODEOWNERS、labeler、secret scanning、统一 release 说明机制。

阶段性原则：

- 优先做小而清晰的改动。
- 优先修复根因，不顺手做大规模架构调整。
- 涉及架构边界、Docker、CI/CD、发布策略、治理规则的改动时，先阅读本文档和相关实现，再修改代码。

## 2. 分支与合并策略

### 2.1 拟采用规则

- 采用 **trunk-based development**。
- `main` 是唯一长期分支。
- 所有日常开发通过短分支合入 `main`。
- 推荐分支前缀：
  - `feat/`
  - `fix/`
  - `docs/`
  - `chore/`
  - `refactor/`
  - `infra/`
- 推荐合并策略为 **squash merge**。
- 不直接向 `main` 推送，除非仓库维护者明确要求。

### 2.2 当前已落地

- 当前默认开发分支为 `main`。
- [CONTRIBUTING.md](/D:/codespace/poco-claw/CONTRIBUTING.md) 已要求从 `main` 拉短分支并通过 PR 合入。
- GitHub Actions 已对 `main` 上的 push 和 PR 执行基础检查。
- GitHub 仓库当前已启用：
  - squash merge
  - auto-merge
  - merge 后自动删除分支
  - 禁用 merge commit
  - 禁用 rebase merge
  - `main` 分支保护
  - 通过 PR 合入 `main`
  - 0 个必需审批
  - 必须通过已配置 checks
  - 必须解决 PR 对话

## 3. Pull Request 规范

### 3.1 拟采用规则

- 所有代码改动通过 PR 合并。
- PR 标题使用 Conventional Commits：
  - `<type>(<optional-scope>): <summary>`
- 允许的 `type`：
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
- 推荐 `scope`：
  - `repo`
  - `docs`
  - `backend`
  - `executor`
  - `executor-manager`
  - `frontend`
  - `im`
  - `docker`
  - `ci`

### 3.2 PR 描述最小要求

PR 描述至少包含：

- 变更摘要
- 验证方式
- 是否影响架构或文档
- 是否影响 Docker、部署或发布
- 是否需要额外治理同步（例如 README、CONTRIBUTING、AGENTS、workflow）

### 3.3 当前已落地

- [CONTRIBUTING.md](/D:/codespace/poco-claw/CONTRIBUTING.md) 已对分支命名、提交格式和 PR 描述给出建议。
- 仓库已提供 [PR 模板](/D:/codespace/poco-claw/.github/pull_request_template.md) 作为最小描述骨架。
- 仓库已提供 [PR 标题校验 workflow](/D:/codespace/poco-claw/.github/workflows/ci-pr-title.yml)。

## 4. 版本与发布策略

### 4.1 当前已落地

- 发布入口是 Git tag。
- [docker-images.yml](/D:/codespace/poco-claw/.github/workflows/docker-images.yml) 仅在 `v*` tag 上构建并推送镜像。
- Docker 镜像 registry 当前为 **GHCR**。
- 镜像包含：
  - `poco-backend`
  - `poco-executor-manager`
  - `poco-executor`（`lite` / `full`）
  - `poco-frontend`
  - `poco-im`

### 4.2 拟采用规则

- release 仅从 `main` 产生。
- tag 格式保持为 `v*`，推荐语义化为 `v0.x.y`。
- 默认不引入 release branch / hotfix branch。
- 发布策略变更必须同步更新：
  - 本文档
  - 对应 workflow
  - README / 部署文档中相关说明

### 4.3 Changeset 策略

当前仓库 **尚未采用 Changesets**。

现阶段不强制引入 Changesets，原因如下：

- 当前仓库不是以独立包版本发布为核心流程。
- 现有发布链路已经基于 tag + Docker 镜像推送工作。
- 在自动化治理仍未补齐前，引入 Changesets 会增加维护复杂度。

后续如需要引入 release PR、统一变更记录或多产物版本管理，再单独评估。

## 5. 本地质量门禁

### 5.1 当前已落地

仓库当前通过 [`.pre-commit-config.yaml`](/D:/codespace/poco-claw/.pre-commit-config.yaml) 配置了以下检查：

- Python:
  - Ruff lint
  - Ruff format
  - Pyrefly
- Frontend:
  - ESLint
  - Prettier

### 5.2 当前约定

- 提交前建议执行：
  - `pre-commit run --all-files`
- 修改前端后建议额外执行：
  - `pnpm --dir frontend lint`
  - `pnpm --dir frontend build`
- 修改 Python 服务后建议至少验证服务能启动。
- 修改 Docker、治理或自动化相关文件后，建议至少额外检查：
  - `docker compose config`
  - 受影响 workflow 的静态正确性
  - 相关文档链接与说明是否同步

### 5.3 治理缺口

当前仓库 **尚未落地** 以下门禁：

- `commit-msg` 提交信息校验
- `pre-push` 完整检查
- spelling / secret scanning / actionlint / contract sync 检查
- 统一的根级 `check` 命令

## 6. GitHub Actions 与自动化现状

### 6.1 当前已落地

仓库当前已有以下 workflow：

- [ci-pr-title.yml](/D:/codespace/poco-claw/.github/workflows/ci-pr-title.yml)
- [ci-eslint.yml](/D:/codespace/poco-claw/.github/workflows/ci-eslint.yml)
- [ci-actionlint.yml](/D:/codespace/poco-claw/.github/workflows/ci-actionlint.yml)
- [ci-gitleaks.yml](/D:/codespace/poco-claw/.github/workflows/ci-gitleaks.yml)
- [ci-markdownlint.yml](/D:/codespace/poco-claw/.github/workflows/ci-markdownlint.yml)
- [ci-prettier.yml](/D:/codespace/poco-claw/.github/workflows/ci-prettier.yml)
- [ci-pyrefly.yml](/D:/codespace/poco-claw/.github/workflows/ci-pyrefly.yml)
- [ci-ruff.yml](/D:/codespace/poco-claw/.github/workflows/ci-ruff.yml)
- [docker-images.yml](/D:/codespace/poco-claw/.github/workflows/docker-images.yml)
- [close-stale-issues.yml](/D:/codespace/poco-claw/.github/workflows/close-stale-issues.yml)
- [opencode.yml](/D:/codespace/poco-claw/.github/workflows/opencode.yml)
- [feishu-bot.yml](/D:/codespace/poco-claw/.github/workflows/feishu-bot.yml)
- GitHub 仓库级安全设置当前已启用：
  - secret scanning
  - push protection

### 6.2 治理缺口

当前仓库尚未落地以下自动化：

- changeset 校验

这些属于后续治理完善项，而不是当前阶段必须一次性补齐的基础设施。

## 7. 文档分工

- [README.md](/D:/codespace/poco-claw/README.md)：项目入口、定位、特性、快速开始。
- [AGENTS.md](/D:/codespace/poco-claw/AGENTS.md)：面向 AI 编程代理的执行约束与目录职责说明。
- [CONTRIBUTING.md](/D:/codespace/poco-claw/CONTRIBUTING.md)：面向贡献者的开发与 PR 规范。
- 本文档：面向仓库治理的正式准绳草案。

后续若架构边界、发布流程、治理规则、目录职责发生变化，代码与上述文档必须同步更新。

## 8. 工作方式

### 8.1 默认原则

- 优先做聚焦改动，不顺手修 unrelated 问题。
- 不为了“看起来完整”而提前引入重型平台化设计。
- 先做最小验证，再扩大验证范围。
- 仓库治理相关改动优先保持“文档先行、自动化后补”的节奏。

### 8.2 当前阶段的非目标

当前阶段不主动引入以下内容，除非有明确需求与验证收益：

- release branch / hotfix branch
- Changesets + release PR 体系
- Kubernetes / 复杂环境编排
- canary / nightly / promotion 流水线
- 多平台镜像发布以外的复杂发布矩阵
- 脱离当前产品边界的统一抽象层

## 9. 治理变更要求

凡是修改以下内容，必须同时更新本文档或相关配套文档：

- `.github/workflows/`
- Docker 发布与镜像策略
- 分支、PR、tag、release 规则
- 质量门禁（hooks / lint / typecheck / build 规则）
- 贡献流程说明

## 10. 治理相关改动检查单

当变更涉及治理、发布、Docker、CI/CD 或仓库自动化时，提交前至少检查以下项目：

- 是否已阅读本文档与相关实现文件
- 是否同步更新了 README、CONTRIBUTING、AGENTS 中受影响的入口说明
- 是否说明该变更属于“当前已落地”还是“拟采用规则”
- 是否明确影响范围：
  - 分支与 PR 流程
  - Docker 构建 / 运行
  - GitHub Actions / 发布流程
  - 本地质量门禁
- 是否补充了最小验证方法
- 是否避免把运行产物、临时配置或本地环境文件带入提交

## 11. 当前治理执行矩阵

| 主题 | 当前准绳 | 当前状态 |
|---|---|---|
| 项目入口 | `README.md` | 已落地 |
| 贡献流程 | `CONTRIBUTING.md` | 已落地 |
| AI 代理约束 | `AGENTS.md` | 已落地 |
| 仓库治理 | `docs/repository-governance.md` | 草案 |
| Python 代码检查 | `ci-ruff.yml`、`ci-pyrefly.yml`、`.pre-commit-config.yaml` | 已落地 |
| Frontend 检查 | `ci-eslint.yml`、`ci-prettier.yml`、`.pre-commit-config.yaml` | 已落地 |
| Markdown 检查 | `ci-markdownlint.yml` | 已落地 |
| PR 标题校验 | `ci-pr-title.yml` | 已落地 |
| Workflow 静态检查 | `ci-actionlint.yml` | 已落地 |
| Secret scanning | `ci-gitleaks.yml` | 已落地 |
| Dependabot | `.github/dependabot.yml` | 已落地 |
| Docker 发布 | `docker-images.yml` | 已落地 |
| CODEOWNERS | `.github/CODEOWNERS` | 已落地 |
| Labeler | `.github/labeler.yml`、`.github/workflows/labeler.yml` | 已落地 |
| GitHub labels | repository labels | 已落地 |
| Merge strategy | repository settings | 已落地 |
| Branch protection | repository settings | 已落地 |

## 12. 下一步建议

基于当前仓库现状，建议按以下顺序补治理自动化：

1. 为 `main` 补 GitHub 仓库设置层的保护与必检规则
2. 把当前分散的 CI workflow 收敛成更清晰的必检集合
3. 评估是否需要引入 Changesets

在这些缺口补齐前，本文档应作为 **人工 review 与 AI 代理执行** 的主要治理依据。
