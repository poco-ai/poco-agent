# Poco 吸收 Claude Code 核心设计模式 - 完整实施计划

## 现状评估

当前执行链路清晰：`Frontend → Backend → Executor Manager → Executor`

**主要短板**：

- Hook 仍是硬编码列表（`task.py:63-80`），缺少阶段、排序、条件、失败策略
- 配置持久化只保留 session/run 快照，长期默认值靠环境变量
- Skill 只有 `entry`/`source`，缺少统一 manifest 和生命周期元数据
- `permission_mode` 是粗粒度枚举，不能表达工具/路径/网络/MCP 级授权
- MCP 只有 UI 侧简单展示，没有正式连接状态机
- Workspace 以 clone/checkout 为主，缺少 worktree/sparse checkout 策略

## 核心原则

1. 所有新增能力默认做成 "typed JSON policy + registry"，不允许用户直接上传可执行代码
2. Worktree/sparse checkout 必须是按需策略，失败时回退到当前 clone 路径
3. 配置分层只覆盖 `system → user → session → run → runtime-injected-secrets`

---

## 第一批：声明式基础设施

### Backend 数据库迁移

```sql
-- 新增 user_execution_settings 表
CREATE TABLE user_execution_settings (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(255) UNIQUE NOT NULL,
    schema_version VARCHAR(32) NOT NULL DEFAULT 'v1',
    settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 扩展 skills 表
ALTER TABLE skills ADD COLUMN manifest_version VARCHAR(32);
ALTER TABLE skills ADD COLUMN manifest JSONB;
ALTER TABLE skills ADD COLUMN entry_checksum VARCHAR(128);
ALTER TABLE skills ADD COLUMN lifecycle_state VARCHAR(32) NOT NULL DEFAULT 'active';

-- 扩展 agent_runs 表
ALTER TABLE agent_runs ADD COLUMN config_layers JSONB;
ALTER TABLE agent_runs ADD COLUMN resolved_hook_specs JSONB;
```

### Backend 模型与服务

**关键文件**：

- `backend/app/models/user_execution_setting.py` (新建)
- `backend/app/models/skill.py:L7-L22` (修改 - 扩展 manifest 字段)
- `backend/app/schemas/execution_settings.py` (新建)
- `backend/app/services/execution_settings_service.py` (新建)
- `backend/app/services/skill_service.py:L43-L163` (修改)
- `backend/app/api/v1/execution_settings.py` (新建)

**Schema 伪代码**：

```python
from pydantic import BaseModel
from typing import Literal

class HookSpec(BaseModel):
    key: str  # workspace, callback, todo, browser_screenshot
    phase: Literal["setup", "pre_query", "message", "error", "teardown"]
    order: int = 100
    enabled: bool = True
    on_error: Literal["continue", "fail"] = "continue"
    config: dict = {}

class ExecutionSettings(BaseModel):
    schema_version: str = "v1"
    hooks: dict = {"pipeline": []}
    permissions: dict = {}
    workspace: dict = {}
    skills: dict = {}
```

**Backend API 端点**：

- `GET /api/v1/execution-settings` - 获取用户设置
- `PATCH /api/v1/execution-settings` - 更新用户设置
- `GET /api/v1/execution-settings/catalog` - 获取设置目录
- `POST /api/v1/skills/{skill_id}/manifest/validate` - 验证 skill manifest

### Executor Manager Config Resolver

**关键文件**：`executor_manager/app/services/config_resolver.py:L114-L268`

**实现分层合并**：

```python
class ConfigResolver:
    def resolve(self, user_id: str, config_snapshot: dict, **ctx) -> dict:
        # Layer 1: System defaults (from env)
        system_defaults = self._load_system_defaults()

        # Layer 2: User settings (from Backend)
        user_settings = await self.backend_client.get_execution_settings(user_id)

        # Layer 3: Session/Run snapshot
        run_overrides = config_snapshot

        # Layer 4: Runtime injection (secrets, tokens)
        runtime_injection = self._prepare_runtime_secrets(user_id)

        # Deep merge with priority: runtime > run > user > system
        return self._deep_merge([
            system_defaults,
            user_settings,
            run_overrides,
            runtime_injection
        ])
```

### Executor Hook Registry & Factory

**关键文件**：

- `executor/app/hooks/registry.py` (新建)
- `executor/app/hooks/factory.py` (新建)
- `executor/app/hooks/manager.py:L6-L24` (修改)
- `executor/app/core/engine.py:L154-L355` (修改 - 使用 HookRegistry)

**Registry 伪代码**：

```python
# executor/app/hooks/registry.py
class HookRegistry:
    _builtins: dict[str, type[AgentHook]] = {
        "workspace": WorkspaceHook,
        "callback": CallbackHook,
        "todo": TodoHook,
        "run_snapshot": RunSnapshotHook,
        "browser_screenshot": BrowserScreenshotHook,
    }

    def build(self, specs: list[HookSpec], deps: HookDependencies) -> list[AgentHook]:
        hooks: list[AgentHook] = []
        for spec in sorted(specs, key=lambda s: (s.phase, s.order)):
            if not spec.enabled:
                continue
            hook_cls = self._builtins[spec.key]
            hooks.append(HookFactory.create(hook_cls, spec.config, deps))
        return hooks
```

### Frontend UI 组件

**新增页面**：

- `frontend/app/(shell)/settings/execution/page.tsx` - 执行设置主页
- `frontend/features/execution-settings/components/hook-config-card.tsx` - Hook 配置卡片
- `frontend/features/execution-settings/components/config-layer-badge.tsx` - 配置来源标签

**修改组件**：

- `frontend/features/capabilities/skills/components/skill-settings-dialog.tsx` - 显示 manifest 信息

**设计语言**：

- 玻璃态效果：`backdrop-blur-md`, `bg-card/60`
- OKLCH Teal/Green: `oklch(0.8348 0.1302 160.908)` (亮色)
- 圆角：`rounded-2xl`

---

## 第二批：权限引擎与 MCP 状态机

### Backend 数据库迁移

```sql
-- 扩展 agent_runs
ALTER TABLE agent_runs ADD COLUMN permission_policy_snapshot JSONB;

-- 扩展 tool_executions
ALTER TABLE tool_executions ADD COLUMN policy_action VARCHAR(16);
ALTER TABLE tool_executions ADD COLUMN policy_rule_id VARCHAR(128);
ALTER TABLE tool_executions ADD COLUMN policy_reason TEXT;

-- 新增 agent_run_mcp_connections 表
CREATE TABLE agent_run_mcp_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL,
    session_id UUID NOT NULL,
    server_id INT,
    server_name VARCHAR(255) NOT NULL,
    state VARCHAR(32) NOT NULL,
    attempt_count INT NOT NULL DEFAULT 0,
    last_error TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Permission Engine

**新建文件**：`executor/app/core/permission_engine.py`

```python
class PermissionEngine:
    def evaluate(self, tool_name: str, tool_input: dict, context: PermissionContext) -> PermissionDecision:
        for rule in self.policy.rules:
            if not rule.matches(tool_name=tool_name, tool_input=tool_input, context=context):
                continue
            return PermissionDecision(
                action=rule.action,  # allow | deny | ask
                rule_id=rule.id,
                reason=rule.reason,
            )
        return self.policy.default_decision()
```

### MCP Connection Tracker

**新建文件**：`executor_manager/app/services/mcp_connection_tracker.py`

```python
class McpConnectionTracker:
    # 状态转换: requested → staged → launching → connected
    #                → failed
    #           connected → degraded → connected
    #           connected|failed → terminated

    def transition(self, run_id: str, server_name: str, to_state: str, **meta):
        self.repository.upsert_transition(run_id, server_name, to_state, meta)
```

### Frontend UI

**新增**：

- `frontend/features/capabilities/permissions/components/rule-editor.tsx` - 权限规则编辑器
- `frontend/features/chat/components/execution/chat-panel/mcp-state-machine-card.tsx` - MCP 状态可视化

**修改**：

- `frontend/features/chat/components/execution/chat-panel/mcp-status-card.tsx:L15-L76`

---

## 第三批：Worktree 与 Sparse Checkout

### Workspace Strategy Design

**新建文件**：`executor/app/schemas/workspace.py`

```python
from typing import Literal

class WorkspaceStrategy(BaseModel):
    checkout_strategy: Literal["clone", "worktree", "sparse-clone", "sparse-worktree"] = "clone"
    sparse_paths: list[str] | None = None
    reference_branch: str | None = None
```

### Fallback Mechanism

**修改文件**：`executor/app/core/workspace.py`

```python
def prepare(self, config: TaskConfig) -> Path:
    strategy = config.workspace_strategy or "clone"

    if strategy == "worktree" and self.repo_cache.exists():
        try:
            return self._prepare_worktree(config)
        except Exception:
            logger.warning("worktree_prepare_failed_fallback_clone")

    if strategy in {"sparse-clone", "sparse-worktree"}:
        return self._prepare_sparse_checkout(config)

    return self._prepare_repository_via_clone(config)
```

### Frontend UI

**新增**：

- `frontend/features/workspace/components/strategy-selector.tsx` - Workspace 策略选择器（高级选项）

---

## Implementation Instructions

### Step 1: Context Verification

Before coding, verify you have sufficient context:

- Use ace-tool MCP (search_context) to search for relevant existing code patterns
- Read the key files listed in the plan to understand current implementation
- If the plan references external libraries/APIs, use context7 MCP to query their latest documentation

Key files to read:

- `backend/app/models/skill.py` - understand current skill model
- `backend/app/services/skill_service.py` - understand skill service
- `executor/app/hooks/base.py` - understand current hook system
- `executor/app/hooks/manager.py` - understand hook manager
- `executor/app/core/engine.py` - understand engine and hook usage
- `executor_manager/app/services/config_resolver.py` - understand config resolution
- `frontend/features/capabilities/skills/components/skill-settings-dialog.tsx` - understand skill UI

### Step 2: Implementation

Implement all three batches in order:

1. **Batch 1**: Declarative infrastructure (database migrations, models, services, API endpoints, hook registry)
2. **Batch 2**: Permission engine and MCP state machine
3. **Batch 3**: Worktree and sparse checkout strategies

Constraints:

- Follow existing code conventions in this project
- Use Python 3.12+ syntax (list[T], T | None)
- Use Pydantic v2 for all models/schemas
- Frontend: Use Tailwind CSS v4, feature-first organization
- Handle edge cases and errors properly
- Keep changes minimal and focused on the plan
- Do NOT modify files outside the plan scope

### Step 3: Self-Verification

After implementation:

- Run `uv run ruff check backend executor executor_manager`
- Run `uv run pyrefly check backend executor executor_manager`
- Run `uv run pytest backend/tests executor/tests executor_manager/tests`
- Run `pnpm --dir frontend lint`
- Run `pnpm --dir frontend build`
- Run `pnpm --dir frontend test`

## Output Format

Respond with a structured report:

### CONTEXT_GATHERED

<What information was searched/found, key findings from MCP tools>

### CHANGES_MADE

For each file changed:

- File path
- What was changed and why
- Lines added/removed

### VERIFICATION_RESULTS

- Ruff lint: pass/fail
- Pyrefly typecheck: pass/fail
- Python tests: pass/fail (details if fail)
- Frontend lint: pass/fail
- Frontend build: pass/fail
- Frontend tests: pass/fail

### REMAINING_ISSUES

<Any unresolved issues, edge cases, or suggestions>
