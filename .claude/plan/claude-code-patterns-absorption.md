# Poco 吸收 Claude Code 核心设计模式分阶段实施计划

## 📋 任务类型

- [x] 后端 (→ Codex 已完成详细规划)
- [x] 前端 (→ 补充设计系统实现)
- [x] 全栈 (→ 前后端协同)

---

## 分析摘要

### 现状评估

当前执行链路清晰：`Frontend → Backend → Executor Manager → Executor`

**主要短板**：

- Hook 仍是硬编码列表（`task.py:63-80`），缺少阶段、排序、条件、失败策略
- 配置持久化只保留 session/run 快照，长期默认值靠环境变量
- Skill 只有 `entry`/`source`，缺少统一 manifest 和生命周期元数据
- `permission_mode` 是粗粒度枚举，不能表达工具/路径/网络/MCP 级授权
- MCP 只有 UI 侧简单展示，没有正式连接状态机
- Workspace 以 clone/checkout 为主，缺少 worktree/sparse checkout 策略

### 架构决策

**保留四服务架构**：

- **Backend**: 持久化与用户配置
- **Executor Manager**: 配置解析与能力 staging
- **Executor**: 最终执行与运行时状态
- **Frontend**: UI 展示与用户交互

**核心原则**：

1. 所有新增能力默认做成 "typed JSON policy + registry"，不允许用户直接上传可执行代码
2. Worktree/sparse checkout 必须是按需策略，失败时回退到当前 clone 路径
3. 配置分层只覆盖 `system → user → session → run → runtime-injected-secrets`

---

## 第一批：声明式基础设施（3-4 周）

### 目标

建立三件基础设施：声明式 hook 模型、用户级配置分层持久化、标准化 skill manifest

### 后端实施步骤

#### 1. 数据库迁移

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

#### 2. Backend 模型与服务

**关键文件**：

- `backend/app/models/user_execution_setting.py` (新建)
- `backend/app/models/skill.py:L7-L22` (修改)
- `backend/app/services/execution_settings_service.py` (新建)
- `backend/app/services/skill_service.py:L43-L163` (修改)

**伪代码**：

```python
# backend/app/schemas/execution_settings.py
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

#### 3. Backend API 端点

- `GET /api/v1/execution-settings` - 获取用户设置
- `PATCH /api/v1/execution-settings` - 更新用户设置
- `GET /api/v1/execution-settings/catalog` - 获取设置目录
- `POST /api/v1/skills/{skill_id}/manifest/validate` - 验证 skill manifest

### Executor Manager 实施

#### 4. Config Resolver 升级

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

### Executor 实施

#### 5. Hook Registry & Factory

**关键文件**：

- `executor/app/hooks/registry.py` (新建)
- `executor/app/hooks/factory.py` (新建)
- `executor/app/hooks/manager.py:L6-L24` (修改)

**伪代码**：

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

### 前端实施

#### 6. UI 组件清单

**新增页面**：

- `frontend/app/(shell)/settings/execution/page.tsx` - 执行设置主页
- `frontend/features/execution-settings/components/hook-config-card.tsx` - Hook 配置卡片
- `frontend/features/execution-settings/components/config-layer-badge.tsx` - 配置来源标签

**修改组件**：

- `frontend/features/capabilities/skills/components/skill-settings-dialog.tsx` - 显示 manifest 信息

#### 7. 设计语言应用

```tsx
// 使用现有设计系统
<div
  className="rounded-2xl bg-card/60 backdrop-blur-md shadow-sm
                transition-all duration-300
                focus-within:shadow-lg focus-within:border-primary/30"
>
  <HookConfigCard />
</div>
```

**色彩**：OKLCH Teal/Green (`oklch(0.8348 0.1302 160.908)` 亮色模式)

### 测试策略

- **Backend**: Migration + Settings service + Skill manifest validator
- **Executor Manager**: Layered merge + Legacy fallback
- **Executor**: Hook registry/factory 单测
- **Frontend**: `pnpm --dir frontend lint` + `pnpm --dir frontend build`

---

## 第二批：权限引擎与 MCP 状态机（4-6 周）

### 目标

升级 `permission_mode` 为规则引擎，把 MCP 状态从 UI 提示升级为正式状态机

### 后端实施

#### 1. 数据库迁移

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

#### 2. Permission Engine

**伪代码**：

```python
# executor/app/core/permission_engine.py
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

#### 3. MCP Connection Tracker

**伪代码**：

```python
# executor_manager/app/services/mcp_connection_tracker.py
class McpConnectionTracker:
    # 状态转换: requested → staged → launching → connected
    #                → failed
    #           connected → degraded → connected
    #           connected|failed → terminated

    def transition(self, run_id: str, server_name: str, to_state: str, **meta):
        self.repository.upsert_transition(run_id, server_name, to_state, meta)
```

### 前端实施

#### 4. UI 组件

**新增**：

- `frontend/features/capabilities/permissions/components/rule-editor.tsx` - 权限规则编辑器
- `frontend/features/chat/components/execution/chat-panel/mcp-state-machine-card.tsx` - MCP 状态可视化

**修改**：

- `frontend/features/chat/components/execution/chat-panel/mcp-status-card.tsx:L15-L76`

#### 5. 状态可视化设计

```tsx
// MCP 连接状态机可视化
<div className="flex items-center gap-2">
  <div
    className={cn(
      "w-2 h-2 rounded-full",
      state === "connected" && "bg-green-500",
      state === "connecting" && "bg-yellow-500 animate-pulse",
      state === "failed" && "bg-red-500",
    )}
  />
  <span className="text-sm">{serverName}</span>
  <Badge variant="outline">{state}</Badge>
</div>
```

### 迁移策略

- 默认把现有 `permission_mode` 映射成内建 policy preset
- 第一阶段 audit-only 记录 permission decisions，再开启 enforce

---

## 第三批：Worktree 与 Sparse Checkout（按需实施）

### 目标

按需引入 worktree/sparse checkout，降低大仓库和多分支场景成本

### 实施策略

#### 1. Workspace Strategy Design

```python
# executor/app/schemas/workspace.py
from typing import Literal

class WorkspaceStrategy(BaseModel):
    checkout_strategy: Literal["clone", "worktree", "sparse-clone", "sparse-worktree"] = "clone"
    sparse_paths: list[str] | None = None
    reference_branch: str | None = None
```

#### 2. Repo Cache Management

**Executor Manager 实现**：

- Host workspace 根下引入 per-user repo cache
- 路径：`<workspace_root>/repo-cache/<user_id>/<repo_hash>`
- Cache 生命周期在 Manager，不在 Executor 容器内

#### 3. Fallback 机制

```python
# executor/app/core/workspace.py
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

### 前端 UI

**新增**：

- `frontend/features/workspace/components/strategy-selector.tsx` - Workspace 策略选择器（高级选项，默认隐藏）

---

## 关键文件清单

### 第一批关键文件

| 文件                                                         | 操作 | 说明               |
| ------------------------------------------------------------ | ---- | ------------------ |
| `backend/app/models/user_execution_setting.py`               | 新建 | 用户执行设置模型   |
| `backend/app/schemas/execution_settings.py`                  | 新建 | 设置 Schema        |
| `backend/app/services/execution_settings_service.py`         | 新建 | 设置服务           |
| `backend/app/api/v1/execution_settings.py`                   | 新建 | 设置 API           |
| `backend/app/models/skill.py:L7-L22`                         | 修改 | 扩展 manifest 字段 |
| `executor_manager/app/services/config_resolver.py:L114-L268` | 修改 | 分层合并逻辑       |
| `executor/app/hooks/registry.py`                             | 新建 | Hook 注册中心      |
| `executor/app/hooks/factory.py`                              | 新建 | Hook 工厂          |
| `executor/app/core/engine.py:L154-L355`                      | 修改 | 使用 HookRegistry  |
| `frontend/app/(shell)/settings/execution/page.tsx`           | 新建 | 执行设置页         |

### 第二批关键文件

| 文件                                                                    | 操作 | 说明         |
| ----------------------------------------------------------------------- | ---- | ------------ |
| `backend/app/models/agent_run_mcp_connection.py`                        | 新建 | MCP 连接模型 |
| `backend/app/services/permission_policy_service.py`                     | 新建 | 权限策略服务 |
| `executor/app/core/permission_engine.py`                                | 新建 | 权限引擎     |
| `frontend/features/capabilities/permissions/components/rule-editor.tsx` | 新建 | 规则编辑器   |

---

## 风险评估

| 风险                                   | 批次 | 严重度 | 缓解措施                                                    |
| -------------------------------------- | ---- | ------ | ----------------------------------------------------------- |
| 用户级设置与 session/run override 漂移 | 1    | 高     | Run 保存 `config_layers`，前端提供 effective config preview |
| 旧 skill 没有 manifest 导致导入失败    | 1    | 高     | 兼容适配器自动补全，校验失败仅阻断新发布不阻断旧运行        |
| Hook registry 切换导致回调丢失         | 1    | 高     | Flag 下双路径运行，`CallbackHook` 固定为强制内建 hook       |
| Permission policy 过严造成任务不可执行 | 2    | 高     | 先 audit-only，再按租户开启 enforce                         |
| MCP transition 写入过多导致状态抖动    | 2    | 中     | Transition 去重、状态去抖、只写真正状态变化                 |
| Worktree/sparse 导致仓库脏状态         | 3    | 高     | 默认 clone；高级策略失败立即回退；仅 opt-in                 |

---

## 推荐上线顺序

1. **第一批**：完成声明式基础设施，所有老任务继续走兼容路径
2. **第二批**：
   - 先上线 MCP 状态机
   - 再上线 permission audit-only
   - 最后切 enforce
3. **第三批**：只对 GitHub HTTPS + persistent workspace 白名单用户开放

---

## SESSION_ID（供 /ccg:execute 使用）

- **CODEX_SESSION**: `019d472a-f88c-79d2-977e-2fd804964dbc`
- **GEMINI_SESSION**: `fa0f1add-5e77-4b24-94ed-48c79892e4c7` (前端设计分析)

---

## 设计语言参考

**色彩**：

- 亮色模式：`oklch(0.8348 0.1302 160.908)` (Teal/Green)
- 暗色模式：`oklch(0.4365 0.1044 156.7556)`

**玻璃态效果**：

```css
.glass-card {
  backdrop-filter: blur(12px);
  background: oklch(0.98 0.01 160.908 / 0.6);
  box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  border-radius: 1rem;
}
```

**交互反馈**：

```css
.interactive {
  transition: all 300ms;
}
.interactive:focus-within {
  box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
  border-color: oklch(0.8348 0.1302 160.908 / 0.3);
}
```

**排版**：

- 标题：`font-family: 'Libre Baskerville', serif`
- 正文：系统 sans-serif 栈
