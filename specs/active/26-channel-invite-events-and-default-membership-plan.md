# Channel invite events and default membership plan

## 元数据

| 字段 | 值 |
| --- | --- |
| **创建日期** | 2026-05-11 |
| **预期改动范围** | backend server/channel models / server invite accept flow / channel member and agent membership services / channel task messages / frontend server conversation rendering / i18n / migrations / tests |
| **改动类型** | feat |
| **优先级** | P1 |
| **状态** | in-progress |

## 实施阶段

- [x] Phase 0: 固定系统频道与轻量事件的产品边界（2026-05-11）
- [x] Phase 1: 后端补齐系统频道模型、迁移与默认成员关系（2026-05-11）
- [x] Phase 2: 后端把加入频道与 task 操作落成结构化 event message（2026-05-11）
- [ ] Phase 3: 前端实现轻量事件行与系统频道保护交互
- [ ] Phase 4: 验证、回写 spec 状态并整理提交

---

## 背景

### 问题陈述

当前 server/channel 协作已经具备基础模型，但邀请和频道事件的心智还不完整：

- 通过 server invite key 加入 server 时，只会写入 `server_members`，不会显式加入一个默认公共频道。虽然 `ServerChannelRepository.list_by_server_for_user()` 会把 public channel 展示给所有 server member，但这不是“自动加入频道”的成员关系，频道成员列表、加入时间和后续事件都缺失。
- personal server 会创建 `Personal` private channel，shared server 目前会创建 `general` public channel，但 `server_channels` 没有字段表达“这是系统保留频道”。`archive_channel()`、`delete_channel()`、`leave_channel()` 也没有保护这些特殊频道。
- 邀请同事或 agent 加入 channel 时，后端只创建 membership，不会在消息流里生成可见提示。用户看到的频道时间线缺少“谁加入了”的轻量反馈。
- channel task 创建当前会生成 `message_type="task"` 的根消息；agent 通过 tool 创建 task 时，`ServerChannelTaskAgentService` 用 session owner 伪造 `current_user`，最终 root message 的 `author_user_id` 仍是人类用户，看起来像“人发了一条 task 消息”。这和实际 actor 不一致。
- task 状态变更、claim、comment 已经写入 `message_type="system"`，但前端 `MessageRow` 把它们当普通消息气泡渲染。agent execution placeholder 也用 `system`，导致“执行过程卡片”和“协作事件提示”混在同一个类型里。

### 目标

本计划目标是把 channel invite 和协作事件收口成稳定的产品/技术契约：

- shared server 必须拥有一个系统 `Public` channel；personal server 必须拥有一个系统 `Personal` channel。
- `Public` 和 `Personal` 都是系统频道，不能删除、归档或离开；`Public` 是通过 invite key 加入 shared server 后默认自动加入的频道。
- 邀请/加入同事和 agent 到 channel 时，在对应频道生成一条结构化轻量 event message。
- task 创建和由 agent tool 触发的 task 操作，不再伪装成普通人类消息，而是生成结构化轻量 event message，并保留 actor 信息。
- 前端消息流新增轻量事件行：靠左一行、次要色、头像 + 名称 + 动作 + 时间，和普通聊天气泡、execution 卡片明显区分。

### 非目标

- 不引入 websocket / SSE；本轮继续复用前端轮询和现有刷新机制。
- 不重做 task board 视图，也不改变 `server_channel_tasks` 的任务字段模型。
- 不把 server invite 变成 channel-specific invite；server invite 仍然只负责加入 server，默认 channel membership 由后端派生。
- 不把 agent execution placeholder 从 `system` 全量迁移走；本轮只把协作事件从普通 system/task 气泡里分离出来。
- 不改变 direct message 的系统频道语义；DM 仍由 `conversation_type="direct_message"` 独立承载。

### 关键洞察

#### 1. public 可见不等于 public 已加入

当前 public channel 对 server member 可见，但没有 membership 时无法表达“这个人属于 Public channel”。默认 Public 频道需要显式 membership，否则成员列表、加入提示、加入时间和未来权限细化都会失真。

#### 2. 系统频道需要模型字段，而不是只靠 slug 约定

只靠 `slug in {"personal", "general"}` 判断会把数据迁移、用户重命名和未来默认频道扩展都做脆。应给 `server_channels` 增加明确的 `system_channel_type`，并由 service 层统一保护。

#### 3. 轻量事件是消息流的一等展示形态，但不是普通对话消息

事件需要出现在 channel 时间线上，参与排序、分页和 thread root 关联；但它不应该使用普通用户/agent 气泡样式，也不应该触发 mention agent。后端应通过结构化 `message_type="event"` 和 `content.event_type` 区分。

#### 4. task root message 仍可作为任务上下文锚点

把 task 创建改为 event 不代表丢掉 thread 锚点。`server_channel_tasks.thread_root_message_id` 可以继续指向 task-created event message，后续 task 状态事件仍然回复到这个 root。

---

## Phase 0: 固定系统频道与轻量事件的产品边界

### 目标

先明确本次改动的对象模型、事件类型和兼容策略，避免实现时在 `system`、`task`、`event` 之间继续混用。

### 任务清单

#### 0.1 定义系统频道类型

**描述：** 在 spec 和实现中固定以下系统频道语义：

- `system_channel_type = "personal"`：只存在于 personal server，默认 private，显示名 `Personal`，slug `personal`。
- `system_channel_type = "public"`：只存在于 shared server，默认 public，显示名 `Public`，slug `public`。
- 普通频道 `system_channel_type = null`。

**涉及文件：**

- `backend/app/models/server_channel.py` - 新增系统频道字段
- `backend/app/schemas/server_channel.py` - API response 暴露系统频道类型和保护状态
- `frontend/features/servers/model/types.ts` - 前端类型同步

**验收标准：**

- [ ] 后续实现不再通过 name/slug 猜测系统频道
- [ ] API response 能让前端知道一个 channel 是否系统频道
- [ ] shared server 的默认公共频道产品名统一为 `Public`

#### 0.2 定义 channel event message 契约

**描述：** 新增 `message_type="event"`，并通过 `content.event_type` 记录具体事件。第一批事件类型：

| event_type | 触发场景 | 核心字段 |
| --- | --- | --- |
| `channel.member_joined` | 用户通过 server invite 自动加入 Public、手动 join public channel、admin 添加用户到 channel | `actor_type`, `actor_user_id`, `actor_label`, `target_user_id`, `target_label`, `membership_id`, `join_reason` |
| `channel.agent_joined` | admin 添加 agent 到 channel | `actor_type`, `actor_user_id`, `actor_label`, `target_agent_identity_id`, `target_agent_handle`, `target_label`, `membership_id` |
| `task.created` | 用户或 agent tool 创建 channel task | `task_id`, `title`, `status`, `priority`, `actor_type`, `actor_user_id`, `actor_label`, `actor_agent_identity_id`, `actor_agent_handle`, `actor_session_id`, `assignee` |
| `task.status_changed` | 用户或 agent tool 移动 task 状态 | `task_id`, `title`, `from_status`, `to_status`, `actor_*` |
| `task.claimed` / `task.unclaimed` | 用户或 agent tool claim/unclaim task | `task_id`, `title`, `assignee`, `actor_*` |

**涉及文件：**

- `backend/app/schemas/server_channel_message.py` - 扩展 message type literal
- `backend/app/services/server_channel_message_service.py` - list/thread response 继续透传 event
- `frontend/features/servers/lib/server-conversation-messages.ts` - 新增 event 判定和文案模型
- `frontend/features/servers/ui/conversation-message-row.tsx` - 根据 display kind 分流渲染

**验收标准：**

- [ ] event message 不触发 `ServerAgentTriggerService.trigger_for_channel_message()`
- [ ] event message 能进入主消息流和 thread replies
- [ ] event message 有结构化 actor/target 字段，不依赖拼接后的 `text_preview` 做业务判断

---

## Phase 1: 后端补齐系统频道模型、迁移与默认成员关系

### 目标

让 Personal/Public 成为后端可识别、可保护、可 backfill 的系统频道，并确保通过 invite key 加入 shared server 的用户会自动加入 Public。

### 任务清单

#### 1.1 为 `server_channels` 增加 `system_channel_type`

**描述：** 新增 nullable 字段 `system_channel_type`，取值约束为 `personal / public / null`。同时增加每个 server 内系统频道类型唯一的约束。

**涉及文件：**

- `backend/app/models/server_channel.py`
- `backend/app/schemas/server_channel.py`
- `backend/alembic/versions/` - 使用 `uv run -m alembic revision --autogenerate -m "add server system channels"` 生成后人工审查

**验收标准：**

- [ ] `ServerChannelResponse` 包含 `system_channel_type`
- [ ] 同一个 server 不能存在两个 `public` 系统频道或两个 `personal` 系统频道
- [ ] 普通频道不受唯一约束影响

#### 1.2 backfill 既有 Personal/general 频道

**描述：** 迁移已有数据：

- personal server 下 slug 为 `personal` 的 channel 标记为 `system_channel_type="personal"`。
- shared server 下优先选择 slug 为 `public` 的 public channel；若不存在，则选择 slug 为 `general` 的 public channel；再不存在时选择最早创建的 public channel。将其标记为 `system_channel_type="public"`。
- 被选中的 shared 默认频道显示名统一改为 `Public`。slug 优先改为 `public`；如果已有同 server 普通频道占用 `public` slug，则保留原 slug 并在后续修复任务中提示人工处理，避免迁移失败。
- 为每个 active `server_members` 写入对应 Public channel 的 active `server_channel_members`。

**涉及文件：**

- `backend/alembic/versions/`
- `backend/app/repositories/server_channel_repository.py` - 如实现需要，补 `get_system_channel()` / `list_missing_system_channel_members()` 等查询

**验收标准：**

- [ ] 迁移后每个 personal server 至少有一个 `personal` 系统频道
- [ ] 迁移后每个 shared server 至少有一个 `public` 系统频道
- [ ] active shared server member 都有 Public channel membership
- [ ] 迁移可重复运行时不会重复创建 membership

#### 1.3 新建 server 时创建系统频道

**描述：** 更新 server 初始化逻辑：

- `ServerService.ensure_personal_server()` 创建 `Personal` channel 时写入 `system_channel_type="personal"`。
- `ServerService.create_server()` 创建 `Public` channel，而不是 `general`，并写入 `system_channel_type="public"`。
- server owner 自动拥有对应系统频道 membership。

**涉及文件：**

- `backend/app/services/server_service.py`
- `backend/tests/` - 新增或扩展 server service 测试

**验收标准：**

- [ ] 新 personal server 默认包含 protected `Personal`
- [ ] 新 shared server 默认包含 protected `Public`
- [ ] owner 创建 shared server 后已经是 Public channel member

#### 1.4 接受 server invite 时自动加入 Public

**描述：** `ServerInviteService.accept_invite()` 在创建 `ServerMember` 后，查找或确保 shared server 的 Public channel，并创建/恢复该用户的 active `ServerChannelMember`。

**涉及文件：**

- `backend/app/services/server_invite_service.py`
- `backend/app/services/server_channel_service.py` - 可抽取 `ensure_system_channel_member()`
- `backend/app/repositories/server_channel_repository.py`
- `backend/tests/` - 新增 invite accept 自动加入 Public 的服务测试

**验收标准：**

- [ ] 通过 invite key 第一次加入 shared server 后，用户自动成为 Public channel active member
- [ ] 若用户已有 left/removed membership，accept/恢复路径会重新激活 membership
- [ ] personal server 不走 Public 自动加入逻辑
- [ ] invite 的 `used_count` 仍然只在成功加入 server 后增加

#### 1.5 保护系统频道不能删除、归档或离开

**描述：** 更新 channel mutation：

- `archive_channel()` 和 `delete_channel()` 遇到 `system_channel_type != null` 返回 business error。
- `leave_channel()` 遇到系统频道返回 business error；owner 离开普通 channel 时删除频道的旧行为保持不变。
- `update_channel()` 不允许修改系统频道的 `name`、`visibility` 或 slug 派生字段；description 是否允许更新可保守禁止。

**涉及文件：**

- `backend/app/services/server_channel_service.py`
- `backend/app/api/v1/server_channels.py`
- `frontend/features/servers/ui/server-conversation-page-client.tsx` - 前端隐藏/禁用 delete/archive/leave 入口

**验收标准：**

- [ ] 后端拒绝删除/归档/离开 Personal 和 Public
- [ ] 前端不会展示误导性的删除/离开系统频道操作
- [ ] 普通 public/private channel 行为不回退

---

## Phase 2: 后端把加入频道与 task 操作落成结构化 event message

### 目标

把“谁加入了 channel”和“谁触发了 task 操作”写入同一套 event message 契约，并修复 agent tool 创建 task 时 actor 被显示成人类用户的问题。

### 任务清单

#### 2.1 新增 channel event message helper

**描述：** 在 service 层新增一个小的内部 helper，用来创建轻量事件消息。helper 只负责构造 `ServerChannelMessage`，不负责权限判断。

**建议接口：**

```python
def create_channel_event_message(
    db: Session,
    *,
    channel_id: uuid.UUID,
    event_type: str,
    actor: ChannelEventActor,
    target: ChannelEventTarget | None,
    content: dict[str, object],
    text_preview: str,
    thread_root_message_id: uuid.UUID | None = None,
) -> ServerChannelMessage:
    ...
```

**涉及文件：**

- `backend/app/services/server_channel_message_service.py` 或新增 `backend/app/services/server_channel_event_service.py`
- `backend/app/models/server_channel_message.py`
- `backend/app/schemas/server_channel_message.py`

**验收标准：**

- [ ] event message 的 `author_user_id` 默认为 `None`
- [ ] actor 信息写在 `content.actor_*`
- [ ] helper 不会触发 mention agent

#### 2.2 用户加入 channel 时生成 event

**描述：** 覆盖以下路径：

- `ServerInviteService.accept_invite()` 自动加入 Public：在 Public channel 生成 `channel.member_joined`，`join_reason="server_invite"`.
- `ServerChannelService.add_channel_member()` admin 添加用户到 channel：生成 `channel.member_joined`，actor 为当前 admin，target 为被添加用户。
- `ServerChannelService.join_channel()` 用户手动 join public channel：生成 `channel.member_joined`，actor 和 target 都是当前用户，`join_reason="self_join"`.

**涉及文件：**

- `backend/app/services/server_invite_service.py`
- `backend/app/services/server_channel_service.py`
- `backend/app/services/user_public_profile_service.py`
- `backend/tests/`

**验收标准：**

- [ ] 新 membership 创建或从非 active 恢复为 active 时才生成 joined event
- [ ] 已经 active 的重复添加不重复生成 event
- [ ] event content 同时包含 actor 与 target，前端可渲染头像和名字

#### 2.3 agent 加入 channel 时生成 event

**描述：** `AgentIdentityService.add_agent_to_channel()` 创建或恢复 `ServerChannelAgentMember` 时生成 `channel.agent_joined`。

**涉及文件：**

- `backend/app/services/agent_identity_service.py`
- `backend/app/repositories/server_channel_agent_member_repository.py`
- `backend/tests/test_agent_identity_service.py`

**验收标准：**

- [ ] 新 agent membership 创建时生成 joined event
- [ ] removed/left agent membership 恢复为 active 时生成 joined event
- [ ] 已经 active 的重复添加不重复生成 event
- [ ] event content 包含 `target_agent_identity_id`、`target_agent_handle`、`target_label`

#### 2.4 task root message 改为 event，并保留 task thread 锚点

**描述：** `ServerChannelTaskService._create_task_root_message()` 从 `message_type="task"` 改为 `message_type="event"`，`content.event_type="task.created"`。当 actor 是 agent 时，`author_user_id` 不再使用 session owner；actor 信息只写入 content。

**涉及文件：**

- `backend/app/services/server_channel_task_service.py`
- `backend/app/services/server_channel_task_agent_service.py`
- `backend/app/schemas/server_channel_message.py`
- `backend/tests/` - 覆盖用户创建 task 和 agent tool 创建 task 两条路径

**验收标准：**

- [ ] 用户创建 task 的消息显示为 task.created event
- [ ] agent tool 创建 task 的消息显示为 task.created event，actor_type 为 `agent`
- [ ] `server_channel_tasks.thread_root_message_id` 仍指向这条 event root message
- [ ] task root event 不触发 agent mention

#### 2.5 task 状态/claim 事件迁移到 event

**描述：** `ServerChannelTaskService._create_system_message()` 改为创建 `message_type="event"`，用于 `task.status_changed`、`task.claimed`、`task.unclaimed`。`task.commented` 是否仍显示为轻量事件，需要按内容区分：纯状态评论保持 event；若未来要支持正文评论，可另开普通 thread reply。

**涉及文件：**

- `backend/app/services/server_channel_task_service.py`
- `backend/tests/`

**验收标准：**

- [ ] task 状态变化不再显示为普通 system 气泡
- [ ] agent tool 更新 task 状态时 actor 是 agent
- [ ] event reply 仍挂在 task root message 的 thread 下

---

## Phase 3: 前端实现轻量事件行与系统频道保护交互

### 目标

让用户在 channel timeline 中清楚地区分聊天消息、agent execution 卡片和协作事件提示。

### 任务清单

#### 3.1 扩展前端类型与 API mapper

**描述：** 同步后端字段：

- `ServerChannelItem.systemChannelType?: "personal" | "public" | null`
- `ServerConversationMessage.messageType` 增加 `"event"`
- 新增 `ServerChannelEventContent` 类型或 helper，用于安全读取 `content.event_type`、actor、target 和 task 字段

**涉及文件：**

- `frontend/features/servers/model/types.ts`
- `frontend/features/servers/api/servers-api.ts`
- `frontend/features/servers/lib/server-conversation-messages.ts`
- `frontend/features/servers/lib/server-conversation-messages.test.ts`

**验收标准：**

- [ ] TypeScript 不再把 event 当成 `system | task` 的例外分支
- [ ] mapper 正确读取 `system_channel_type`
- [ ] 单测覆盖 event type 判定和 fallback 文案

#### 3.2 新增 `ChannelEventRow`

**描述：** 在 `conversation-message-row.tsx` 中拆出轻量事件行，或新增独立组件：

- 左对齐单行或最多两行
- 使用 `text-muted-foreground` / `bg-muted/20` 等 design token，不硬编码颜色
- 显示 avatar + actor/target name + action phrase + time
- 用户头像复用 `Avatar`
- agent 头像复用 `ServerAgentAvatar`
- 不显示 copy / reply / save / reaction 操作
- task created event 可点击打开 task detail 或 thread；第一版如没有稳定入口，可只保留静态行

**涉及文件：**

- `frontend/features/servers/ui/conversation-message-row.tsx`
- 可选新增 `frontend/features/servers/ui/channel-event-row.tsx`
- `frontend/features/servers/lib/server-message-text.ts`
- `frontend/lib/i18n/locales/*/translation.json`

**验收标准：**

- [ ] `channel.member_joined` 渲染为 “Alice joined Public · 14:32” 类轻量行
- [ ] `channel.agent_joined` 渲染为 agent 头像 + agent display name
- [ ] `task.created` 渲染为 “Alex created task: Fix parser” 或 “Agent created task: ...”
- [ ] 长名称和长 task title 不撑破布局，移动端能截断或换行
- [ ] 普通 user message 和 agent execution 卡片样式不回退

#### 3.3 系统频道操作保护 UI

**描述：** 前端根据 `systemChannelType` 隐藏或禁用危险操作：

- `Personal` / `Public` 不展示 delete/archive/leave 操作。
- channel list 或 header 给系统频道稳定图标/排序；`Personal` 和 `Public` 应优先显示在普通频道前。
- 创建 channel 对话框不允许创建同名系统频道造成混淆；后端仍以唯一约束兜底。

**涉及文件：**

- `frontend/features/servers/ui/server-conversation-page-client.tsx`
- `frontend/features/servers/ui/server-workspace-sidebar.tsx`
- `frontend/features/servers/lib/server-conversation-view.ts`
- `frontend/lib/i18n/locales/*/translation.json`

**验收标准：**

- [ ] 系统频道不会出现删除/归档/离开入口
- [ ] Public 在 shared server 的频道列表中稳定靠前
- [ ] Personal 在 personal server 中稳定靠前
- [ ] 普通频道仍能按现有逻辑管理

#### 3.4 统一 event 文案 i18n

**描述：** 所有轻量事件文案走 i18n，不在组件中硬编码英文/中文。

**建议 key：**

- `conversationView.events.channelMemberJoined`
- `conversationView.events.channelAgentJoined`
- `conversationView.events.taskCreated`
- `conversationView.events.taskStatusChanged`
- `conversationView.events.taskClaimed`
- `conversationView.events.taskUnclaimed`
- `conversationView.events.unknown`

**涉及文件：**

- `frontend/lib/i18n/locales/en/translation.json`
- `frontend/lib/i18n/locales/zh/translation.json`
- 其他已有 locale 文件同步补 key

**验收标准：**

- [ ] `pnpm lint` 不出现 missing translation 或硬编码可见文案问题
- [ ] fallback event 使用统一 unknown 文案

---

## Phase 4: 验证、回写 spec 状态并整理提交

### 目标

用后端服务测试、前端单测和最小构建验证覆盖本次行为变更。

### 任务清单

#### 4.1 后端验证

**描述：** 按影响面新增或更新测试，至少覆盖：

- server 创建时系统频道字段
- invite accept 自动加入 Public
- 系统频道不能删除/归档/离开
- 添加用户/agent 到 channel 生成 event
- 用户/agent 创建 task 生成 `message_type="event"`

**建议命令：**

```bash
cd backend
uv run pytest tests/test_server_invite_service.py tests/test_server_channel_service.py tests/test_agent_identity_service.py tests/test_server_channel_task_service.py -q
```

**验收标准：**

- [ ] 相关后端测试通过
- [ ] 变更的 Python 文件通过 `uv run python -m py_compile ...`

#### 4.2 前端验证

**描述：** 覆盖 mapper、event helper 和渲染分支。

**建议命令：**

```bash
cd frontend
node --test --experimental-strip-types --experimental-specifier-resolution=node features/servers/lib/server-conversation-messages.test.ts
pnpm lint
pnpm build
```

**验收标准：**

- [ ] event helper 单测通过
- [ ] lint/build 通过
- [ ] 手动检查 channel timeline 中 user message、execution message、event row 三种样式区分明显

#### 4.3 回写实施记录

**描述：** 每完成一个 phase，在本文档“实施阶段”勾选并补日期；实现完成进入 review 状态。

**涉及文件：**

- `specs/active/26-channel-invite-events-and-default-membership-plan.md`

**验收标准：**

- [ ] spec 状态更新到 `review`
- [ ] 实施记录说明已跑过哪些验证以及是否存在既有失败

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
| --- | --- | --- |
| 迁移重命名 `general` 到 `Public/public` 时遇到 slug 冲突 | Alembic 迁移失败或频道链接变化 | 只强制设置 `system_channel_type` 和 display name；slug 冲突时保留原 slug 并记录人工 follow-up |
| 把 task root 从 `task` 改成 `event` 影响旧前端类型 | 消息流渲染或 thread 打开失败 | 后端 schema、前端 mapper 和 `MessageRow` 同步修改；保留 `thread_root_message_id` 关系 |
| event message 被误当 user message 触发 agent mention | 加入/任务事件导致 agent 意外运行 | `ServerChannelMessageService.send_message()` 只对 `message_type="user"` 触发；内部 helper 不调用 send_message |
| 系统频道保护只做前端不做后端 | 用户可通过 API 删除 Public/Personal | service 层必须先拒绝，前端只做体验优化 |
| agent tool 创建 task 仍带 session owner `author_user_id` | UI 继续误显示成人类消息 | event helper 默认 `author_user_id=None`，actor 全部走 content 中的 `actor_type`/`actor_*` |

---

## 总结

本计划把 Public/Personal 从“默认创建的普通频道”提升为系统频道，并把 invite、channel membership 和 task 操作统一收敛到结构化 event message。实现后，频道时间线会有三种清晰形态：普通聊天消息、agent execution 卡片、轻量协作事件行；通过 invite key 加入 server 的同事也会真正成为 Public channel 成员，而不是只“看得到 public channel”。
