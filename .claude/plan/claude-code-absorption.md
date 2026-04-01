# Poco 吸收 Claude Code 核心设计模式 - 分阶段实施计划

> 基于 Codex 后端架构分析和 Gemini 前端设计评估生成

## 📋 任务类型

- [x] 后端 (→ Codex)
- [x] 前端 (→ Gemini)
- [x] 全栈 (→ 并行)

## 🎯 技术方案

**核心原则**：Poco 不应"复刻 Claude Code CLI"，而应吸收其控制面抽象，并适配云端多用户场景。

**架构决策**：

- 保持现有四服务架构（Frontend/Backend/Executor Manager/Executor）
- Backend 负责持久化与用户配置
- Executor Manager 负责配置解析与能力 staging
- Executor 负责最终执行与运行时状态
- Frontend 提供配置 UI 和状态可视化

**分批策略**：

1. **第一批（高优先级，3-4周）**：Hook 系统 + 配置分层 + 技能 manifest
2. **第二批（中优先级，4-6周）**：权限规则引擎 + MCP 状态机
3. **第三批（低优先级，按需）**：Worktree / Sparse checkout

+| `frontend/features/chat/types/api/session.ts` | `159-186` | modify | 支持 execution settings 相关类型 |
+| `frontend/features/task-composer/api/task-submit-api.ts` | `15-58`, `92-130` | modify | 只发送 run override |
+| `frontend/features/capabilities/skills/types/index.ts` | `3-27` | modify | 前端 skill manifest 类型 |
+| `frontend/features/capabilities/skills/components/skill-settings-dialog.tsx` | `71-170` | modify | 展示 manifest/lifecycle 状态 |

- +### Database Changes
- +- `user_execution_settings`
- - `id BIGSERIAL PK`
- - `user_id VARCHAR(255) UNIQUE NOT NULL`
- - `schema_version VARCHAR(32) NOT NULL DEFAULT 'v1'`
- - `settings JSONB NOT NULL DEFAULT '{}'::jsonb`
    +- `skills`
- - `manifest_version VARCHAR(32) NULL`
- - `manifest JSONB NULL`
- - `entry_checksum VARCHAR(128) NULL`
- - `lifecycle_state VARCHAR(32) NOT NULL DEFAULT 'active'`
    +- `agent_runs`
- - `config_layers JSONB NULL`
- - `resolved_hook_specs JSONB NULL`
- +### API Endpoints
- +- `GET /api/v1/execution-settings`
  +- `PATCH /api/v1/execution-settings`
  +- `GET /api/v1/execution-settings/catalog`
  +- `POST /api/v1/skills/{skill_id}/manifest/validate`
  +- `POST /api/v1/internal/execution-settings/resolve`
- +### Pseudocode
- +```python
  +class HookSpec(BaseModel):
- key: str
- phase: Literal["setup", "pre_query", "message", "error", "teardown"]
- order: int = 100
- enabled: bool = True
- on_error: Literal["continue", "fail"] = "continue"
- config: dict[str, Any] = Field(default_factory=dict)
-
- +class HookRegistry:
- \_builtins: dict[str, type[AgentHook]] = {
-        "workspace": WorkspaceHook,
-        "callback": CallbackHook,
-        "todo": TodoHook,
-        "run_snapshot": RunSnapshotHook,
-        "browser_screenshot": BrowserScreenshotHook,
- }
-
- def build(self, specs: list[HookSpec], deps: HookDependencies) -> list[AgentHook]:
-        hooks: list[AgentHook] = []
-        for spec in sorted(specs, key=lambda item: (item.phase, item.order)):
-            if not spec.enabled:
-                continue
-            hook_cls = self._builtins[spec.key]
-            hooks.append(HookFactory.create(hook_cls, spec.config, deps))
-        return hooks
  +```
- +```ts
  +export interface ExecutionSettings {
- schema_version: "v1";
- hooks: {
- pipeline: Array<{
-      key: string;
-      enabled: boolean;
-      order: number;
-      config?: Record<string, unknown>;
- }>;
- };
- permissions?: Record<string, unknown>;
- workspace?: Record<string, unknown>;
- skills?: Record<string, unknown>;
  +}
  +```
- +### Tests
- +- `backend`: `uv run -m pytest backend/tests` 中新增 migration、settings service、skill manifest validator 覆盖。
  +- `executor_manager`: 扩展 `tests/test_config_resolver.py`，验证 layered merge、legacy fallback、manifest-invalid fail-fast。
  +- `executor`: 新增 hook registry/factory 单测，保留 `tests/test_engine.py` 和 `tests/test_workspace.py` 回归。
  +- `frontend`: 类型收敛后跑 `pnpm --dir frontend lint` 和 `pnpm --dir frontend build`。
- +## Batch 2
- +### Goal
- +把 `permission_mode` 升级为规则引擎，把 MCP 状态从 UI 提示升级为正式状态机与审计对象。
- +### Steps
- +1. 数据库迁移
- - `agent_runs` 增加 `permission_policy_snapshot`。
- - `tool_executions` 增加 `policy_action`、`policy_rule_id`、`policy_reason`。
- - 新增 `agent_run_mcp_connections` 表。
    +2. Backend
- - 新增 permission policy schema/service。
- - 新增 MCP connection repository/service/API。
- - `CallbackService` 支持写入 permission events 和 MCP transitions。
    +3. Executor
- - 把 `engine.py` 中的 `can_use_tool()` 内联逻辑替换成 `PermissionEngine.evaluate()`。
- - 新增 `McpConnectionTrackerHook`，把 staging/launch/connect/fail/terminate 变更写回 callback。
    +4. Frontend
- - 增加权限策略页签或 execution settings 下的 permission editor。
- - `mcp-status-card.tsx` 升级为状态机展示，不再只看 `connected/error/disconnected`。
    +5. 迁移策略
- - 默认把现有 `permission_mode` 映射成内建 policy preset。
- - 第一阶段以 audit-only 方式记录 permission decisions，再开启 enforce。
- +### Key Files
- +| 文件 | 行号范围 | 操作类型 | 说明 |
  +| --- | --- | --- | --- |
  +| `backend/app/models/agent_run.py` | `56-91` | modify | 增加 permission policy snapshot |
  +| `backend/app/models/tool_execution.py` | `23-58` | modify | 增加 permission decision 审计字段 |
  +| `backend/app/schemas/callback.py` | `21-70` | modify | 增加 MCP transition / permission event payload |
  +| `backend/app/services/callback_service.py` | `56-145`, `218-299` | modify | 持久化 permission 与 MCP transition |
  +| `backend/app/schemas/run.py` | `21-74` | modify | 暴露 permission snapshot / MCP summary |
  +| `backend/app/models/agent_run_mcp_connection.py` | `new` | create | MCP 运行态实体 |
  +| `backend/app/services/mcp_connection_service.py` | `new` | create | MCP 状态机服务 |
  +| `backend/app/services/permission_policy_service.py` | `new` | create | 规则引擎配置服务 |
  +| `backend/app/api/v1/runs_mcp.py` | `new` | create | run 级 MCP 状态查询 |
  +| `executor/app/core/engine.py` | `154-279` | modify | 用 PermissionEngine 替换内联判断 |
  +| `executor/app/schemas/state.py` | `16-60` | modify | MCP 状态扩充为 state machine shape |
  +| `frontend/features/chat/types/api/callback.ts` | `13-64` | modify | 前端接收更细粒度的 MCP 与 permission 状态 |
  +| `frontend/features/chat/components/execution/chat-panel/mcp-status-card.tsx` | `15-76` | modify | 状态机可视化 |
  +| `frontend/features/capabilities/mcp/types/index.ts` | `3-53` | modify | 增加 health/state machine 类型 |
- +### Database Changes
- +- `agent_runs`
- - `permission_policy_snapshot JSONB NULL`
    +- `tool_executions`
- - `policy_action VARCHAR(16) NULL`
- - `policy_rule_id VARCHAR(128) NULL`
- - `policy_reason TEXT NULL`
    +- `agent_run_mcp_connections`
- - `id UUID PK`
- - `run_id UUID NOT NULL`
- - `session_id UUID NOT NULL`
- - `server_id INT NULL`
- - `server_name VARCHAR(255) NOT NULL`
- - `state VARCHAR(32) NOT NULL`
- - `attempt_count INT NOT NULL DEFAULT 0`
- - `last_error TEXT NULL`
- - `metadata JSONB NULL`
- - `created_at`, `updated_at`
- +### API Endpoints
- +- `GET /api/v1/runs/{run_id}/mcp-connections`
  +- `POST /api/v1/mcp-servers/{server_id}/health-check`
  +- `GET /api/v1/execution-settings/permissions`
  +- `PATCH /api/v1/execution-settings/permissions`
- +### Pseudocode
- +```python
  +class PermissionEngine:
- def evaluate(self, tool_name: str, tool_input: dict, context: PermissionContext) -> PermissionDecision:
-        for rule in self.policy.rules:
-            if not rule.matches(tool_name=tool_name, tool_input=tool_input, context=context):
-                continue
-            return PermissionDecision(
-                action=rule.action,  # allow | deny | ask
-                rule_id=rule.id,
-                reason=rule.reason,
-            )
-        return self.policy.default_decision()
  +```
- +```python
  +class McpConnectionTracker:
- def transition(self, run_id: str, server_name: str, to_state: str, \*\*meta: Any) -> None:
-        # requested -> staged -> launching -> connected
-        # launching -> failed
-        # connected -> degraded -> connected
-        # connected|failed -> terminated
-        self.repository.upsert_transition(run_id, server_name, to_state, meta)
  +```
- +### Tests
- +- Permission rule matching、preset 映射、audit-only/enforce 切换。
  +- MCP transition 幂等、乱序回调去重、前端状态映射。
  +- 回归验证 plan mode 仍能工作，且不被新策略引擎破坏。
- +## Batch 3
- +### Goal
- +按需引入 worktree/sparse checkout，在不破坏当前 clone 路径的前提下，降低大仓库和多分支场景下的成本。
- +### Steps
- +1. 策略设计
- - 新增 `workspace.checkout_strategy`：`clone | worktree | sparse-clone | sparse-worktree`。
- - 新增 `workspace.sparse_paths` 和 `workspace.reference_branch`。
    +2. Executor Manager
- - 在 host workspace 根下引入 per-user repo cache：`<workspace_root>/repo-cache/<user_id>/<repo_hash>`。
- - 把 cache 生命周期放在 Manager，不放在 Executor 临时容器内。
    +3. Executor
- - `WorkspaceManager.prepare()` 改为 strategy dispatch。
- - `git.operations` 增加 `worktree add/remove/prune`、`sparse-checkout init/set/disable`。
- - 任一高级策略失败后回退到当前 `clone + checkout` 路径。
    +4. Frontend
- - repo dialog 增加 advanced workspace strategy 配置。
- - 默认隐藏，仅在绑定 repo 的任务中可见。
    +5. 上线顺序
- - 先支持 GitHub HTTPS 仓库。
- - 只对 persistent workspace 或明确启用的用户生效。
- +### Key Files
- +| 文件 | 行号范围 | 操作类型 | 说明 |
  +| --- | --- | --- | --- |
  +| `executor/app/core/workspace.py` | `47-130`, `186-263` | modify | clone 路径改为 strategy dispatch |
  +| `executor/app/utils/git/operations.py` | `109-160`, `970-1128`, `1485-1515` | modify | 增加 worktree/sparse git primitives |
  +| `executor/tests/test_workspace.py` | `94-137`, `156-230`, `351-485` | modify | 覆盖 fallback 与策略选择 |
  +| `executor_manager/app/services/workspace_manager.py` | `31-103`, `223-259` | modify | 增加 repo cache 目录与元数据 |
  +| `executor_manager/app/services/run_pull_service.py` | `250-508` | modify | 将 resolved workspace strategy 一并下发 |
  +| `backend/app/services/task_service.py` | `403-489` | modify | session/run snapshot 支持 workspace strategy override |
  +| `backend/app/schemas/session.py` | `11-28` | modify | 新增 workspace policy 字段 |
  +| `frontend/features/task-composer/api/task-submit-api.ts` | `15-58` | modify | 发送 checkout strategy / sparse paths |
- +### Database Changes
- +- 必选：无新增表，沿用 Batch 1 的 `user_execution_settings.settings.workspace` 和 session/run snapshot。
  +- 可选：`repo_workspace_caches` 表，用于后台清理和容量审计；如果第一轮资源有限，可以先用 filesystem metadata 实现。
- +### Pseudocode
- +```python
  +def prepare(self, config: TaskConfig) -> Path:
- strategy = config.workspace_strategy or "clone"
- if strategy == "worktree" and self.repo_cache.exists():
-        try:
-            return self._prepare_worktree(config)
-        except Exception:
-            logger.warning("worktree_prepare_failed_fallback_clone")
- if strategy in {"sparse-clone", "sparse-worktree"}:
-        return self._prepare_sparse_checkout(config)
- return self.\_prepare_repository_via_clone(config)
  +```
- +### Tests
- +- Git command builder 单测，不依赖真实远端。
  +- 大仓库路径 fallback 测试。
  +- deliverable detection / workspace export 在 sparse 模式下的回归验证。
- +## Cross-cutting Test Strategy
- +- Backend: migration + repository + service contract tests。
  +- Executor Manager: resolver/stager/run dispatch tests，确保 legacy payload 仍可跑。
  +- Executor: hook lifecycle、permission、workspace strategy 全部做纯单元测试，避免依赖真实 Claude SDK。
  +- Frontend: 类型同步、关键设置页交互、`pnpm --dir frontend lint`、`pnpm --dir frontend build`。
  +- 集成回归链路：
- - 创建 session
- - enqueue run
- - Manager resolve/stage
- - Executor callback
- - Backend 持久化
- - Frontend 状态展示
- +## Risk Assessment
- +| 风险 | 批次 | 严重度 | 缓解 |
  +| --- | --- | --- | --- |
  +| 用户级设置与 session/run override 漂移 | 1 | high | run 保存 `config_layers`，前端提供“effective config preview” |
  +| 旧 skill 没有 manifest 导致导入失败 | 1 | high | 兼容适配器自动补全，校验失败仅阻断新发布不阻断旧运行 |
  +| hook registry 切换导致回调丢失 | 1 | high | flag 下双路径运行，`CallbackHook` 固定为强制内建 hook |
  +| permission policy 过严造成任务不可执行 | 2 | high | 先 audit-only，再按租户开启 enforce |
  +| MCP transition 写入过多导致状态抖动 | 2 | medium | transition 去重、状态去抖、只写真正状态变化 |
  +| worktree/sparse 导致仓库脏状态或 export 缺文件 | 3 | high | 默认 clone；高级策略失败立即回退；仅 opt-in |
  +| repo cache 跨用户泄漏 | 3 | high | cache 目录按 `user_id + repo_hash` 隔离，禁止共享 credential 上下文 |
- +## Recommended Rollout Order
- +1. 先完成 Batch 1，并让所有老任务继续走兼容路径。
  +2. Batch 2 先上线 MCP 状态机，再上线 permission audit-only，再切 enforce。
  +3. Batch 3 最后做，且只对 GitHub HTTPS + persistent workspace 的白名单用户开放。

  ***

  SESSION_ID: 019d472a-f88c-79d2-977e-2fd804964dbc

## 📌 SESSION_ID（供 /ccg:execute 使用）

- **CODEX_SESSION**: 019d472a-f88c-79d2-977e-2fd804964dbc
- **GEMINI_SESSION**: fa0f1add-5e77-4b24-94ed-48c79892e4c7
