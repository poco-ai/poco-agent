# Workspace agent execution plan

## 元数据

| 字段 | 值 |
|------|-----|
| **创建日期** | 2026-04-15 |
| **预期改动范围** | backend issue execution / backend agent assignment / executor_manager scheduled trigger / executor persistent sandbox / frontend issues feature |
| **改动类型** | feat |
| **优先级** | P1 |
| **状态** | completed |

## 实施阶段

- [x] Phase 0: 明确 issue → agent 执行的架构边界
- [x] Phase 1: 设计 issue 的 AI assignee 模型与分配流程
- [x] Phase 2: 设计持久化 sandbox 执行模式
- [x] Phase 3: 设计定时任务触发执行模式
- [x] Phase 4: 建立执行状态同步与生命周期管理
- [x] Phase 5: 接入审计日志

---

## 背景

### 问题陈述

当前 Poco 的执行模型是严格的请求-响应模式：用户发送 prompt → executor 创建/复用容器 → agent 运行 → 响应流回 → 容器销毁或保留。这个模型适合交互式编码助手场景，但不支持"给 AI 分配一个长期任务，让它自主工作"的团队协作场景。

团队 issue board 引入后，issue 需要支持分配给一个 preset（代表 AI agent 能力），并且系统需要能够自动触发 agent 执行来完成该 issue。这要求执行模型从"用户手动触发"扩展为"系统自主触发"，同时保留用户手动触发的灵活性。

### 目标

本计划的目标是建立 issue → preset → agent execution 的自动化链路，支持两种触发模式：

- **持久化 sandbox**：为 AI assignee 创建一个长期运行的容器，agent 在其中持续工作直到任务完成
- **定时任务**：通过 APScheduler 定期检查 issue 状态，按需触发 agent 执行

本计划依赖 [00-workspace-tenancy-foundation-plan.md](/Users/bytedance/Developer/poco-agent/specs/draft/00-workspace-tenancy-foundation-plan.md) 和 [01-workspace-collaboration-plan.md](/Users/bytedance/Developer/poco-agent/specs/draft/01-workspace-collaboration-plan.md) 中定义的 workspace、issue、preset 模型。

### 关键洞察

#### 1. 持久化容器基础设施已经存在

当前 executor_manager 已经支持 `container_mode: "ephemeral" | "persistent"`，`ContainerPool` 会在任务完成后保留 persistent 容器。这意味着持久化 sandbox 不需要从零构建容器管理，而是复用现有的 persistent container 能力，扩展为"绑定到 issue assignee 的长期工作空间"。

#### 2. `sdk_session_id` 支持跨 run 对话恢复

当前架构中 `sdk_session_id` 允许在同一容器内跨多次执行恢复 Claude SDK 会话。这对持久化 sandbox 场景至关重要——agent 可以在多次触发中保持上下文连续性。

#### 3. 定时任务和持久化 sandbox 是正交的两种模式

定时任务（APScheduler 轮询 + 按需触发）适合"周期性检查、按需执行"的场景，如每日构建、定时审查。持久化 sandbox 适合"给 AI 一个持续工作空间"的场景，如长期开发任务。两者不应互斥，用户在分配 AI assignee 时可以选择触发方式。

#### 4. 执行链路不需要感知 workspace

与 tenancy foundation 的设计原则一致，执行链路（executor / executor_manager）不需要知道 workspace 的存在。backend 在触发执行时负责权限校验和资源解析，执行层只看到 session、project、preset 和 prompt。

---

## Phase 0: 明确 issue → agent 执行的架构边界

### 目标

定义 issue → agent 执行链路中各组件的职责边界，明确哪些是新增能力、哪些是复用现有基础设施。

### 任务清单

#### 0.1 定义执行触发架构

**描述：** 明确执行触发的完整链路和各层职责：

```
Issue 分配 AI preset assignee
        ↓
Backend: 创建 agent_assignment 记录
        ↓
  ┌─────────────────────────────────────────┐
  │ 触发方式（用户在分配时选择）              │
  │                                          │
  │  持久化 sandbox:                          │
  │    Backend → ExecutorManager              │
  │      → ContainerPool.get_or_create       │
  │      → persistent container              │
  │      → executor.execute(prompt)           │
  │    Agent 在容器中持续工作                  │
  │                                          │
  │  定时任务:                                │
  │    APScheduler → poll_issues()            │
  │      → 发现需要执行的 AI-assigned issue    │
  │      → Backend → ExecutorManager          │
  │      → ephemeral/persistent container     │
  │      → executor.execute(prompt)           │
  │    执行完成后等待下一次轮询                │
  └─────────────────────────────────────────┘
        ↓
Executor → Backend callback
        ↓
Backend: 更新 issue 状态（status → in_progress/done 等）
```

**涉及组件：**
- `backend/app/services/` — 权限校验、assignment 管理、执行触发
- `executor_manager/app/scheduler/` — 定时任务调度
- `executor_manager/app/services/container_pool.py` — 持久化容器管理
- `executor/app/core/engine.py` — agent 执行

**验收标准：**
- [x] spec 中明确各层职责边界
- [x] spec 中明确执行层不感知 workspace

#### 0.2 定义 agent_assignment 数据模型

**描述：** 新增 `agent_assignments` 表，记录 issue 与 AI preset 的执行绑定关系：

- `id` (UUID)
- `workspace_id` (UUID, FK → workspaces)
- `issue_id` (UUID, FK → workspace_issues)
- `preset_id` (UUID, FK → presets)
- `trigger_mode` (VARCHAR) — `persistent_sandbox` / `scheduled_task`
- `session_id` (UUID, nullable, FK → agent_sessions) — 关联的执行 session
- `container_id` (VARCHAR, nullable) — 持久化容器的标识
- `status` (VARCHAR) — `pending` / `running` / `completed` / `failed` / `cancelled`
- `prompt` (TEXT) — 生成给 agent 的任务描述
- `schedule_cron` (VARCHAR, nullable) — 定时任务的 cron 表达式
- `last_triggered_at` (TIMESTAMP, nullable)
- `last_completed_at` (TIMESTAMP, nullable)
- `created_by` (UUID, FK → users)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

**涉及文件：**
- `backend/app/models/agent_assignment.py`（新建）
- `backend/app/repositories/agent_assignment_repository.py`（新建）
- `backend/app/schemas/agent_assignment.py`（新建）
- `backend/alembic/versions/*`

**验收标准：**
- [x] spec 中明确 assignment 与 issue 的 1:1 关系
- [x] spec 中明确两种 trigger_mode 的区分
- [x] spec 中明确 status 状态机

---

## Phase 1: 设计 issue 的 AI assignee 模型与分配流程

### 目标

定义用户如何给 issue 分配 AI preset 作为 assignee，以及分配后的初始化流程。

### 任务清单

#### 1.1 定义 AI assignee 分配 API

**描述：** 扩展 issue 分配 API，支持两种 assignee 类型：

- 分配人类成员：`assignee_user_id = <user_id>`, `assignee_preset_id = null`
- 分配 AI preset：`assignee_preset_id = <preset_id>`, `assignee_user_id = null`
- 取消分配：两者都置 null

分配 AI preset 时，额外需要：
- 选择 trigger_mode（`persistent_sandbox` / `scheduled_task`）
- 如果是 scheduled_task，需要提供 schedule_cron 或使用默认值
- 系统根据 issue 内容和 preset 配置自动生成 prompt

**涉及文件：**
- `backend/app/api/v1/workspace_issues.py`
- `backend/app/services/workspace_issue_service.py`
- `backend/app/schemas/workspace_issue.py`
- `frontend/features/issues/api/`

**验收标准：**
- [x] spec 中明确双模 assignee 的 API 契约
- [x] spec 中明确分配 AI preset 时需要指定 trigger_mode
- [x] spec 中明确 prompt 自动生成策略

#### 1.2 定义 prompt 生成策略

**描述：** 当 issue 被分配给 AI preset 时，系统需要根据 issue 内容自动生成给 agent 的 prompt。第一版建议：

- 基础模板：`"<issue.title>\n\n<issue.description>"`
- 如果 issue 关联了 project，追加项目上下文（project name、描述、相关文件）
- 如果 issue 有自定义字段值，追加到 prompt 末尾
- prompt 生成后存储在 `agent_assignments.prompt` 中，用户可以在执行前查看和编辑

**涉及文件：**
- `backend/app/services/agent_assignment_service.py`（新建）
- `backend/app/lib/prompt_builder.py`（新建，可选）

**验收标准：**
- [x] spec 中明确 prompt 模板的组成要素
- [x] spec 中明确 prompt 可在执行前编辑

---

## Phase 2: 设计持久化 sandbox 执行模式

### 目标

利用现有 persistent container 基础设施，为 AI assignee 创建一个长期运行的 agent 工作空间。

### 任务清单

#### 2.1 设计 sandbox 生命周期

**描述：** 持久化 sandbox 的完整生命周期：

1. **创建**：AI preset 被分配到 issue 且选择 `persistent_sandbox` 模式时，backend 通过 executor_manager 请求创建 persistent container
2. **首次执行**：container 就绪后，自动执行第一次 agent run（使用 `agent_assignments.prompt`）
3. **持续工作**：agent 在容器中持续运行，通过 sdk_session_id 保持上下文
4. **状态同步**：executor 通过 callback 向 backend 报告进度，backend 更新 issue 和 assignment 状态
5. **用户交互**：用户可以通过 session 向正在运行的 agent 发送追加 prompt（复用现有 session queue）
6. **完成/失败**：agent 完成任务或出错，backend 更新 issue status，container 标记为可回收
7. **回收**：超时未活动或用户手动释放后，container 被销毁

**涉及文件：**
- `backend/app/services/agent_assignment_service.py`
- `executor_manager/app/services/container_pool.py`
- `executor_manager/app/scheduler/task_dispatcher.py`
- `backend/app/services/session_service.py`

**验收标准：**
- [x] spec 中明确 sandbox 的 7 个生命周期阶段
- [x] spec 中明确容器复用现有 `container_mode: "persistent"`
- [x] spec 中明确超时回收策略

#### 2.2 设计 sandbox 容器配置

**描述：** 持久化 sandbox 的容器配置需要考虑：

- **文件系统**：使用 `filesystem_mode: "sandbox"`，workspace 挂载 issue 关联的 project（如果有）
- **浏览器**：根据 preset 配置决定是否启用 `browser_enabled`
- **MCP 配置**：使用 preset 中定义的 MCP 服务器配置
- **模型**：使用 preset 中指定的模型
- **权限模式**：默认使用较宽松的权限模式（因为是自主执行），但可以通过 preset 配置覆盖
- **环境变量**：使用 preset 中定义的环境变量覆盖

**涉及文件：**
- `executor_manager/app/services/config_resolver.py`
- `executor/app/schemas/request.py`
- `backend/app/services/preset_service.py`

**验收标准：**
- [x] spec 中明确 sandbox 容器的配置来源
- [x] spec 中明确 preset 配置如何映射到 TaskConfig

---

## Phase 3: 设计定时任务触发执行模式

### 目标

通过 APScheduler 定期检查需要执行的 AI-assigned issue，按需触发 agent 执行。

### 任务清单

#### 3.1 设计 issue 轮询调度器

**描述：** 在 executor_manager 中新增一个定时任务，定期轮询 backend 获取需要触发的 AI-assigned issue：

- 查询条件：`agent_assignments` 中 `status = pending` 或 `status = completed`（对于周期性任务）且 `trigger_mode = scheduled_task`
- 对于 `pending` 的 assignment：首次触发执行
- 对于 `completed` 的周期性 assignment：按 cron 表达式判断是否需要重新触发
- 触发执行时：通过现有 TaskDispatcher.dispatch 发起执行，使用 ephemeral 或 persistent container（由 preset 配置决定）
- 执行完成后：更新 assignment 的 `last_triggered_at` 和 `last_completed_at`

轮询间隔建议：60 秒（可配置），避免对 backend 造成过大压力。

**涉及文件：**
- `executor_manager/app/scheduler/scheduler_config.py` — 新增轮询 job
- `executor_manager/app/services/issue_poller.py`（新建）
- `backend/app/api/v1/agent_assignments.py`（新建）— 提供轮询查询接口

**验收标准：**
- [x] spec 中明确轮询间隔和查询条件
- [x] spec 中明确首次触发和周期触发的区分
- [x] spec 中明确轮询接口的认证方式（复用现有 internal_api_token）

#### 3.2 设计 scheduled_task 的容器策略

**描述：** 定时任务模式的容器策略：

- 默认使用 ephemeral container（每次触发创建新容器，执行完成后销毁）
- 如果 preset 配置要求 persistent container，则复用已有容器（类似 sandbox 模式，但由调度器而非手动触发）
- 支持通过 preset 配置覆盖默认容器策略

**涉及文件：**
- `executor_manager/app/services/task_dispatcher.py`
- `executor_manager/app/services/config_resolver.py`

**验收标准：**
- [x] spec 中明确默认使用 ephemeral 容器
- [x] spec 中明确 preset 可覆盖容器策略

---

## Phase 4: 建立执行状态同步与生命周期管理

### 目标

确保 issue、assignment、session 三者之间的状态同步正确，用户能在前端看到 agent 的执行进度。

### 任务清单

#### 4.1 设计状态同步机制

**描述：** 定义 issue、assignment、session 三者的状态映射关系：

| assignment.status | issue.status | session.status | 含义 |
|---|---|---|---|
| `pending` | `todo` / `in_progress` | — | 等待触发 |
| `running` | `in_progress` | `running` | agent 正在执行 |
| `completed` | `done` | `completed` | agent 完成任务 |
| `failed` | `in_progress` | `failed` | agent 执行失败，可重试 |
| `cancelled` | `todo` | `cancelled` | 用户取消分配 |

状态流转由 executor callback 驱动：executor_manager 在收到 executor 的 callback 后，更新 backend session 状态，backend 再联动更新 assignment 和 issue 状态。

**涉及文件：**
- `backend/app/services/callback_service.py`
- `backend/app/services/agent_assignment_service.py`
- `backend/app/services/workspace_issue_service.py`

**验收标准：**
- [x] spec 中明确三方状态映射关系
- [x] spec 中明确 callback 驱动的状态流转链路

#### 4.2 设计执行结果回写

**描述：** agent 执行完成后，需要将结果回写到 issue：

- 如果 issue 有 `related_project_id`，agent 在 sandbox 中产生的代码变更应通过 PR / commit 形式关联到 project
- issue 的 description 或 comment 中记录执行摘要（成功/失败、变更文件数、关键决策）
- 执行日志和 session 记录可通过 issue 详情页查看

第一版不建议自动创建 PR，而是将 agent 的工作成果保留在 sandbox 的 workspace 中，由人类成员决定是否采纳。

**涉及文件：**
- `backend/app/services/agent_assignment_service.py`
- `frontend/features/issues/ui/`

**验收标准：**
- [x] spec 中明确执行结果不自动创建 PR
- [x] spec 中明确结果保留在 sandbox workspace 中
- [x] spec 中明确前端可查看执行 session

#### 4.3 设计前端执行状态展示

**描述：** 在 issue 详情页展示 AI assignee 的执行状态：

- 显示当前 assignment 状态（pending / running / completed / failed）
- 运行中时显示容器信息和执行时长
- 提供查看执行 session 的入口（跳转到 chat/session 详情）
- 提供手动重试、取消、释放 sandbox 的操作

**涉及文件：**
- `frontend/features/issues/ui/issue-detail.tsx`
- `frontend/features/issues/api/`

**验收标准：**
- [x] spec 中明确前端展示的执行状态信息
- [x] spec 中明确用户可执行的操作（重试/取消/释放）

---

## Phase 5: 接入审计日志

### 目标

为 agent assignment 的关键操作添加审计日志记录。

### 任务清单

#### 5.1 为 assignment 操作接入审计日志

**描述：** 在 agent_assignment 相关 service 方法上添加 `@auditable` 装饰器：

- `agent_assignment.created` — 分配 AI preset 到 issue
- `agent_assignment.triggered` — 触发执行
- `agent_assignment.completed` — 执行完成
- `agent_assignment.failed` — 执行失败
- `agent_assignment.cancelled` — 取消分配
- `agent_assignment.retried` — 重试执行

**涉及文件：**
- `backend/app/services/agent_assignment_service.py`

**验收标准：**
- [x] spec 中明确 assignment 全生命周期审计点
- [x] spec 中明确 metadata 包含 trigger_mode、preset_id、issue_id 等关键信息

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 持久化 sandbox 资源泄漏 | 容器长期占用导致资源耗尽 | 设置最大存活时间、空闲超时自动回收、用户手动释放 |
| 定时任务轮询对 backend 压力过大 | 影响正常 API 响应 | 控制轮询间隔（≥60s）、限制单次查询数量、使用专用查询接口 |
| AI assignee 执行结果不可控 | agent 产生错误代码或破坏性变更 | sandbox 文件系统隔离、不自动创建 PR、结果由人类审核 |
| prompt 生成质量不佳 | agent 无法正确理解任务 | prompt 模板化 + 用户可编辑、后续支持自定义 prompt 模板 |
| issue 和 assignment 状态不一致 | 用户看到错误状态 | callback 驱动的单向状态流转、幂等更新 |
| 执行层感知 workspace 导致范围膨胀 | executor/executor_manager 改动过大 | 执行层只接收 session/project/preset，workspace 校验留在 backend |

---

## 关联文档

- **Constitution:** [2026-04-15-workspace-team-multitenancy.md](/Users/bytedance/Developer/poco-agent/specs/constitution/2026-04-15-workspace-team-multitenancy.md)
- **前置依赖:** [00-workspace-tenancy-foundation-plan.md](/Users/bytedance/Developer/poco-agent/specs/draft/00-workspace-tenancy-foundation-plan.md)、[01-workspace-collaboration-plan.md](/Users/bytedance/Developer/poco-agent/specs/draft/01-workspace-collaboration-plan.md)
- **设计范式:** `dev-notes/设计范式/声明式可插拔审计日志.md`

---

## 总结

本计划在现有的 persistent container 和 APScheduler 基础设施上，建立了 issue → preset → agent execution 的自动化链路。核心设计原则是：执行层不感知 workspace（权限校验留在 backend），两种触发模式（持久化 sandbox 和定时任务）正交共存，执行结果由人类审核而非自动采纳。这使得 Poco 从"交互式编码助手"扩展为"团队自主执行平台"，同时保持了架构的简洁性和可维护性。
