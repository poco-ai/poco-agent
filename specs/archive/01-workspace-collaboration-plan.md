> **状态**：✅ 已完成 (2026-04-17)
> **归档原因**：功能已实现并测试通过

# Workspace collaboration plan

## 元数据

| 字段 | 值 |
|------|-----|
| **创建日期** | 2026-04-15 |
| **预期改动范围** | backend collaboration domain / project and preset ownership / issue board / audit logging / frontend workspaces and issues features |
| **改动类型** | feat |
| **优先级** | P1 |
| **状态** | completed |

## 实施阶段

- [x] Phase 0: 明确团队协作资源边界
- [x] Phase 1: 设计 shared preset 与 personal/workspace copy 流程
- [x] Phase 2: 设计 shared project 与复制派生流程
- [x] Phase 3: 设计团队看板与 issue 领域模型
- [x] Phase 4: 设计资源级可见性与访问控制
- [x] Phase 5: 为协作操作接入审计日志

---

## 背景

### 问题陈述

在具备 workspace 基础之后，Poco 团队模式的核心价值不在于"多人登录"，而在于"多人围绕共享资源协作"。核心需求包括：团队看板与 issue 管理，并能关联项目等已有生态资源；个人 project / preset 与团队 project / preset 之间的双向流转；团队成员和共享资源都需要分层权限；issue 支持人类和 AI preset 双模 assignee，AI assignee 可触发 agent 执行。

这说明团队协作不能只是把原有数据直接挪到 workspace 下，而需要重新定义资源归属、复制语义和权限边界。同时，这些设计还必须贴合当前项目结构：preset 已经有现成的 backend API 和 frontend feature，project 也已经有成熟的 `backend/app/services/project_service.py` 和 `frontend/features/projects/`，因此新方案更适合在现有领域模型上演进，而不是另起一套平行系统。

### 目标

本计划的目标是定义 workspace 模式下的协作资源模型和产品行为，重点覆盖：

- shared preset
- shared project
- issue board（含人类 + AI preset 双模 assignee）
- resource-level access

本计划不负责 workspace / invite / member 的基础模型，它依赖 [00-workspace-tenancy-foundation-plan.md](/Users/bytedance/Developer/poco-agent/specs/draft/00-workspace-tenancy-foundation-plan.md)。

本计划不负责 AI assignee 的执行触发链路（持久化 sandbox / 定时任务），该能力由 [02-workspace-agent-execution-plan.md](/Users/bytedance/Developer/poco-agent/specs/draft/02-workspace-agent-execution-plan.md) 负责。

### 关键洞察

#### 1. 第一版更适合"复制 / 派生"，不适合"实时同步"

个人和团队之间的双向操作方向合理，但第一版更稳妥的语义是 copy、fork、create shared copy，而不是实时同步或镜像。这样既能满足协作，又不会把冲突合并、权限回收、同步失败恢复等高复杂度问题一起拉进来。

#### 2. preset 和 project 的复杂度不同

preset 非常适合先做共享。project 的价值很高，但会触及文件、执行上下文和本地挂载语义，因此需要单独设计，不能简单照搬 preset 模式。

#### 3. 新的前端协作功能应沿用 feature-first，而不是继续增加 `services/`

根部 [AGENTS.md](/Users/bytedance/Developer/poco-agent/specs/AGENTS.md) 对新 feature 的组织已经很明确。因此 issue board 和 team collaboration 的前端能力更适合采用：

- `frontend/features/workspaces/`：团队项目、团队预设、成员、邀请、上下文
- `frontend/features/issues/`：board、issue 列表、issue 详情、筛选与视图状态

而不是再新增一个 `features/team-board/services/`。

#### 4. Issue 的 assignee 需要支持人类和 AI 双模

issue 不只是给人分配的任务容器，还可以分配给一个 preset（代表一个 AI agent 能力）。两种 assignee 共存，但触发不同的后续行为：人类 assignee 只做通知和跟踪，AI preset assignee 会触发 agent 执行链路（详见 [02-workspace-agent-execution-plan.md](/Users/bytedance/Developer/poco-agent/specs/draft/02-workspace-agent-execution-plan.md)）。

#### 5. 团队 project 允许直接执行 agent 任务

用户可以在团队 project 中直接创建新的 session，团队 project 不只是共享资产容器。执行时 session 仍由当前用户拥有，引用 workspace 范围内的 project。

#### 6. 复制行为保留来源追踪

个人空间和团队空间之间的 copy 行为保留来源追踪关系（类似 `forked_from`），但 fork 完成后源和目标是两份独立内容，不引入自动双向同步。

---

## Phase 0: 明确团队协作资源边界

### 目标

定义哪些资源进入团队协作范围，以及这些资源如何贴合当前 backend/frontend 领域组织。

### 任务清单

#### 0.1 定义首批协作资源范围

**描述：** 第一阶段聚焦以下资源：

- presets
- projects
- boards
- issues

暂不覆盖：

- sessions（session 仍 user-owned，只引用 workspace 资源）
- chats
- env vars
- model credentials
- local mounts
- 团队级 MCP 配置

这符合当前 Poco 的现实边界：project 和 preset 已经有清晰的 API 与前端 feature，适合先演进；session、chat 和本地挂载则直接连到执行链路，过早纳入团队共享会明显放大复杂度。

**涉及文件：**
- `backend/app/models/`
- `backend/app/services/preset_service.py`
- `backend/app/services/project_service.py`
- `frontend/features/capabilities/presets/`
- `frontend/features/projects/`

**验收标准：**
- [x] spec 中明确首批团队协作资源范围
- [x] spec 中明确哪些高风险资源暂不纳入

#### 0.2 定义统一归属元数据

**描述：** 协作资源逐步统一以下基础元数据：

- `scope`
- `workspace_id`
- `owner_user_id`
- `created_by`
- `created_at`
- `updated_by`
- `updated_at`

这些字段应通过 backend model + repository + service 逐层落地，而不是只在前端类型里补几个字段。

**涉及文件：**
- `backend/app/models/preset.py`
- `backend/app/models/project.py`
- `backend/app/schemas/preset.py`
- `backend/app/schemas/project.py`

**验收标准：**
- [x] spec 中明确 shared resource 不再只靠 `user_id` 表达归属
- [x] spec 中明确创建者和时间信息为必备展示属性

---

## Phase 1: 设计 shared preset 与 personal/workspace copy 流程

### 目标

把 preset 定义成第一批可稳定共享的团队资源，并建立个人空间与团队空间之间的复制流程。

### 任务清单

#### 1.1 定义 preset 的 workspace 归属模型

**描述：** 设计 preset 在团队模式下的归属方式，至少支持：

- 个人 preset
- workspace shared preset
- system preset

为了符合当前 backend 约束，preset 相关 API 仍应通过 `backend/app/api/v1/presets.py` 暴露，service 层继续收口在 `backend/app/services/preset_service.py`，repository 继续收口在 `preset_repository.py`。前端则尽量复用 `frontend/features/capabilities/presets/`，而不是再做一套平行的 team preset feature。

**涉及文件：**
- `backend/app/models/preset.py`
- `backend/app/repositories/preset_repository.py`
- `backend/app/services/preset_service.py`
- `backend/app/schemas/preset.py`
- `frontend/features/capabilities/presets/`

**验收标准：**
- [x] spec 中明确 preset 的三类 scope
- [x] spec 中明确 shared preset 需要展示创建者与创建时间
- [x] spec 中明确 preset 仍沿用现有 preset 领域 API，不另起平行资源

#### 1.2 定义 preset 的双向操作

**描述：** 第一版为 preset 提供以下操作语义：

- `Copy to workspace`
- `Copy to personal space`
- `Create shared preset`
- `Fork as personal preset`

这些操作本质上都是 mutation request，因此后续 schema 命名应遵循仓库约定，例如 `PresetCopyRequest`、`PresetCopyResponse`、`PresetForkRequest` 等，而不是在 service 中直接吞吐匿名字典。

复制行为保留来源追踪关系（`forked_from` 字段），但 fork 完成后源和目标独立。

**涉及文件：**
- `backend/app/api/v1/presets.py`
- `backend/app/services/preset_service.py`
- `backend/app/schemas/preset.py`
- `frontend/features/capabilities/presets/api/`
- `frontend/features/capabilities/presets/lib/`

**验收标准：**
- [x] spec 中明确是复制 / 派生而不是实时同步
- [x] spec 中明确复制后保留 `forked_from` 来源追踪
- [x] spec 中明确 request/response 使用显式 schema 命名

---

## Phase 2: 设计 shared project 与复制派生流程

### 目标

为团队共享 project 建立一套可控的复制式协作模型，并保证它和当前 task/session 执行链路兼容。

### 任务清单

#### 2.1 定义 shared project 的第一版边界

**描述：** shared project 第一版先定义为团队内可见、可复制的项目资源，不直接承诺与本地文件系统挂载深度联动。原因是当前本地挂载能力与部署模式、host path、安全边界强相关，直接把它带进 shared project 会迅速复杂化。

但团队 project 允许直接执行 agent 任务——用户可以在团队 project 中直接创建 session，而不是只当作共享资产容器。

**涉及文件：**
- `backend/app/models/project.py`
- `backend/app/repositories/project_repository.py`
- `backend/app/services/project_service.py`
- `backend/app/schemas/project.py`
- `frontend/features/projects/`

**验收标准：**
- [x] spec 中明确 shared project 第一版不直接绑定用户本地挂载
- [x] spec 中明确团队 project 允许直接执行 agent 任务
- [x] spec 中明确团队 project 的基础元数据

#### 2.2 定义 project 的双向复制语义

**描述：** 第一版提供以下操作：

- 从个人 project 复制到 workspace
- 从 workspace project 复制到个人空间
- 从 workspace project 派生新的 workspace project

这里的复制应明确区分"复制配置和元数据"与"复制文件快照"的策略。因为当前 project 已经和 project files、session workspace 导出、preset 选择等能力相关联，后续 spec 需要明确每类数据是否跟随复制。

复制行为保留来源追踪关系（`forked_from` 字段）。

**涉及文件：**
- `backend/app/api/v1/projects.py`
- `backend/app/services/project_service.py`
- `backend/app/services/project_file_service.py`
- `backend/app/schemas/project.py`
- `frontend/features/projects/api/`
- `frontend/features/projects/lib/`

**验收标准：**
- [x] spec 中明确复制行为的目标空间和 ownership 变化
- [x] spec 中明确不做实时双向同步
- [x] spec 中明确 project file 与 project metadata 的复制范围
- [x] spec 中明确复制后保留 `forked_from` 来源追踪

#### 2.3 明确 shared project 与 session 的关系

**描述：** 为了贴合当前 Poco 的执行链路，shared project 第一版应采用以下原则：

- session 仍由当前用户创建和拥有
- session 可以引用 workspace 范围内有权限的 project
- backend 在创建 session 时校验 workspace 资源访问权限
- executor 和 executor_manager 初期不需要基于 `workspace_id` 改协议

这可以让团队协作能力尽量停留在 backend API 和权限层，不一开始就侵入执行引擎协议。

**涉及文件：**
- `backend/app/services/session_service.py`
- `backend/app/services/task_service.py`
- `executor_manager/app/services/`
- `executor/app/schemas/`

**验收标准：**
- [x] spec 中明确 session 仍然 user-owned
- [x] spec 中明确共享 project 只影响资源选择和授权校验
- [x] spec 中明确第一版不要求 executor 协议感知 workspace

---

## Phase 3: 设计团队看板与 issue 领域模型

### 目标

定义团队看板和 issue 的第一版产品能力，使其既像 todo / issue，又能和 Poco 现有项目生态结合，并支持人类和 AI preset 双模 assignee。

### 任务清单

#### 3.1 定义 board 领域模型

**描述：** 设计团队看板模型，至少包含：

- `workspace_id`
- `name`
- `description`
- `created_by`
- `created_at`

为了贴合当前 backend 命名习惯，第一版更建议将 board 和 issue 作为单独的领域文件组织，例如 `workspace_board.py`、`workspace_issue.py`，避免使用过于宽泛的 `issue.py` 导致后续全局语义冲突。

**涉及文件：**
- `backend/app/models/workspace_board.py`
- `backend/app/repositories/workspace_board_repository.py`
- `backend/app/services/workspace_board_service.py`
- `backend/app/schemas/workspace_board.py`

**验收标准：**
- [x] spec 中明确 board 属于 workspace
- [x] spec 中明确 board 是 issue 的容器，而不是 project 的别名

#### 3.2 定义 issue 第一版字段模型

**描述：** 第一版 issue 支持可配置字段模板，但必须包含以下系统字段作为基础：

- `title`
- `description`
- `status`
- `type`
- `priority`
- `due_date`
- `assignee_user_id`（人类 assignee，可 nullable）
- `assignee_preset_id`（AI preset assignee，可 nullable）
- `reporter_user_id`
- `related_project_id`
- `creator_user_id`
- `created_at`
- `updated_at`

**双模 assignee 设计：**

- `assignee_user_id` 和 `assignee_preset_id` 互斥：一个 issue 同一时间只能有一个活跃 assignee（人类或 AI）
- 人类 assignee：常规任务分配，仅做通知和跟踪
- AI preset assignee：分配后可触发 agent 执行链路（详见 [02-workspace-agent-execution-plan.md](/Users/bytedance/Developer/poco-agent/specs/draft/02-workspace-agent-execution-plan.md)）
- 切换 assignee 类型时（如从人类改为 AI），旧的 assignee 自动清除

**涉及文件：**
- `backend/app/models/workspace_issue.py`
- `backend/app/repositories/workspace_issue_repository.py`
- `backend/app/services/workspace_issue_service.py`
- `backend/app/schemas/workspace_issue.py`
- `frontend/features/issues/`

**验收标准：**
- [x] spec 中明确 issue 的系统字段集合
- [x] spec 中明确双模 assignee 互斥约束
- [x] spec 中明确 assignee 切换时旧 assignee 自动清除

#### 3.3 定义可配置字段模板

**描述：** board 级别支持自定义字段模板，允许团队根据协作习惯配置字段结构。第一版建议：

- 每个 board 可以关联一组自定义字段定义（`workspace_board_fields` 表）
- 自定义字段类型支持：`text`、`number`、`date`、`select`、`multi_select`
- 自定义字段值存储在 `workspace_issue_field_values` 表中（issue × field → value）
- 系统字段不可删除或修改类型，自定义字段可增删改

这样既保证了系统字段的稳定性，又提供了灵活性。

**涉及文件：**
- `backend/app/models/workspace_board_field.py`（新建）
- `backend/app/models/workspace_issue_field_value.py`（新建）
- `backend/app/repositories/`
- `backend/app/schemas/`

**验收标准：**
- [x] spec 中明确系统字段不可删除
- [x] spec 中明确自定义字段的类型范围
- [x] spec 中明确自定义字段值使用独立关联表存储

#### 3.4 设计前端 issue feature 的组织方式

**描述：** 为贴合前端架构，新 issue 功能建议使用：

- `frontend/features/issues/api/`
- `frontend/features/issues/model/`
- `frontend/features/issues/ui/`
- `frontend/features/issues/lib/`
- `frontend/features/issues/index.ts`

路由层可以新增：

- `frontend/app/[lng]/(shell)/team/issues/page.tsx`
- `frontend/app/[lng]/(shell)/team/issues/[issueId]/page.tsx`

这些 route 只负责组装 feature 公共 API。所有用户可见文案都必须接入 i18n。

**涉及文件：**
- `frontend/features/issues/`（新建）
- `frontend/app/[lng]/(shell)/team/issues/`
- `frontend/lib/i18n/locales/*/translation.json`

**验收标准：**
- [x] spec 中明确 issues feature 目录结构
- [x] spec 中明确 route 文件保持薄
- [x] spec 中明确新增文案必须接入 i18n

---

## Phase 4: 设计资源级可见性与访问控制

### 目标

定义团队成员角色之外的资源级访问控制模型，让共享资源可以有不同可见范围，同时避免超出当前仓库可维护复杂度。

### 任务清单

#### 4.1 定义轻量资源访问策略

**描述：** 第一版资源访问策略建议采用轻量枚举，而不是完整 ACL 表。建议至少支持：

- `private`
- `workspace_read`
- `workspace_write`
- `admins_only`

这套策略更适合当前 backend service 层判断方式，也更容易在 frontend 侧映射为简单可解释的 UI。

**涉及文件：**
- `backend/app/models/`
- `backend/app/schemas/`
- `backend/app/services/`
- `frontend/features/`

**验收标准：**
- [x] spec 中明确资源访问策略集合
- [x] spec 中明确团队级角色和资源级策略的组合关系

#### 4.2 定义各类资源的默认策略

**描述：** 按资源类型定义默认策略，例如：

- shared preset：默认 `workspace_read`
- shared project：默认 `workspace_write` 或 `workspace_read`
- board：默认全体成员可见
- issue：默认继承 board 可见性

这一步需要特别说明：默认策略是产品默认值，不代表所有资源都必须支持完全一致的操作能力。

**涉及文件：**
- `backend/app/services/preset_service.py`
- `backend/app/services/project_service.py`
- `backend/app/services/workspace_board_service.py`
- `backend/app/services/workspace_issue_service.py`
- `frontend/features/capabilities/presets/`
- `frontend/features/projects/`
- `frontend/features/issues/`

**验收标准：**
- [x] spec 中明确每类资源的默认访问策略
- [x] spec 中明确 owner/admin/member 对资源策略的影响

---

## Phase 5: 为协作操作接入审计日志

### 目标

在 tenancy foundation 建立的审计基础设施之上，为协作资源操作添加审计日志记录。

### 任务清单

#### 5.1 为 board 操作接入审计日志

**描述：** 在 board 相关 service 方法上添加 `@auditable` 装饰器：

- `board.created`、`board.updated`、`board.deleted`

**涉及文件：**
- `backend/app/services/workspace_board_service.py`

**验收标准：**
- [x] spec 中明确 board 操作审计点
- [x] spec 中明确 metadata 包含 board 名称等关键信息

#### 5.2 为 issue 操作接入审计日志

**描述：** 在 issue 相关 service 方法上添加 `@auditable` 装饰器：

- `issue.created`、`issue.updated`、`issue.deleted`
- `issue.status_changed`、`issue.assigned`、`issue.unassigned`、`issue.priority_changed`

对于 assignee 相关操作，metadata 需要区分人类 assignee 和 AI preset assignee。

**涉及文件：**
- `backend/app/services/workspace_issue_service.py`

**验收标准：**
- [x] spec 中明确 issue 操作审计点
- [x] spec 中明确 assignee 类型在 metadata 中的区分方式

#### 5.3 为 project 操作接入审计日志

**描述：** 在 project 相关 service 方法上添加 `@auditable` 装饰器：

- `project.shared`、`project.forked`、`project.updated`、`project.deleted`

**涉及文件：**
- `backend/app/services/project_service.py`

**验收标准：**
- [x] spec 中明确 project 操作审计点
- [x] spec 中明确复制/派生操作记录来源和目标信息

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 一开始追求实时双向同步 | 复杂度和数据冲突过高 | 第一版只支持复制和派生 |
| shared project 直接绑定本地挂载 | 权限和执行语义混乱 | 第一版不把 shared project 与本地挂载深度耦合 |
| issue board 直接做成自定义字段平台 | 范围失控 | 系统字段 + 可配置自定义字段，两层分离 |
| 资源 ACL 设计过重 | 实现和使用成本过高 | 第一版采用轻量访问策略枚举 |
| 新前端协作功能继续扩散到 `services/` | 架构边界继续恶化 | 新 feature 严格采用 `api/model/ui/lib` |
| 双模 assignee 切换逻辑复杂 | 用户困惑或数据不一致 | 明确互斥约束，切换时自动清除旧 assignee |
| 自定义字段模板过度灵活 | 性能和查询复杂度上升 | 限制字段类型范围，自定义字段值使用独立表 |

---

## 关联文档

- **Constitution:** [2026-04-15-workspace-team-multitenancy.md](/Users/bytedance/Developer/poco-agent/specs/constitution/2026-04-15-workspace-team-multitenancy.md)
- **前置依赖:** [00-workspace-tenancy-foundation-plan.md](/Users/bytedance/Developer/poco-agent/specs/draft/00-workspace-tenancy-foundation-plan.md)
- **下游 spec:** [02-workspace-agent-execution-plan.md](/Users/bytedance/Developer/poco-agent/specs/draft/02-workspace-agent-execution-plan.md)

---

## 总结

本计划把团队协作能力分成五块：共享资源边界、preset 流转、project 流转、issue board（含双模 assignee 和可配置字段）、资源访问策略，以及协作操作审计日志。它的核心原则是先建立清晰、可解释、可验证的协作语义，再考虑更复杂的同步和细粒度 ACL，同时保证设计始终贴合 Poco 当前的 backend service/repository 分层、Next.js App Router 组织方式，以及 task-centric 执行链路。
