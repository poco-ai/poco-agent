# Workspace tenancy foundation plan

## 元数据

| 字段 | 值 |
|------|-----|
| **创建日期** | 2026-04-15 |
| **预期改动范围** | backend auth / backend tenancy model / backend audit logging / backend API / frontend shell context / frontend workspaces feature |
| **改动类型** | feat |
| **优先级** | P0 |
| **状态** | drafting |

## 实施阶段

- [ ] Phase 0: 明确术语、命名和架构边界
- [ ] Phase 1: 建立 auth mode 与本地部署兼容策略
- [ ] Phase 2: 建立 workspace、member、invite 基础模型
- [ ] Phase 3: 定义团队角色与基础权限语义
- [ ] Phase 4: 建立声明式审计日志基础设施
- [ ] Phase 5: 建立前端 workspace 上下文与导航入口

---

## 背景

### 问题陈述

当前系统已经具备用户登录和按 `user_id` 隔离的大部分基础，但它仍缺少真正的 workspace 级边界，因此更像"多用户系统"，而不是"多租户系统"。与此同时，产品目标并不只有云端团队协作，还明确要求保留本地部署体验：本地部署时可以不启用 OAuth；团队部署时要支持 workspace、成员、邀请与权限；前端和后端都要能区分"当前是个人模式还是团队模式"。

### 目标

本计划的目标是建立一个稳定的 tenancy 基础层，用于支撑后续 shared project、shared preset、issue board 和 agent execution 等团队协作能力。

本计划不覆盖看板、共享项目、共享预设、issue 执行触发等高层协作功能，只负责它们依赖的租户基础设施和审计日志基础设施。

### 关键洞察

#### 1. `AUTH_MODE` 和 workspace 能力不是一回事

`AUTH_MODE` 用来控制是否要求登录。workspace/team 能力是另一层产品语义。如果把两者混成一个布尔变量，后续很难同时兼容本地部署和团队协作。

#### 2. 这份 spec 必须遵守当前仓库的分层约束

根部 [AGENTS.md](/Users/bytedance/Developer/poco-agent/specs/AGENTS.md) 已经明确 backend 采用 `api/v1`、`services`、`repositories`、`schemas` 分层，frontend 采用 feature-first 组织。因此 tenancy 设计不能只停留在概念层，而必须明确哪些能力落在 API、Service、Repository、Schema，以及新的前端 feature 应如何组织。

#### 3. 需要避开现有 `backend/app/schemas/workspace.py` 的命名冲突

当前 [backend/app/schemas/workspace.py](/Users/bytedance/Developer/poco-agent/backend/app/schemas/workspace.py) 已经用于 session 导出 workspace 文件树，不适合再承载 tenancy schema。后续 tenancy 相关 schema 应另起文件，例如 `workspace_tenancy.py`、`workspace_member.py`、`workspace_invite.py` 或 `team.py`。

---

## Phase 0: 明确术语、命名和架构边界

### 目标

统一本计划使用的核心术语、文件命名和模块分层，避免后续实现过程中概念混乱或与现有结构冲突。

### 任务清单

#### 0.1 统一后端域术语

**描述：** 明确后端域模型统一使用以下术语：

- `workspace`：团队或空间边界
- `personal workspace`：用户个人空间
- `shared workspace`：多人协作空间
- `membership`：用户与 workspace 的成员关系
- `invite`：用于加入 workspace 的邀请实体

前端文案层可以显示"团队"或 "Team"，但后端模型、数据库表和 schema 尽量统一使用 `workspace`。

**涉及文件：**
- `backend/app/models/` - 新增 tenancy 相关模型
- `backend/app/schemas/` - 新增 tenancy 相关 schema
- `frontend/features/workspaces/` - 提供前端上下文和 UI

**验收标准：**
- [ ] spec 中不再混用 `team`、`tenant`、`workspace` 作为后端模型名
- [ ] spec 中明确前端文案和后端模型名可以不同

#### 0.2 明确新增模块的目录落点

**描述：** 根据当前仓库架构，明确 tenancy 基础层建议新增如下模块：

- Backend API: `backend/app/api/v1/workspaces.py`、`workspace_members.py`、`workspace_invites.py`
- Backend Services: `backend/app/services/workspace_service.py`、`workspace_member_service.py`、`workspace_invite_service.py`
- Backend Repositories: `backend/app/repositories/workspace_repository.py`、`workspace_member_repository.py`、`workspace_invite_repository.py`
- Backend Schemas: 避免使用 `workspace.py`，改用 `workspace_tenancy.py` 或拆分文件
- Frontend feature: `frontend/features/workspaces/{api,model,ui,lib,index.ts}`

这符合当前项目的 feature-first 和 service/repository 分层要求，也能避免把新能力继续塞进不相关文件。

**涉及文件：**
- `backend/app/api/v1/`
- `backend/app/services/`
- `backend/app/repositories/`
- `backend/app/schemas/`
- `frontend/features/`

**验收标准：**
- [ ] spec 中明确 backend 的 API、Service、Repository、Schema 分层
- [ ] spec 中明确 frontend 的新 feature 不继续扩展 `services/` 旧模式

---

## Phase 1: 建立 auth mode 与本地部署兼容策略

### 目标

让系统先具备"本地模式"和"登录模式"共存的基础能力，为后续 workspace 引入稳定入口。

### 任务清单

#### 1.1 定义 `AUTH_MODE`

**描述：** 在 backend settings 中引入显式 auth 模式，建议至少支持：

- `disabled`
- `oauth_required`

必要时可预留 `optional`，但第一版不强制实现。

为贴合当前架构，这个配置应由 `backend/app/core/settings.py` 统一读取，路由依赖通过 `backend/app/core/deps.py` 控制行为，而不是单独做一层与现有依赖体系平行的"鉴权中间件系统"。

**涉及文件：**
- `backend/app/core/settings.py`
- `backend/app/core/deps.py`
- `backend/.env.example`

**验收标准：**
- [ ] spec 中明确 `AUTH_MODE` 语义
- [ ] spec 中明确本地默认推荐值
- [ ] spec 中不使用 `MULTI_TENANT_ENABLED` 替代 auth mode

#### 1.2 定义 `/auth/config` 与 SSR 判定入口

**描述：** 为了匹配当前前端 SSR 鉴权逻辑，应定义轻量配置接口，例如 `/api/v1/auth/config`，返回 auth mode、可用 provider 和是否启用 workspace 能力。这样 `frontend/features/auth/lib/server-session.ts` 和 shell route 可以在服务端知道当前到底是本地模式还是登录模式。

**涉及文件：**
- `backend/app/api/v1/auth.py`
- `backend/app/schemas/auth.py`
- `frontend/features/auth/lib/server-session.ts`
- `frontend/services/api-client.ts`

**验收标准：**
- [ ] spec 中明确前端 SSR 不能只靠 session cookie 判断模式
- [ ] spec 中明确 auth config 作为服务端守卫输入

#### 1.3 定义默认个人空间行为

**描述：** 无论是否登录，系统都需要存在稳定的个人空间语义：

- `AUTH_MODE=disabled` 时，系统使用本地默认用户和本地默认个人空间
- `AUTH_MODE=oauth_required` 时，登录用户自动拥有个人空间

这一步只定义 tenancy 入口，不直接改变 session、task、executor 的 ownership 协议。

**涉及文件：**
- `backend/app/core/deps.py`
- `backend/app/services/auth_service.py`
- `backend/app/services/session_service.py`
- `frontend/features/workspaces/model/`

**验收标准：**
- [ ] spec 中明确匿名模式下的默认用户/默认空间策略
- [ ] spec 中明确登录模式下的个人空间初始化策略
- [ ] spec 中明确第一阶段不要求 executor_manager 感知 workspace

---

## Phase 2: 建立 workspace、member、invite 基础模型

### 目标

定义 workspace 及其成员、邀请关系的数据模型、repository 责任边界和基础 API 契约。

### 任务清单

#### 2.1 新增 workspace 主模型

**描述：** 设计 `workspaces` 表，至少包含以下字段：

- `id`
- `name`
- `slug`
- `kind`，例如 `personal` / `shared`
- `owner_user_id`
- `created_at`
- `updated_at`

数据库模型返回 SQLAlchemy 实例，service 层再组装为显式 response schema，符合当前 backend 分层规则。

**涉及文件：**
- `backend/app/models/workspace.py`
- `backend/app/repositories/workspace_repository.py`
- `backend/app/services/workspace_service.py`
- `backend/app/schemas/workspace_tenancy.py`
- `backend/alembic/versions/*`

**验收标准：**
- [ ] spec 中明确 personal/shared workspace 的区分方式
- [ ] spec 中明确 workspace service 不直接返回 `dict[str, Any]`
- [ ] spec 中明确 migration 采用 `alembic revision --autogenerate`

#### 2.2 新增 membership 模型

**描述：** 设计 `workspace_members` 表，至少包含：

- `workspace_id`
- `user_id`
- `role`
- `joined_at`
- `invited_by`
- `status`

角色放在 membership 而不是 `users` 表上，这样更符合一个用户可加入多个 workspace 的多租户模型。

**涉及文件：**
- `backend/app/models/workspace_member.py`
- `backend/app/repositories/workspace_member_repository.py`
- `backend/app/services/workspace_member_service.py`
- `backend/app/schemas/workspace_member.py`
- `backend/alembic/versions/*`

**验收标准：**
- [ ] spec 中明确 membership 负责表示团队关系
- [ ] spec 中明确角色存放位置在 membership

#### 2.3 新增 invite 模型

**描述：** 设计 `workspace_invites` 表，第一版以过期邀请链接为主，至少包含：

- `workspace_id`
- `token`
- `role`
- `expires_at`
- `created_by`
- `max_uses`
- `used_count`
- `revoked_at`

**涉及文件：**
- `backend/app/models/workspace_invite.py`
- `backend/app/repositories/workspace_invite_repository.py`
- `backend/app/services/workspace_invite_service.py`
- `backend/app/schemas/workspace_invite.py`
- `backend/alembic/versions/*`

**验收标准：**
- [ ] spec 中明确邀请可过期、可撤销
- [ ] spec 中明确邀请可指定加入角色
- [ ] spec 中明确不是永久通用邀请码

---

## Phase 3: 定义团队角色与基础权限语义

### 目标

定义 workspace 级别的角色和基础权限，并与现有 backend service 责任边界对齐。

### 任务清单

#### 3.1 定义最小角色集

**描述：** 第一版采用三档角色：

- `owner`
- `admin`
- `member`

后续如有必要，再单独引入 `viewer`。第一版不建议一开始就做过多角色，以免 service 和前端状态模型过度复杂。

**涉及文件：**
- `backend/app/schemas/workspace_member.py`
- `backend/app/services/workspace_member_service.py`
- `frontend/features/workspaces/model/`

**验收标准：**
- [ ] spec 中明确每个角色的职责边界
- [ ] spec 中没有一开始引入过多角色复杂度

#### 3.2 明确团队级操作权限

**描述：** 先定义团队级操作的权限分配，例如：

- owner：删除 workspace、转移 ownership、管理所有角色与邀请
- admin：管理大部分资源和邀请，但不能转移 ownership
- member：参与团队资源协作

权限判断建议收口在 workspace 相关 service 或授权 helper 中，而不是散落在 route 文件中。route 只负责注入 `db`、当前用户和 request schema。

**涉及文件：**
- `backend/app/api/v1/workspaces.py`
- `backend/app/services/workspace_service.py`
- `backend/app/services/workspace_member_service.py`

**验收标准：**
- [ ] spec 中明确 owner/admin/member 的团队级权限
- [ ] spec 中明确 route 保持薄，业务判断放在 service

---

## Phase 4: 建立声明式审计日志基础设施

### 目标

建立可插拔的审计日志系统，为所有团队操作提供统一的记录能力。本阶段只建设基础设施和核心操作日志，不涉及 UI。

### 设计原则

审计日志系统采用**声明式装饰器 + 配置层解耦**的架构：

- Service 方法通过 `@auditable(action="...")` 声明"这个方法会产生什么日志"
- 配置层（`AuditConfig`）决定"这个日志是否真的写入"
- 新增审计点只需加装饰器，开关审计只需改配置，零基础设施改动

设计范式详见：`dev-notes/设计范式/声明式可插拔审计日志.md`

### 任务清单

#### 4.1 定义 `activity_logs` 数据模型

**描述：** 设计单表统一审计日志模型，至少包含：

- `id` (UUID)
- `workspace_id` (UUID, FK → workspaces)
- `actor_user_id` (UUID, FK → users)
- `action` (VARCHAR) — 点分命名，如 `workspace.member_role_changed`
- `target_type` (VARCHAR) — 如 `workspace`、`member`、`issue`、`board`、`project`
- `target_id` (VARCHAR)
- `metadata` (JSONB) — 变更详情，不同操作携带不同结构
- `created_at` (TIMESTAMP WITH TIME ZONE)

索引：`(workspace_id, created_at DESC)`、`(target_type, target_id)`、`(actor_user_id)`

**涉及文件：**
- `backend/app/models/activity_log.py`（新建）
- `backend/app/repositories/activity_log_repository.py`（新建）
- `backend/app/schemas/activity_log.py`（新建）
- `backend/alembic/versions/*`

**验收标准：**
- [ ] spec 中明确单表统一模型，不按域拆表
- [ ] spec 中明确 metadata 使用 JSONB
- [ ] spec 中明确 action 使用点分命名空间

#### 4.2 实现 `@auditable` 装饰器和 `AuditConfig`

**描述：** 实现声明式审计日志写入机制：

- `@auditable(action, target_type, target_id, workspace_id, metadata_fn)` 装饰器，在 service 方法执行完毕后提取日志信息
- `AuditConfig` 从 settings 读取规则，支持精确匹配和通配符（如 `issue.*`），最长前缀匹配优先
- `ActivityLogger` 服务类，接收装饰器提取的信息，查询 AuditConfig 后决定是否写入

**涉及文件：**
- `backend/app/core/audit.py`（新建）— 装饰器和 AuditConfig
- `backend/app/services/activity_logger.py`（新建）— ActivityLogger 服务
- `backend/app/core/settings.py` — 新增 AUDIT_RULES 配置

**验收标准：**
- [ ] spec 中明确装饰器只声明意图，不直接写数据库
- [ ] spec 中明确配置层支持通配符和 default fallback
- [ ] spec 中明确关闭某类审计只需改配置，不改代码

#### 4.3 为 tenancy 核心操作接入审计日志

**描述：** 在 workspace、member、invite 相关 service 方法上添加 `@auditable` 装饰器，覆盖以下操作：

- workspace: `created`、`updated`、`deleted`、`ownership_transferred`
- member: `joined`、`left`、`removed`、`role_changed`
- invite: `created`、`accepted`、`revoked`

**涉及文件：**
- `backend/app/services/workspace_service.py`
- `backend/app/services/workspace_member_service.py`
- `backend/app/services/workspace_invite_service.py`

**验收标准：**
- [ ] spec 中明确 tenancy 核心操作全覆盖
- [ ] spec 中明确其他域（issue、board、project）的审计日志在各自 spec 中定义

---

## Phase 5: 建立前端 workspace 上下文与导航入口

### 目标

让前端在 shell 层能表达"当前位于哪个 workspace"，而不只是提供一个 Team 管理页面。

### 任务清单

#### 5.1 设计 `features/workspaces`

**描述：** 新的 tenancy 前端 feature 应遵循 AGENTS 约束，优先采用：

- `frontend/features/workspaces/api/`
- `frontend/features/workspaces/model/`
- `frontend/features/workspaces/ui/`
- `frontend/features/workspaces/lib/`
- `frontend/features/workspaces/index.ts`

不要为新功能继续增加 `features/workspaces/services/` 作为业务逻辑入口。

**涉及文件：**
- `frontend/features/workspaces/`（新建）
- `frontend/services/api-client.ts`

**验收标准：**
- [ ] spec 中明确新 feature 的目录结构
- [ ] spec 中明确 API 调用在 `api/`，状态和上下文在 `model/`

#### 5.2 设计 shell 入口与 route 组织

**描述：** 为了贴合当前 App Router 组织方式，建议新增薄 route 文件，例如：

- `frontend/app/[lng]/(shell)/team/page.tsx`
- `frontend/app/[lng]/(shell)/team/members/page.tsx`
- `frontend/app/[lng]/(shell)/team/invites/page.tsx`

这些 route 文件只负责组装 feature 公共 API，真正的交互组件和状态逻辑都下沉到 `features/workspaces`。

**涉及文件：**
- `frontend/app/[lng]/(shell)/team/`
- `frontend/components/shell/`
- `frontend/features/workspaces/`

**验收标准：**
- [ ] spec 中明确 route 文件保持薄
- [ ] spec 中明确 tenancy UI 复用现有 shell 导航体系

#### 5.3 明确 i18n 与展示要求

**描述：** 所有新增用户可见文案必须接入现有 i18n 体系，不能在新 route 或 feature 里硬编码 "Team"、"Invite"、"Members"等文案。

**涉及文件：**
- `frontend/lib/i18n/locales/*/translation.json`
- `frontend/features/workspaces/ui/`
- `frontend/components/shell/`

**验收标准：**
- [ ] spec 中明确新增 Team/workspace 文案进入 i18n
- [ ] spec 中明确 shell 入口和设置页都遵循现有设计系统变量

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| auth mode 与 workspace mode 概念混淆 | 配置和实现容易走偏 | 在 settings、API 和前端上下文中分开建模 |
| tenancy schema 与现有 `schemas/workspace.py` 冲突 | 文件命名和语义混乱 | tenancy schema 另起文件 |
| 把角色判断散落在 route 层 | 后续维护困难 | 统一收口到 service 层 |
| 新前端功能继续沿用旧 `services/` 组织 | 边界继续恶化 | 新功能严格采用 `api/model/ui/lib` |
| 提前要求 executor_manager 改协议 | 范围迅速膨胀 | 第一阶段保持 session 仍然 user-owned |
| 审计日志写入失败影响主流程 | 业务操作被阻塞 | 审计写入采用 fire-and-forget，不阻塞主事务 |

---

## 关联文档

- **Constitution:** [2026-04-15-workspace-team-multitenancy.md](/Users/bytedance/Developer/poco-agent/specs/constitution/2026-04-15-workspace-team-multitenancy.md)
- **前置调研:** [2026-04-15-workspace-team-multitenancy-research.md](/Users/bytedance/Developer/poco-agent/specs/draft/2026-04-15-workspace-team-multitenancy-research.md)
- **下游 spec:** [01-workspace-collaboration-plan.md](/Users/bytedance/Developer/poco-agent/specs/draft/01-workspace-collaboration-plan.md)、[02-workspace-agent-execution-plan.md](/Users/bytedance/Developer/poco-agent/specs/draft/02-workspace-agent-execution-plan.md)

---

## 总结

本计划定义的是多租户的基础骨架和审计日志基础设施，而不是最终的协作能力集合。只有先把 `AUTH_MODE`、workspace、membership、invite、role、前端 workspace 上下文和可插拔审计日志建立起来，后续的 shared presets、shared projects、issue board 和 agent execution 才有稳定的归属和权限基础，而且不会偏离当前 Poco 的后端分层和前端 feature-first 架构。
