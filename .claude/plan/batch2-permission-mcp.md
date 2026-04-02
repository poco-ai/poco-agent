# 📋 实施计划：Batch 2 — 权限规则引擎 + MCP 状态机

## 任务类型

- [x] 后端 (→ Codex 分析完成)
- [x] 前端 (→ Gemini 不可用，Claude 自行设计)
- [x] 全栈 (→ 前后端协同)

---

## 背景与现状

Batch 1 已完成"字段预埋"，但未打通闭环：

| 组件 | 现状 | 缺口 |
|------|------|------|
| `PermissionEngine` | 基础实现存在 | 只支持精确工具名匹配，无优先级/组合/audit-only |
| `tool_executions.policy_*` | 列已存在 | 从未被填充，始终为空 |
| `agent_run_mcp_connections` | 表已存在 | 只有 current snapshot，无 transition 验证，无历史 |
| `permission_policy_snapshot` | 列已存在 | 从未被填充 |
| MCP 状态生产者 | 无 | executor 没有任何 mcp_status 生产逻辑 |

---

## 技术方案（Codex 推荐 Option 2：双层投影）

### 权限引擎

三层架构：
1. `PresetPolicyCompiler`：把 `permission_mode` 编译成 preset rules（保持 SDK 兼容）
2. `PermissionContextBuilder`：构建标准化 `PermissionContext`（含 tool_category/paths/network/mcp）
3. `PermissionEvaluator`：优先级规则匹配，支持 audit-only / enforce 模式

第一阶段：audit-only（记录决策，不改变放行结果）
第二阶段：enforce（按规则实际拦截）

### MCP 状态机

事件源 + 投影模式：
- `agent_run_mcp_connections`：current snapshot（保留）
- `agent_run_mcp_connection_events`：append-only transition history（新增）
- `health` 字段：`healthy | degraded`（与 lifecycle state 分离）

状态转换路径：
```
requested → staged → launching → connected → terminated
                  ↘ failed ↗
           connected → degraded → connected（重连）
```

事件源分工：
- backend/task enqueue → `requested`
- executor_manager staging → `staged`
- executor SDK 启动 → `launching` → `connected` / `failed`
- executor teardown → `terminated`

---

## 实施步骤

### Step 1：数据库迁移

**新建文件**：`backend/alembic/versions/<hash>_batch2_permission_audit_mcp_events.py`

```sql
-- 权限审计事件表（companion audit，不污染 tool_executions）
CREATE TABLE permission_audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL,
    session_id UUID NOT NULL,
    tool_name VARCHAR(128) NOT NULL,
    tool_input JSONB,
    policy_action VARCHAR(16) NOT NULL,  -- allow | deny | ask
    policy_rule_id VARCHAR(128),
    policy_reason TEXT,
    audit_mode BOOLEAN NOT NULL DEFAULT TRUE,
    context JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX ix_permission_audit_events_run_id ON permission_audit_events(run_id);

-- MCP 连接事件表（append-only transition history）
CREATE TABLE agent_run_mcp_connection_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id UUID NOT NULL REFERENCES agent_run_mcp_connections(id),
    run_id UUID NOT NULL,
    from_state VARCHAR(32),
    to_state VARCHAR(32) NOT NULL,
    event_source VARCHAR(32) NOT NULL,  -- backend | executor_manager | executor
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX ix_mcp_connection_events_connection_id ON agent_run_mcp_connection_events(connection_id);
CREATE INDEX ix_mcp_connection_events_run_id ON agent_run_mcp_connection_events(run_id);

-- agent_run_mcp_connections 增加 health 字段
ALTER TABLE agent_run_mcp_connections ADD COLUMN health VARCHAR(16) DEFAULT 'healthy';
```

**预期产物**：迁移文件，`alembic upgrade head` 通过

---

### Step 2：权限策略 Schema（Backend）

**新建文件**：`backend/app/schemas/permission_policy.py`

```python
from typing import Any, Literal
from pydantic import BaseModel, Field

class PermissionRuleMatch(BaseModel):
    tools: list[str] | None = None          # 精确工具名列表
    tool_categories: list[str] | None = None # read | write | execute | network | mcp
    path_patterns: list[str] | None = None   # glob 路径模式
    network_patterns: list[str] | None = None # URL/域名模式
    mcp_servers: list[str] | None = None     # MCP server 名称

class PermissionRule(BaseModel):
    id: str
    priority: int = 100                      # 数字越小优先级越高
    match: PermissionRuleMatch = Field(default_factory=PermissionRuleMatch)
    action: Literal["allow", "deny", "ask"]
    reason: str = ""
    enabled: bool = True

class PermissionPolicy(BaseModel):
    version: str = "v1"
    mode: Literal["audit", "enforce"] = "audit"  # 第一阶段 audit-only
    default_action: Literal["allow", "deny"] = "allow"
    preset_source: str | None = None         # default | acceptEdits | plan | bypassPermissions
    rules: list[PermissionRule] = Field(default_factory=list)
```

**修改文件**：`backend/app/schemas/execution_settings.py`
- `permissions: dict[str, Any]` → `permissions: PermissionPolicy`

**预期产物**：强类型策略 schema，向后兼容（空 dict → 默认 PermissionPolicy）

---

### Step 3：权限引擎升级（Executor）

**修改文件**：`executor/app/core/permission_engine.py`

```python
# 新增 PermissionContext dataclass
@dataclass(slots=True)
class PermissionContext:
    tool_name: str
    tool_category: str          # read | write | execute | network | mcp
    tool_input: dict[str, Any]
    cwd: str
    normalized_paths: list[str]
    network_targets: list[str]
    mcp_server_name: str | None
    session_id: str
    run_id: str | None
    permission_mode: str
    plan_approved: bool

# 新增 PresetPolicyCompiler
class PresetPolicyCompiler:
    PRESET_RULES: dict[str, list[dict]] = {
        "plan": [...],           # 只允许 read 类工具
        "acceptEdits": [...],    # 允许 read + write，不允许 execute
        "bypassPermissions": [], # 空规则 = 全部 allow
        "default": [],           # 空规则 = 全部 allow
    }

    @classmethod
    def compile(cls, permission_mode: str) -> list[PermissionRule]:
        ...

# 升级 PermissionEngine
class PermissionEngine:
    def __init__(self, *, policy: PermissionPolicy, permission_mode: str, plan_approved: bool):
        self.policy = policy
        self.permission_mode = permission_mode
        self.plan_approved = plan_approved
        # 编译 preset rules，优先级低于自定义规则
        self._preset_rules = PresetPolicyCompiler.compile(permission_mode)

    def evaluate(self, tool_name: str, tool_input: dict, context: dict) -> PermissionDecision:
        perm_ctx = PermissionContextBuilder.build(tool_name, tool_input, context)
        # plan mode 前置检查（保持现有行为）
        if self.permission_mode == "plan" and not self.plan_approved:
            ...
        # 自定义规则（高优先级）
        for rule in sorted(self.policy.rules, key=lambda r: r.priority):
            if rule.enabled and self._matches(rule, perm_ctx):
                return PermissionDecision(action=rule.action, rule_id=rule.id, reason=rule.reason)
        # preset rules（低优先级）
        for rule in self._preset_rules:
            if self._matches(rule, perm_ctx):
                return PermissionDecision(...)
        # default
        return PermissionDecision(action=self.policy.default_action, ...)
```

**预期产物**：支持优先级、多维度匹配的权限引擎，向后兼容现有 plan mode

---

### Step 4：权限审计落点（Executor + Backend）

**修改文件**：`executor/app/core/engine.py`（`can_use_tool` 闭包）

```python
async def can_use_tool(tool_name, input_data, context):
    decision = permission_engine.evaluate(tool_name, ...)

    # 审计记录（通过 callback hook 异步发送）
    if callback_hook:
        await callback_hook.record_permission_event(
            tool_name=tool_name,
            tool_input=input_data,
            decision=decision,
            audit_mode=(permission_engine.policy.mode == "audit"),
        )

    # audit-only 模式：记录但不拦截（除 plan mode 外）
    if permission_engine.policy.mode == "audit" and decision.action == "deny":
        if self.permission_mode != "plan":
            return PermissionResultAllow(updated_input=input_data)

    if decision.action == "deny":
        return PermissionResultDeny(message=decision.reason, interrupt=False)
    ...
```

**修改文件**：`executor/app/hooks/callback.py`
- 新增 `record_permission_event()` 方法，通过 callback API 发送审计事件

**修改文件**：`backend/app/api/v1/internal.py`（或新建 internal callback 端点）
- 接收权限审计事件，写入 `permission_audit_events` 表

**预期产物**：audit-only 模式下权限决策被记录，不影响执行

---

### Step 5：MCP 状态生产者（Executor）

**修改文件**：`executor/app/hooks/callback.py`

```python
class CallbackHook:
    async def on_mcp_state_change(
        self,
        server_name: str,
        to_state: str,  # launching | connected | failed | terminated
        error_message: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        await self._send_callback({
            "type": "mcp_transition",
            "server_name": server_name,
            "to_state": to_state,
            "event_source": "executor",
            "error_message": error_message,
            "metadata": metadata,
        })
```

**修改文件**：`executor/app/core/engine.py`
- 在 SDK MCP 启动前后调用 `on_mcp_state_change`
- 在 teardown 时发送 `terminated`

**修改文件**：`executor_manager/app/services/run_pull_service.py`
- 在 staging 完成后通过 backend API 写入 `staged` 事件

**预期产物**：MCP 状态从 executor 侧生产，backend 侧接收并持久化

---

### Step 6：MCP 状态机服务（Backend）

**修改文件**：`backend/app/services/mcp_connection_service.py`

```python
# 合法状态转换矩阵
VALID_TRANSITIONS: dict[str | None, set[str]] = {
    None: {"requested"},
    "requested": {"staged", "failed"},
    "staged": {"launching", "failed"},
    "launching": {"connected", "failed"},
    "connected": {"terminated", "failed"},
    "failed": {"launching", "terminated"},  # 支持重连
    "terminated": set(),  # terminal state
}

class McpConnectionService:
    def record_transition(
        self,
        db: Session,
        *,
        run_id: UUID,
        session_id: UUID,
        server_name: str,
        to_state: str,
        event_source: str,
        error_message: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        existing = AgentRunMcpConnectionRepository.get_by_run_and_server_name(db, run_id, server_name)
        from_state = existing.state if existing else None

        # 验证合法转换
        if to_state not in VALID_TRANSITIONS.get(from_state, set()):
            logger.warning("invalid_mcp_transition", from_state=from_state, to_state=to_state)
            return  # 幂等：非法转换静默忽略

        # 幂等：相同状态不重复写
        if existing and existing.state == to_state:
            return

        # upsert current snapshot
        if existing is None:
            existing = AgentRunMcpConnection(run_id=run_id, session_id=session_id, server_name=server_name)
            AgentRunMcpConnectionRepository.create(db, existing)

        existing.state = to_state
        if to_state == "failed":
            existing.last_error = error_message
            existing.attempt_count = (existing.attempt_count or 0) + 1
        if to_state == "connected":
            existing.health = "healthy"

        # append transition event
        event = AgentRunMcpConnectionEvent(
            connection_id=existing.id,
            run_id=run_id,
            from_state=from_state,
            to_state=to_state,
            event_source=event_source,
            error_message=error_message,
            metadata=metadata,
        )
        db.add(event)
        db.flush()
```

**预期产物**：状态机有 transition 验证、幂等去重、append-only 历史

---

### Step 7：API 端点（Backend）

**新建文件**：`backend/app/api/v1/runs_mcp.py`

```python
# GET /api/v1/runs/{run_id}/mcp-connections
# 返回 current snapshot + transition history

# GET /api/v1/runs/{run_id}/permission-audit
# 返回权限审计事件列表
```

**修改文件**：`backend/app/api/v1/execution_settings.py`
- `GET /api/v1/execution-settings/permissions` — 获取权限策略
- `PATCH /api/v1/execution-settings/permissions` — 更新权限策略

**修改文件**：`backend/app/api/v1/internal.py`
- 新增 `POST /internal/mcp-transition` — executor_manager 发送 MCP 状态转换
- 新增 `POST /internal/permission-audit` — executor 发送权限审计事件

**预期产物**：完整的 API 端点，前端可查询 MCP 状态和权限审计

---

### Step 8：Run 级快照回写（Executor Manager）

**修改文件**：`executor_manager/app/services/config_resolver.py`

```python
# resolve() 完成后，把 resolved permission policy 回写到 run
await backend_client.update_run_metadata(run_id, {
    "permission_policy_snapshot": resolved_config.permissions.model_dump(mode="json"),
    "resolved_hook_specs": [spec.model_dump(mode="json") for spec in resolved_hook_specs],
})
```

**预期产物**：`agent_runs.permission_policy_snapshot` 被填充，事后可审计

---

### Step 9：前端权限规则编辑器

**新建文件**：`frontend/features/capabilities/permissions/`

```
permissions/
├── index.ts
├── components/
│   ├── permission-policy-editor.tsx   # 主编辑器（preset 选择 + 规则列表）
│   ├── rule-editor.tsx                # 单条规则编辑（工具/路径/网络/MCP 匹配）
│   ├── rule-list.tsx                  # 规则列表（可拖拽排序）
│   └── policy-mode-toggle.tsx         # audit / enforce 切换
├── hooks/
│   └── use-permission-policy.ts       # 策略 CRUD hooks
└── types.ts                           # 前端类型定义
```

关键 UX 决策：
- Preset 选择器：4 个内建模式（default/acceptEdits/plan/bypassPermissions）
- 自定义规则：在 preset 基础上叠加，优先级可调
- audit-only 模式：默认开启，显示"仅记录，不拦截"提示
- 规则测试：输入工具名 → 实时预览匹配结果

---

### Step 10：前端 MCP 状态可视化

**修改文件**：`frontend/features/chat/components/execution/chat-panel/mcp-status-card.tsx`
- 升级为使用 `agent_run_mcp_connections` API 数据
- 状态指示器：`requested`(灰) → `staged`(蓝) → `launching`(黄闪) → `connected`(绿) → `failed`(红) → `terminated`(灰)
- `degraded` 用 `health` overlay 显示（绿底黄点）

**新建文件**：`frontend/features/chat/components/execution/chat-panel/mcp-state-machine-card.tsx`
- 展开视图：显示 transition history 时间线
- 错误信息：`failed` 状态显示 `last_error`
- 重连提示：`failed` 状态显示重连次数

---

## 关键文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/alembic/versions/<hash>_batch2_*.py` | 新建 | 迁移：permission_audit_events + mcp_connection_events + health 列 |
| `backend/app/schemas/permission_policy.py` | 新建 | 强类型权限策略 schema |
| `backend/app/schemas/execution_settings.py` | 修改 | permissions 字段改为 PermissionPolicy |
| `backend/app/models/permission_audit_event.py` | 新建 | 权限审计事件模型 |
| `backend/app/models/agent_run_mcp_connection_event.py` | 新建 | MCP 转换事件模型 |
| `backend/app/services/mcp_connection_service.py` | 修改 | 增加 transition 验证和 history |
| `backend/app/api/v1/runs_mcp.py` | 新建 | MCP 状态查询 API |
| `backend/app/api/v1/internal.py` | 修改 | 新增 mcp-transition 和 permission-audit 端点 |
| `executor/app/core/permission_engine.py` | 修改 | 三层架构升级 |
| `executor/app/core/engine.py` | 修改 | audit 记录 + MCP 状态生产 |
| `executor/app/hooks/callback.py` | 修改 | 新增 record_permission_event + on_mcp_state_change |
| `executor_manager/app/services/config_resolver.py` | 修改 | 回写 permission_policy_snapshot |
| `executor_manager/app/services/run_pull_service.py` | 修改 | 发送 staged 事件 |
| `frontend/features/capabilities/permissions/` | 新建 | 权限规则编辑器 |
| `frontend/features/chat/components/execution/chat-panel/mcp-status-card.tsx` | 修改 | 升级状态可视化 |
| `frontend/features/chat/components/execution/chat-panel/mcp-state-machine-card.tsx` | 新建 | MCP 历史时间线 |

---

## 风险与缓解

| 风险 | 严重度 | 缓解措施 |
|------|--------|----------|
| audit-only 模式下 callback 失败导致审计丢失 | 中 | 审计失败不影响执行，fire-and-forget + 本地日志兜底 |
| MCP 状态生产者缺失导致状态永远是 requested | 高 | executor 侧先实现 launching/connected/failed，staged 可后补 |
| `execution_settings.permissions` schema 变更破坏现有数据 | 高 | 空 dict → 默认 PermissionPolicy，向后兼容适配器 |
| transition 验证过严导致合法状态被拒绝 | 中 | 非法转换静默忽略（warn log），不抛异常 |
| 前端 permission editor 误操作导致任务不可执行 | 高 | 默认 audit-only，enforce 需要显式开启；规则测试模拟器 |

---

## 测试策略

### Backend
- `permission_audit_events` CRUD
- `McpConnectionService.record_transition()` 矩阵测试（合法/非法/幂等）
- `PermissionPolicy` schema 向后兼容（空 dict 解析）

### Executor
- `PermissionEngine` 优先级规则匹配
- `PresetPolicyCompiler` 各 preset 映射
- audit-only 模式不拦截
- plan mode 前置检查不被新规则覆盖

### Executor Manager
- `config_resolver` 回写 `permission_policy_snapshot`
- `run_pull_service` 发送 `staged` 事件

### Frontend
- `pnpm --dir frontend lint`
- `pnpm --dir frontend build`
- `pnpm --dir frontend test --run`

---

## 上线顺序

1. Step 1（迁移）→ Step 2（schema）→ Step 3（引擎）→ Step 4（audit 落点）
2. Step 5（MCP 生产者）→ Step 6（状态机服务）→ Step 7（API）
3. Step 8（快照回写）
4. Step 9-10（前端）

---

## SESSION_ID（供 /ccg:execute 使用）

- **CODEX_SESSION**: `019d4996-0ac2-7240-85c4-7a0068981b6e`
- **GEMINI_SESSION**: N/A（429 rate limit，3 次全部失败）
