# Workspace agent execution hardening plan

## 元数据

| 字段 | 值 |
|------|-----|
| **创建日期** | 2026-04-16 |
| **预期改动范围** | backend issue assignment transitions / backend scheduling semantics / backend state lifecycle / frontend issue assignment UX |
| **改动类型** | fix |
| **优先级** | P1 |
| **状态** | proposed |

## 实施阶段

- [ ] Phase 0: 明确本次收紧的边界与非目标
- [ ] Phase 1: 设计 assignee 切换时的执行处置协议
- [ ] Phase 2: 收紧 scheduled task 的首次触发语义
- [ ] Phase 3: 修正 assignment、issue、session 的生命周期约束
- [ ] Phase 4: 补齐前端确认交互与回归测试

---

## 背景

### 问题陈述

[02-workspace-agent-execution-plan.md](/Users/bytedance/Developer/poco-agent/specs/draft/02-workspace-agent-execution-plan.md) 已经把 issue → preset → agent execution 的主链路定义完整，并且对应实现已经提交。但在实现复盘中暴露出几个不应继续留在应用层“自由发挥”的行为缺口：assignee 切换会影响正在运行的 session，scheduled task 的首次触发时间存在歧义，旧 assignment 的执行上下文可能在切换后失联。

这些问题不属于推翻 `02` 的方向，而是需要一份单独的 hardening spec 来补充“状态机如何收口”和“用户确认点放在哪里”。这样可以避免反复修改已完成 spec，也能让后续修复实现时有一份明确的 follow-up 依据。

### 目标

本计划的目标是收紧 workspace agent execution 的行为语义，重点覆盖以下范围：

- assignee 切换时，如何处置正在运行或已保留的 AI execution context
- scheduled task 的首次执行时间，如何与 cron 表达式严格对齐
- assignment、issue、session 三者之间，哪些状态迁移必须是原子的
- 前端在提交高风险切换前，必须展示哪些确认信息

本计划不重新定义 workspace、issue board、preset、persistent sandbox 或 scheduled task 的基础概念。这些基础语义仍以 [02-workspace-agent-execution-plan.md](/Users/bytedance/Developer/poco-agent/specs/draft/02-workspace-agent-execution-plan.md) 和对应 constitution 为准。

### 关键洞察

#### 1. assignee 切换本质上是生命周期操作，不是字段更新

一旦 issue 已经绑定 AI assignment，`assignee_user_id` 或 `assignee_preset_id` 的变化就会影响 session、container、activity log 和 issue 状态。继续把它当成普通 PATCH 字段处理，会导致静默覆盖、孤儿 session 或责任归属不清。

#### 2. scheduled task 的“首次执行”必须服从 cron 语义

用户选择 `scheduled_task` 时，默认心智是“从下一个满足 cron 的时间点开始执行”，而不是“保存后立刻跑一次”。如果产品将“立即执行一次”也视为合法行为，它必须是单独的显式选项，不能混在基础语义里。

#### 3. 用户确认点必须前移到切换发生前

如果前端先提交 assignee 变更，再在后端被动发现旧 session 还在跑，系统只能在脏状态里补救。更稳妥的设计是先返回 impact preview，让用户决定是否终止 session、是否释放 retained container，然后再提交真正的切换请求。

---

## Phase 0: 明确本次收紧的边界与非目标

### 目标

这一阶段定义本次 hardening 的设计边界，避免修复实现时顺手扩展到不相关的产品能力。

### 任务清单

#### 0.1 明确本次计划处理的问题清单

本次计划只处理已经在当前实现中出现的行为偏差，不扩大为新的 roadmap 功能。

- assignee 从 AI 切换到人类或另一个 preset 时，旧 session 的处置
- persistent sandbox retained container 在切换场景中的处理
- scheduled task 的首次触发时间计算
- issue、assignment、session 三者的原子状态迁移

**非目标：**
- 不设计多 assignee 模型
- 不引入自动 PR、自动 merge 或自动采纳
- 不引入“scheduled task 保存后立即执行一次”的默认语义
- 不改造 executor 或 executor_manager 使其感知 workspace

**验收标准：**
- [ ] spec 中明确列出本次处理的问题清单与非目标

---

## Phase 1: 设计 assignee 切换时的执行处置协议

### 目标

这一阶段把“切换负责人”定义成一个显式协议，要求前端和 backend 一起参与，而不是由 service 层静默猜测。

### 任务清单

#### 1.1 定义切换矩阵

系统必须为以下切换定义统一语义：

- 人类 → AI preset：直接创建新 assignment，清除 `assignee_user_id`
- AI preset → 人类：先处置旧 execution context，再写入新的人类 assignee
- AI preset → 另一个 AI preset：先处置旧 execution context，再创建或更新新的 AI assignment
- AI preset → 未分配：先处置旧 execution context，再清空 assignee

在任意时刻，一个 issue 只能有一个活跃 assignee。系统不能出现“新 assignee 已生效，但旧 AI session 仍在继续执行”的状态。

**验收标准：**
- [ ] spec 中明确所有 assignee 切换路径的统一语义
- [ ] spec 中明确任意时刻只能有一个活跃 assignee

#### 1.2 定义 execution disposition

当旧 assignee 为 AI preset 时，backend 必须把 execution disposition 视为显式输入，而不是内部默认分支。

建议第一版支持以下 disposition：

- `no_active_execution`: backend 已确认没有活跃 session，允许直接切换
- `terminate_and_keep_artifacts`: 终止活跃 session，但保留已有 session 记录和 retained container
- `terminate_and_release_artifacts`: 终止活跃 session，并释放 retained container

如果请求缺少 disposition，而 backend 发现当前 assignment 仍有活跃 session 或 retained container，接口必须拒绝直接修改 assignee，并返回 impact preview 所需数据。

**涉及文件：**
- `backend/app/api/v1/workspace_issues.py`
- `backend/app/services/workspace_issue_service.py`
- `backend/app/services/agent_assignment_service.py`

**验收标准：**
- [ ] spec 中明确 execution disposition 是显式协议字段
- [ ] spec 中明确 backend 在缺少 disposition 时不能静默覆盖旧 assignment

#### 1.3 定义 impact preview 交互

在真正提交 assignee 切换前，前端必须先拿到 impact preview，并向用户展示本次切换会影响哪些执行资产。

impact preview 至少包含：

- 当前 assignment 状态
- 当前 session 状态
- 是否存在 retained persistent sandbox
- 当前切换动作会不会触发终止 session
- 当前切换动作会不会释放 retained container

如果存在活跃 session，前端必须给出清晰确认文案，例如“当前 issue 仍有运行中的 AI 执行。切换负责人前，需要先终止这段执行。”第一版不支持保留活跃 session 并继续切换 assignee。

**涉及文件：**
- `frontend/features/issues/ui/`
- `frontend/features/issues/api/`
- `backend/app/api/v1/workspace_issues.py`

**验收标准：**
- [ ] spec 中明确前端必须先展示 impact preview
- [ ] spec 中明确活跃 session 场景下只能“终止后切换”或取消

---

## Phase 2: 收紧 scheduled task 的首次触发语义

### 目标

这一阶段要求 scheduled task 的首次执行时间与 cron 表达式严格一致，避免保存后立即执行造成用户预期偏差。

### 任务清单

#### 2.1 定义首次触发时间计算

系统创建 `scheduled_task` assignment 时，必须以 `created_at` 或独立记录的 `schedule_effective_from` 作为基准，计算下一个满足 cron 的时间点，并将其视为首次可执行时间。

示例：

- issue 在 `2026-04-16 08:30` 创建，cron 为 `0 9 * * *`，首次执行时间是 `2026-04-16 09:00`
- issue 在 `2026-04-16 09:05` 创建，cron 为 `0 9 * * *`，首次执行时间是 `2026-04-17 09:00`

保存 scheduled assignment 后立即执行一次，不属于默认语义。如果产品后续需要该能力，应通过单独字段表达，例如 `run_immediately_once`。

**涉及文件：**
- `backend/app/services/agent_assignment_service.py`
- `backend/app/repositories/agent_assignment_repository.py`
- `executor_manager/app/services/agent_assignment_dispatch_service.py`

**验收标准：**
- [ ] spec 中明确 scheduled task 的首次执行必须与 cron 对齐
- [ ] spec 中明确“保存后立即执行一次”不是默认行为

#### 2.2 定义调度器跳过与重试语义

调度器在轮询 scheduled assignment 时，必须区分三类情况：

- 尚未到达 next run：跳过，不更新 `last_triggered_at`
- 已到达 next run，但当前仍有活跃 execution：跳过，并保留本次 due 状态，等待下次轮询继续判断
- 已到达 next run，且没有活跃 execution：触发执行，并更新 `last_triggered_at`

调度器不能因为“当前有活跃 execution”就把本次 due 时间吞掉，否则会破坏 cron 的可解释性。

**验收标准：**
- [ ] spec 中明确 due 但因活跃 execution 被跳过时，不能静默推进调度基线

---

## Phase 3: 修正 assignment、issue、session 的生命周期约束

### 目标

这一阶段把几个当前容易被写散的状态约束收成可实现的规则。

### 任务清单

#### 3.1 定义切换时的旧 execution 收口规则

旧 assignment 的 session 不能通过简单清空 `session_id` 来“移除”。系统必须先完成旧 execution 的收口，再提交新的 assignee。

收口规则如下：

- 如果旧 assignment 存在 `pending`、`running` 或 `canceling` session，必须先发起取消
- 如果旧 assignment 的 session 已结束，但 retained container 仍存在，是否释放由 disposition 决定
- 如果旧 assignment 没有活跃 session 且没有 retained container，允许直接切换
- 切换完成后，旧 assignment 只能进入可追溯但非活跃状态，不能再作为当前 issue 的执行入口

**验收标准：**
- [ ] spec 中明确旧 session 不能靠清空外键伪装成已收口
- [ ] spec 中明确切换后不能留下与 issue 脱钩的活跃 session

#### 3.2 收紧状态映射

对于本次 hardening，以下状态映射需要额外强调：

| 场景 | assignment.status | issue.status | session.status |
|------|-------------------|--------------|----------------|
| scheduled assignment 已创建但未到首次触发时间 | `pending` | `todo` | — |
| persistent assignment 正在执行 | `running` | `in_progress` | `running` |
| assignee 切换触发旧 session 取消 | `cancelled` 或中间取消态 | `todo` 或等待新 assignee 生效 | `canceling` / `cancelled` |
| 新 assignee 已正式生效 | 新 assignment 接管 | 跟随新 assignment | 新旧 session 不可混淆 |

切换过程中，backend 必须保证“新 assignment 生效”与“旧 execution 不再活跃”之间不存在失配窗口。

**验收标准：**
- [ ] spec 中明确 scheduled 未到期时 issue 仍保持 `todo`
- [ ] spec 中明确切换过程不能出现新旧 assignment 同时活跃

---

## Phase 4: 补齐前端确认交互与回归测试

### 目标

这一阶段要求前端和测试一起补齐，避免 hardening 只停留在 backend 分支判断里。

### 任务清单

#### 4.1 定义前端交互补充项

issue 详情页至少需要新增以下交互：

- assignee 切换前的 impact preview 弹层
- retained container 是否同步释放的显式勾选项
- scheduled assignment 的 `next run` 展示
- scheduled mode 下的首次执行说明文案

这些信息必须在用户提交前可见，而不是在失败 toast 中事后解释。

**验收标准：**
- [ ] spec 中明确 issue 详情页需要展示 impact preview 和 next run

#### 4.2 定义回归测试覆盖面

这次修复至少需要补齐以下测试：

- AI → 人类切换且旧 session 仍在运行时，缺少 disposition 会被拒绝
- AI → AI 切换时，旧 session 必须先取消，不能留下孤儿执行
- scheduled assignment 创建后，首次执行时间按 cron 对齐
- due 时间到达但仍有活跃 execution 时，不推进调度基线

测试既要覆盖 backend service，也要覆盖必要的前端交互流。

**涉及文件：**
- `backend/tests/`
- `frontend/features/issues/`

**验收标准：**
- [ ] spec 中明确至少四类关键回归测试

---

## 风险与缓解

这份 hardening spec 主要解决错误状态和交互歧义，因此风险集中在兼容性和实现复杂度上。

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| assignee 切换引入额外确认步骤 | 用户觉得流程变长 | 只在存在活跃 session 或 retained container 时显示 impact preview |
| backend 引入 disposition 协议后与旧前端不兼容 | 旧请求直接失败 | 为缺少 disposition 的请求返回结构化 preview 响应，指导前端升级 |
| scheduled 首次触发语义调整影响现有用户认知 | 用户误以为保存后会立刻执行 | 在 UI 上明确展示 next run，并将“立即执行一次”保留为未来可选项 |
| 状态收口规则不完整 | 仍可能出现孤儿 session | 把切换路径纳入 service 测试和端到端回归测试 |

---

## 关联文档

- **基线 spec:** [02-workspace-agent-execution-plan.md](/Users/bytedance/Developer/poco-agent/specs/draft/02-workspace-agent-execution-plan.md)
- **Constitution:** [2026-04-15-workspace-agent-execution.md](/Users/bytedance/Developer/poco-agent/specs/constitution/2026-04-15-workspace-agent-execution.md)
- **Constitution:** [2026-04-15-workspace-team-multitenancy.md](/Users/bytedance/Developer/poco-agent/specs/constitution/2026-04-15-workspace-team-multitenancy.md)

---

## 总结

这份计划不是替换 `02`，而是把 `02` 在落地过程中暴露出来的边界条件正式收进规范。它的核心是三点：assignee 切换前置 impact preview，scheduled task 首次触发严格服从 cron，旧 execution context 必须显式收口。这样后续修复实现时，backend、frontend 和测试会对同一套行为语义对齐。
