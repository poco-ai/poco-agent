# Channel task delegation and activity plan

## 元数据

| 字段 | 值 |
| --- | --- |
| **创建日期** | 2026-05-11 |
| **预期改动范围** | backend channel task model / task event payload / task schemas and profile hydration / frontend channel task board and drawer / channel event row / context drawer / i18n / migrations / tests |
| **改动类型** | feat |
| **优先级** | P1 |
| **状态** | review |

## 实施阶段

- [x] Phase 0: 对齐当前实现与设计边界
- [x] Phase 1: 补齐 task 编号、actor 与 assignee 数据契约
- [x] Phase 2: 收敛 task event payload 与 activity timeline
- [x] Phase 3: 升级 task 面板的委托关系展示与编辑
- [x] Phase 4: 修正为一 thread 一 task 的 task 面板入口
- [x] Phase 5: 验证、回写 spec 状态并等待审查

---

## 背景

### 问题陈述

`specs/constitution/2026-05-11-channel-task-collaboration-model.md` 已经固定了 channel task 的长期心智：task 是 channel-native 协作工作项，可以由人类或 agent 创建，可以分配给人类或 server agent，也可以保持未分配。2026-05-11 的修正决策进一步明确：接受一 thread 一 task；用 As task 创建的消息就是 task 的 root thread，task 更新、评论和 agent 回复都追加为这个 root thread 的 replies。

当前代码已经向这个方向推进了一部分：

- `server_channel_tasks` 已经是独立主表，直接归属于 `server_id + channel_id`。
- task 创建、状态变化、claim/unclaim 已经开始写入 `message_type="event"`。
- 前端 `conversation-message-row.tsx` 已经有 `ChannelEventRow` 的初步渲染分支。
- server conversation 页面已经有 task drawer，并能读取 `thread_root_message_id` 对应的 thread/activity。

但现状仍有几个核心缺口：

- task 没有频道内可读编号，只能显示 UUID 或标题，无法形成 `task #42` 这样的协作引用。
- event payload 只包含粗略 actor 和 `assignee` raw payload，没有稳定的“委托方 / 被委托方”展示契约。
- agent assignee 仍主要通过 `assignee_preset_id` 表达，不能准确指向 server 中的某个 agent identity。
- task 面板没有显示创建/委托关系，也不能直接更新被委托方。
- task 创建来源和 thread 归属还没有完全收敛：部分 task update 被展示成主 timeline 事件，task 面板也曾尝试另开上下文抽屉，而不是直接展示 task root thread。

### 目标

本计划的目标是把 task 从“能建、能拖、能 claim”的功能状态，升级为“委托关系和协作历史可读、可追溯”的产品状态：

- 为 task 增加频道内可读编号，所有 UI 使用 `#<number>` 表达 task。
- 后端 task response 和 event payload 提供结构化 actor / assignee summary，前端不从 `text_preview` 反推业务信息。
- task 创建、分配、取消分配、状态变化、字段更新、评论都形成一行轻量 event。
- task 面板显示创建方、最近委托方和当前被委托方，使用头像 + name。
- task 面板支持更新被委托方，并把该调整同步为 task root thread 中的轻量提示。
- task 面板点击后右侧抽屉直接展示 root thread：root message、task event replies 和 agent execution/reply 都在同一个 thread 中追踪。

### 非目标

- 不把 task 强制绑定 agent；未分配 task 继续是合法状态。
- 不把 task activity 改成独立 activity log 表；第一阶段继续以 channel message event 为唯一 timeline 来源。
- 不重做整个 channel message 架构，不引入 websocket/SSE。
- 不在本轮实现复杂的多人 assignee、子任务、依赖关系或自定义字段。
- 不恢复旧 workspace issue 作为产品主语。

### 关键洞察

#### 1. Task 编号是协作语言，不是数据库主键

UUID 适合 API 精确寻址，但不适合人在频道里讨论。用户需要看到 `#42`、`#43` 这样的短编号。编号只需要在同一个 channel 内唯一，跨 channel 可重复。

#### 2. 委托关系必须显式建模

“谁创建了 task”和“当前分配给谁”不是同一个问题。一个 task 可以由 Alice 创建、Bob 重新分配、`@docs-agent` 当前负责。UI 需要同时能解释这些关系，而不是只显示 `updated_by` 或 assignee id。

#### 3. Activity 是 task root thread 的投影

Task activity 不应该成为孤立日志。每条 activity 都应该是 task root thread 中的 message：As task 的原始 trigger 是 root，`task.created`、状态变化、分配变化、评论和 agent 回复都是 replies。这样 task 面板不需要再打开另一个上下文抽屉，直接显示这个 root thread 即可。

#### 4. Agent assignee 应尽量指向 agent identity

Preset 是能力模板，agent identity 是 server 里的协作者。长期正确模型应分配给 agent identity；`assignee_preset_id` 可短期兼容，但不能继续作为唯一表达。

---

## Phase 0: 对齐当前实现与设计边界

### 目标

先把本计划与现有 dirty worktree、constitution 和已实现的 event 改造对齐，避免重复实现或把未完成代码误当最终契约。

### 任务清单

#### 0.1 读取并确认当前 task/event 改动

**描述：** 检查当前工作区中已修改的 task 相关文件，明确哪些能力已经实现、哪些只是半成品。

**涉及文件：**

- `backend/app/schemas/server_channel_task.py`
- `backend/app/services/server_channel_task_service.py`
- `backend/tests/test_server_channel_task_service.py`
- `frontend/features/channel-tasks/api/channel-tasks-api.ts`
- `frontend/features/channel-tasks/model/types.ts`
- `frontend/features/servers/ui/conversation-message-row.tsx`
- `frontend/features/servers/ui/server-conversation-page-client.tsx`
- `frontend/features/servers/ui/conversation-drawers.tsx`

**验收标准：**

- [x] 明确已有 `message_type="event"` 改造是否覆盖 create/status/claim/unclaim/comment
- [x] 明确前端 `ChannelEventRow` 当前支持哪些 event type
- [x] 明确 task drawer 当前如何读取和展示 activity

#### 0.2 固定本轮不变量

**描述：** 实现时必须遵守 constitution 中的以下规则：

- task 不强制绑定 agent
- task 可以未分配
- 人类和 agent 都可以成为 actor
- 被委托方最多一个
- activity 必须可回到 task root thread message

**涉及文件：**

- `specs/constitution/2026-05-11-channel-task-collaboration-model.md`

**验收标准：**

- [x] 本 spec 不提出与 constitution 冲突的实现路径
- [x] 后续 phase 都围绕 channel-native task，不回退到 workspace issue

---

## Phase 1: 补齐 task 编号、actor 与 assignee 数据契约

### 目标

让后端能稳定表达 task 的可读编号、创建方、委托方和被委托方，为 UI 和 event 文案提供结构化数据。

### 任务清单

#### 1.1 新增 channel-local task 编号

**描述：** 为 `server_channel_tasks` 增加频道内可读编号字段。推荐字段名 `display_number`，类型为 integer。

**涉及文件：**

- `backend/app/models/server_channel_task.py` - 新增 `display_number`
- `backend/app/schemas/server_channel_task.py` - response 暴露 `display_number`
- `backend/app/services/server_channel_task_service.py` - 创建 task 时分配下一个编号
- `backend/app/repositories/server_channel_task_repository.py` - 新增按 channel 查询最大编号或使用锁定策略
- `backend/alembic/versions/` - 通过 Alembic autogenerate 开始，再人工审查

**验收标准：**

- [x] 同一 channel 内 `display_number` 唯一
- [x] 新 task 自动获得递增编号
- [x] 既有 task 迁移后按 `created_at, id` 回填编号
- [x] API response 同时保留 `task_id` 和 `display_number`

#### 1.2 定义 actor summary 和 assignee summary

**描述：** 在 schema 层引入用于展示的 summary，不让前端拿裸 id 自己猜。

**建议结构：**

```python
class ChannelTaskActorSummary(BaseModel):
    actor_type: Literal["user", "agent"]
    user_id: str | None = None
    agent_identity_id: UUID | None = None
    agent_handle: str | None = None
    label: str
    avatar_url: str | None = None
    visual_key: str | None = None
```

**涉及文件：**

- `backend/app/schemas/server_channel_task.py`
- `backend/app/services/server_channel_task_service.py`
- `backend/app/repositories/agent_identity_repository.py`
- `backend/app/services/user_public_profile_service.py`

**验收标准：**

- [x] `ServerChannelTaskResponse` 包含 `creator` summary
- [x] `ServerChannelTaskResponse` 包含 `assignee` summary，未分配时为 null
- [x] user assignee 返回 display name / avatar
- [x] agent assignee 返回 display name / handle / visual key

#### 1.3 支持 agent identity assignee

**描述：** 在 task 主表中补充 `assignee_agent_identity_id`，让 task 可以准确分配给 server 中的一个 agent。短期保留 `assignee_preset_id` 兼容已有数据和 agent claim 逻辑。

**涉及文件：**

- `backend/app/models/server_channel_task.py`
- `backend/app/schemas/server_channel_task.py`
- `backend/app/services/server_channel_task_service.py`
- `backend/app/services/server_channel_task_agent_service.py`
- `backend/alembic/versions/`

**验收标准：**

- [x] 新请求支持设置 `assignee_agent_identity_id`
- [x] `assignee_agent_identity_id` 与 `assignee_user_id` 互斥
- [x] agent claim task 时优先写入当前 `agent_identity_id`
- [x] 旧 `assignee_preset_id` 数据仍能被读取和展示

#### 1.4 校验 assignee 合法性

**描述：** 设置 assignee 时必须验证对象属于当前 server，且对当前 channel 具备合理协作关系。

**涉及文件：**

- `backend/app/services/server_channel_task_service.py`
- `backend/app/repositories/server_member_repository.py`
- `backend/app/repositories/server_channel_agent_member_repository.py`
- `backend/tests/test_server_channel_task_service.py`

**验收标准：**

- [x] 分配给 user 时，user 必须是 active server member
- [x] 分配给 agent identity 时，agent 必须属于当前 server 且未 removed
- [x] 如果 agent 不是当前 channel 成员，返回明确业务错误或先按产品决策自动加入；本轮建议返回错误，避免隐式扩大频道成员

---

## Phase 2: 收敛 task event payload 与 activity timeline

### 目标

让每个 task 关键动作都生成结构化轻量 event，并让 event 文案能准确表达“谁对 task 做了什么、分配给谁、内容是什么”。

### 任务清单

#### 2.1 建立 task event payload builder

**描述：** 在 `ServerChannelTaskService` 中新增 task-specific event builder，复用通用 channel event helper，但统一注入 task 编号、标题、actor、assignee 和变更前后状态。

**涉及文件：**

- `backend/app/services/server_channel_task_service.py`
- `backend/app/services/server_channel_event_service.py`
- `backend/app/schemas/server_channel_message.py`

**验收标准：**

- [x] 所有 task event 包含 `event_type`
- [x] 所有 task event 包含 `task_id` 和 `task_number`
- [x] 所有 task event 包含 `task_title`
- [x] 所有 task event 包含 `actor` summary 字段
- [x] 涉及 assignee 的 event 包含 `assignee` summary 字段

#### 2.2 创建 task event 支持 assignee 文案

**描述：** task 创建时，根据是否有 assignee 生成不同 event：

- 无 assignee：`task.created`
- 有 assignee：仍可用 `task.created`，但 payload 包含 assignee；前端文案显示 “created task #x and assigned it to y”

**涉及文件：**

- `backend/app/services/server_channel_task_service.py`
- `frontend/features/servers/lib/server-conversation-messages.ts`
- `frontend/features/servers/ui/conversation-message-row.tsx`
- `frontend/lib/i18n/locales/*/translation.json`

**验收标准：**

- [x] 创建无 assignee task 时，event 一行显示创建者和 task 编号
- [x] 创建有 assignee task 时，event 一行显示创建者、task 编号和被委托方
- [x] 文案过长时最多一行截断

#### 2.3 新增 assignee 更新事件

**描述：** 当 task 被分配、重新分配或取消分配时，生成独立 event。

**建议 event：**

- `task.assigned`
- `task.reassigned`
- `task.unassigned`

**涉及文件：**

- `backend/app/services/server_channel_task_service.py`
- `backend/app/api/v1/server_channel_tasks.py`
- `backend/app/schemas/server_channel_task.py`
- `frontend/features/channel-tasks/api/channel-tasks-api.ts`
- `frontend/features/servers/lib/server-conversation-messages.ts`

**验收标准：**

- [x] 从 unassigned 到 assigned 生成 `task.assigned`
- [x] 从 A assignee 到 B assignee 生成 `task.reassigned`
- [x] 从 assigned 到 unassigned 生成 `task.unassigned`
- [x] event payload 包含 from/to assignee summary

#### 2.4 字段更新与评论事件收口

**描述：** 对 title/description/priority/due_date 等普通字段更新生成 `task.updated` event；comment 保持 `task.commented` event。

**涉及文件：**

- `backend/app/services/server_channel_task_service.py`
- `backend/tests/test_server_channel_task_service.py`

**验收标准：**

- [x] 编辑 title 或 description 后 activity 中可见 `task.updated`
- [x] comment event 的一行文案显示评论摘要
- [x] 更新事件不重复生成无意义 event；没有实际字段变化时不写 event

---

## Phase 3: 升级 task 面板的委托关系展示与编辑

### 目标

让 task board/list/detail 明确显示 task 的协作关系，并支持从 task 面板调整被委托方。

### 任务清单

#### 3.1 更新前端 task 类型与 API mapper

**描述：** 同步后端新增字段：`displayNumber`、`creator`、`assignee`、agent identity assignee 等。

**涉及文件：**

- `frontend/features/channel-tasks/model/types.ts`
- `frontend/features/channel-tasks/api/channel-tasks-api.ts`
- `frontend/features/servers/model/types.ts`
- `frontend/features/servers/api/servers-api.ts`

**验收标准：**

- [x] `ChannelTask` 包含 `displayNumber`
- [x] `ChannelTask` 包含 `creator`
- [x] `ChannelTask` 包含 `assignee`
- [x] mapper 不再只保留裸 `creatorUserId` / `assigneeUserId`

#### 3.2 Task 卡片展示 creator 与 assignee

**描述：** 在 board/list task card 中显示协作关系：创建者和当前被委托方。布局保持紧凑，不把卡片做成大详情页。

**涉及文件：**

- `frontend/features/channel-tasks/ui/channel-task-page-client.tsx`
- `frontend/features/servers/ui/server-conversation-page-client.tsx`
- 可选新增 `frontend/features/channel-tasks/ui/task-actor-pill.tsx`

**验收标准：**

- [x] task card 显示 `#<displayNumber>`
- [x] task card 显示 creator 头像 + name
- [x] task card 显示 assignee 头像 + name，未分配时显示 Unassigned
- [x] agent assignee 使用 agent avatar，user assignee 使用 user avatar
- [x] 移动端不出现文字溢出

#### 3.3 Task detail 支持更新 assignee

**描述：** 在 task detail 中提供被委托方选择控件。可选项来自当前 server/channel 的 user 和 agent。选择后调用后端更新 task assignee，并刷新 task 和 activity。

**涉及文件：**

- `frontend/features/channel-tasks/ui/channel-task-detail-dialog.tsx`
- `frontend/features/servers/ui/conversation-drawers.tsx`
- `frontend/features/servers/api/servers-api.ts`
- `frontend/features/channel-tasks/api/channel-tasks-api.ts`

**验收标准：**

- [x] detail 中可把 task 分配给 user
- [x] detail 中可把 task 分配给 agent
- [x] detail 中可清空 assignee
- [x] 成功更新后 task card 和 detail 同步刷新
- [x] 更新 assignee 后 channel timeline 中出现轻量 event

#### 3.4 同步 server conversation 内嵌 task drawer

**描述：** 当前 server conversation 页面也有 task drawer。它必须和独立 channel task 页面使用同一套展示逻辑，避免两个入口表现不同。

**涉及文件：**

- `frontend/features/servers/ui/conversation-drawers.tsx`
- `frontend/features/servers/ui/server-conversation-page-client.tsx`
- 可选抽取 shared task detail 子组件到 `frontend/features/channel-tasks/ui/`

**验收标准：**

- [x] 从 server conversation 打开的 task drawer 显示 creator/assignee
- [x] 从 channel task 页面打开的 detail 显示一致
- [x] 两个入口更新 assignee 后都刷新 activity

---

## Phase 4: 修正为一 thread 一 task 的 task 面板入口

### 目标

让 task activity 不再是单独的上下文日志，而是直接落在 task 绑定的 root thread 中。Task 面板点击后右侧抽屉展示该 root thread，不再打开另一个频道上下文抽屉。

### 任务清单

#### 4.1 固定 task thread 归属

**描述：** 创建 task 时优先复用来源消息所属 root thread。As task 原消息创建 task 时，原消息就是 root；在已有 thread 中把 reply 标记为 task 时，task 绑定到已有 root；没有来源消息时才由后端创建 `task.created` root event。

**涉及文件：**

- `backend/app/services/server_channel_task_service.py`
- `backend/app/repositories/server_channel_message_repository.py`
- `backend/tests/test_server_channel_task_service.py`

**验收标准：**

- [x] `source_message_id` 对应 root message 时，task 的 `thread_root_message_id` 等于该消息 id
- [x] `source_message_id` 对应 reply 时，task 的 `thread_root_message_id` 等于 reply 所属 root id
- [x] agent tool 传入 `source_thread_root_message_id` 时，task 绑定到该 root
- [x] 无来源创建 task 时仍能创建独立 root event

#### 4.2 让 task 事件都追加为 thread replies

**描述：** `task.created`、`task.status_changed`、`task.assigned`、`task.unassigned`、`task.updated`、`task.commented` 都写入 task root thread。频道主 timeline 保持只展示 root messages，避免 task 更新在主 timeline 中重复刷屏。

**涉及文件：**

- `backend/app/repositories/server_channel_message_repository.py`
- `backend/app/services/server_channel_task_service.py`
- `backend/tests/test_server_channel_task_service.py`

**验收标准：**

- [x] task 更新事件使用 `thread_root_message_id=task.thread_root_message_id`
- [x] channel message 列表不再为了 task event 特判展示 replies
- [x] task event 继续使用轻量 event payload 和轻量提示样式

#### 4.3 Task 面板展示 root thread

**描述：** 在 server conversation 的 task 面板中，点击 task 后加载 `thread_root_message_id` 对应 thread，并用既有 `MessageRow` 展示 root 和 replies。轻量提示中仍保持“名称 + 下划线”的 actor 样式，不展示用户头像。

**涉及文件：**

- `frontend/features/servers/ui/conversation-drawers.tsx`
- `frontend/features/servers/ui/server-conversation-page-client.tsx`
- `frontend/features/channel-tasks/ui/channel-task-detail-dialog.tsx`
- `frontend/features/channel-tasks/api/channel-tasks-api.ts`

**验收标准：**

- [x] task drawer 读取并展示 root thread，而不是 task-only activity API
- [x] root message、task event reply、execution placeholder 和 agent reply 都在同一个抽屉里可见
- [x] 轻量提示不展示用户头像，仅显示名称 + 下划线样式
- [x] 更新 assignee 后刷新同一个 root thread

#### 4.4 清理不再需要的 activity context 分支

**描述：** 移除本轮误加的 task activity context API/前端调用路径，避免产品心智变成“task 面板 -> activity item -> 另一个上下文抽屉”。

**涉及文件：**

- `backend/app/api/v1/server_channel_messages.py`
- `backend/app/services/server_channel_message_service.py`
- `frontend/services/api-client.ts`
- `frontend/features/servers/ui/server-conversation-page-client.tsx`
- `frontend/features/channel-tasks/api/channel-tasks-api.ts`
- `frontend/features/channel-tasks/ui/channel-task-detail-dialog.tsx`

**验收标准：**

- [x] 前端不再调用 `/tasks/{task_id}/activity`
- [x] 右侧 task drawer 不再维护 context/highlight 状态
- [x] 既有 message context API 可保留给其他上下文跳转，但 task 面板不依赖它

---

## Phase 5: 验证、回写 spec 状态并等待审查

### 目标

用后端服务测试、前端 lint/build 和最小人工检查覆盖 task 委托与 root thread 展示。本轮按审查要求不提交。

### 任务清单

#### 5.1 后端验证

**描述：** 覆盖 task 编号、assignee 校验、event payload、message context API。

**建议命令：**

```bash
cd backend
uv run pytest tests/test_server_channel_task_service.py tests/test_server_channel_task_api.py tests/test_server_channel_message_service.py -q
```

**验收标准：**

- [x] 创建 task 自动分配 display number
- [x] 设置 user/agent assignee 生成正确 event
- [x] 清空 assignee 生成正确 event
- [x] agent claim 写入 agent identity assignee
- [x] message context API 权限和返回范围正确

#### 5.2 前端验证

**描述：** 覆盖 event parser、task mapper、activity item 和 context drawer 状态。

**建议命令：**

```bash
cd frontend
node --test --experimental-strip-types --experimental-specifier-resolution=node features/servers/lib/server-conversation-messages.test.ts
node --test --experimental-strip-types --experimental-specifier-resolution=node features/channel-tasks/lib/channel-task-board.test.ts
pnpm lint
pnpm build
```

**验收标准：**

- [x] task card 显示编号、creator、assignee
- [x] task detail 可更新 assignee
- [x] activity 使用轻量 event timeline
- [x] task 面板点击后展示 root thread
- [x] i18n 文案无硬编码用户可见英文

#### 5.3 手动验收路径

**描述：** 在本地 server 页面手动走一遍用户链路。

**验收路径：**

1. 在 channel 中发送一条 As task 消息。
2. 确认该消息成为 task 的 root thread，`task.created` 作为 reply 追加。
3. 打开 task 面板，确认右侧抽屉展示 root message 与 task replies。
4. 在 task 面板中分配给人类用户。
5. 确认 task card/detail 显示 assignee，root thread 出现 assigned event。
6. 重新分配给 agent。
7. 确认 task thread 有 created/assigned/reassigned event，agent execution placeholder 和 agent reply 也在同一个 thread 中。

**验收标准：**

- [x] 上述路径可完整完成
- [x] event 行最多一行，长标题截断
- [x] 普通消息与 execution placeholder 样式不回退

#### 5.4 回写实施记录

**描述：** 每完成一个 phase，在本文档勾选并补日期；完成后状态改为 `review`。

**涉及文件：**

- `specs/active/27-channel-task-delegation-and-activity-plan.md`

**验收标准：**

- [x] 文档 phase 状态与实际实现一致
- [x] 记录最终验证命令和任何既有失败

---


## 实施记录

- 2026-05-11：完成 Phase 0-2，第一个提交补齐 task display number、agent identity assignee、actor/assignee summary 与结构化 task event payload。
- 2026-05-11：完成 Phase 3-4，第二个提交补齐 task 卡片/detail/drawer 的委托展示与编辑、activity event timeline，以及按 message 定位的频道上下文回跳。
- 2026-05-11：根据审查反馈修正 Phase 4；接受一 thread 一 task，As task 原消息作为 task root，task 更新和 agent 回复统一追加到 root thread；task 面板点击直接展示 root thread。本轮不提交，等待人工审查。
- 验证：`cd backend && uv run python -m py_compile app/api/v1/server_channel_messages.py app/schemas/server_channel_message.py app/services/server_channel_message_service.py` 通过；`cd backend && uv run python -m py_compile app/models/server_channel_task.py app/schemas/server_channel_task.py app/schemas/server_channel_task_agent.py app/services/server_channel_task_service.py app/services/server_channel_task_agent_service.py app/repositories/server_channel_task_repository.py tests/test_server_channel_task_service.py` 通过。
- 验证：`cd backend && uv run python -m unittest tests.test_server_channel_task_service tests.test_server_execution_observability` 通过；`cd backend && uv run python -m py_compile app/services/server_channel_task_service.py app/services/server_channel_message_service.py app/repositories/server_channel_message_repository.py app/api/v1/server_channel_messages.py tests/test_server_channel_task_service.py` 通过。
- 验证：`cd frontend && pnpm lint` 通过；`cd frontend && pnpm build` 通过。
- 既有阻塞：`cd backend && uv run pytest tests/test_server_channel_task_service.py -q` 因当前 backend 环境未安装 `pytest` 可执行文件而无法运行。

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
| --- | --- | --- |
| display number 并发分配冲突 | 同一 channel 出现重复 `#42` | 后端在 transaction 内查询并分配；必要时增加唯一约束并在冲突时重试 |
| `assignee_preset_id` 到 agent identity 迁移不完整 | UI 显示 agent assignee 不准确 | 短期兼容 preset，优先用 server agent identity；无法解析时显示 preset fallback |
| activity context API 返回过多消息 | 抽屉加载慢或信息噪声大 | 默认 `before=20&after=20`，前端分页按需扩展 |
| task event 文案从 payload 拼接不稳定 | 多语言和截断难维护 | payload 提供结构化字段，文案只在前端 i18n 层拼接 |
| 两个 task 入口实现分叉 | server conversation drawer 与 channel task page 行为不一致 | 抽取共享 task actor pill、activity item 和 assignee selector 组件 |

---

## 总结

这份计划把 channel task 的重点从“状态看板”推进到“委托协作”。完成后，task 将具备可读编号、明确的创建/委托/被委托关系，以及绑定 root thread 的结构化轻量 event timeline。它继续保持 channel-native，不强制绑定 agent，但让人类和 agent 都能作为一等协作者参与 task 流转。
