# Server agent status consistency plan

## 元数据

| 字段 | 值 |
| --- | --- |
| **创建日期** | 2026-05-17 |
| **预期改动范围** | frontend server workspace / agent runtime status model / backend persistent runtime reconciliation / channel task assignment semantics / preset deletion validation / targeted tests |
| **改动类型** | fix |
| **优先级** | P1 |
| **状态** | draft |
| **关联 issue** | `poco-ai/poco-claw#114 Display status inconsistency` |

## 实施阶段

- [ ] Phase 0: 固定问题边界与统一状态词典
- [ ] Phase 1: 收敛 agent runtime 单一状态源
- [ ] Phase 2: 增加 stale runtime / stale executor 回收机制
- [ ] Phase 3: 对齐 task 分配、执行与 UI 状态语义
- [ ] Phase 4: 收敛 inbox、页面导航与 preset 删除反馈
- [ ] Phase 5: 验证、灰度检查与 spec 回写

---

## 背景

`issue #114` 表面上是“显示状态不一致”，但结合截图、评论和当前代码，实际暴露的是一组跨前后端的状态模型断裂：

- 同一个 agent 在不同 UI 面板中使用不同状态判定逻辑。
- task 的“分配”“开始执行”“进行中”没有被清晰区分，导致用户看到待开始卡片、系统事件和 agent 详情互相打架。
- executor / persistent agent 的忙闲状态只依赖 callback 终态释放，一旦 callback 缺失、session 残留或 placeholder 没回收，就会长期卡在 busy。
- inbox 未读数完全由前端本地 `readMessageIds` 和启发式 `hasInboxSignal()` 计算，缺少稳定的服务端语义。
- preset 删除失败只有通用 400，没有把“被谁占用、为什么删不了”反馈到 UI。

当前代码已经能解释 issue 中的大部分现象：

- `frontend/features/servers/lib/agent-runtime-status.ts` 用派生逻辑把 `runtime_status + active_session_id + active_task_id` 折叠成前端标签。
- `frontend/features/servers/ui/server-agent-detail-dialog.tsx` 却直接显示原始 `persistentState.runtimeStatus`，没有复用同一派生结果。
- `frontend/features/servers/ui/server-workspace-sidebar.tsx` 的 server 下拉仅调用 `setSelectedServerId`，没有复用 `switchServer()` 的 URL 同步路径，容易让旧 `channelId` 和新 server 脱钩。
- `frontend/features/servers/ui/server-conversation-page-client.tsx` 里的 `activeChannelIdByAgentId` 依赖“当前已加载消息里的 session id -> channel id 映射”，不是稳定后端字段。
- 当前 route 走的是 `frontend/features/servers/ui/channel-tasks-workspace.tsx`，但旧的 `frontend/features/channel-tasks/ui/channel-task-page-client.tsx` 仍保留另一套 task 状态编辑/拖拽语义，前端实际上有两套 task surface。
- `backend/app/services/agent_runtime_service.py` 只有在 callback 收到 `completed/failed/canceled` 时才释放 runtime；没有补偿式 reconciliation。
- `backend/app/services/agent_assignment_service.py` 在切换 preset / trigger mode 时先覆写 assignment 字段，再做比较，旧 `session_id` / `container_id` 的清理分支实际上很容易失效。
- `backend/app/services/server_channel_task_service.py` 中 `claim_task()` 只更新 assignee，不改变 task status，也不会创建“执行已启动”的单独语义。
- `backend/app/services/server_channel_task_service.py` 允许 `assignee_preset_id` 进入 claim/update 流程，但 `_validate_task_assignee()` 并不校验 preset 是否仍可见或可用。
- `backend/app/services/preset_service.py` 的 `delete_preset()` 只校验 project default usage，没有把 server agent / channel agent / assignment 等依赖暴露给前端。

因此这次修复不能只改某一个 badge 文案，而是要把“状态从哪里来、什么时刻迁移、哪些页面消费同一个语义”全部固定下来。

## 目标

本计划要把 server / channel 协作中的几套状态重新收敛成一套可解释、可回收、可复用的模型：

- 为 persistent agent 建立唯一的 runtime summary，并保证同事列表、详情面板、任务面板、执行抽屉消费同一个状态派生结果。
- 为 stale session / stale executor / callback 丢失场景增加后端 reconciliation，让 busy 状态不会永久残留。
- 明确区分 task 的 assignment state、workflow status、execution activity，避免“分配后立即显示运行中”的心智混乱。
- 让 inbox count、搜索/服务器菜单切换和 loading 状态更稳定，不再依赖脆弱的本地推断。
- 让 preset 删除失败能返回结构化占用原因，而不是单纯 400。

## 非目标

- 不把 channel task 改成自动跟随 executor run 的强绑定对象；task 仍然可以已分配但未开始执行。
- 不在本轮引入 websocket / SSE；继续基于轮询和现有 API 收敛状态。
- 不重做整个 server workspace 导航布局。
- 不处理多 executor_manager 的部署拓扑和本地路径映射策略；这单独作为运维/架构议题记录。
- 不在本轮删除 `assignee_preset_id` 兼容字段。

## 关键洞察

### 1. “原始 runtime_status” 不是可直接展示给用户的最终状态

后端 `runtime_status` 只是持久状态文件上的一个低层字段；用户真正关心的是：

- 这个 agent 现在是否可接新活
- 它是不是被残留 session 卡住了
- 它当前忙是因为活跃执行，还是因为坏状态没有清掉

因此 UI 不应一处显示派生状态、一处显示原始值，而应有统一的 `runtime summary`。

### 2. task 分配和 task 执行是两个不同状态机

`claim_task()` 当前只意味着“谁负责”，不意味着“开始运行”。issue 里“分配就去运行中？”正是因为产品没有把这两个概念拆开。修复方向不应是偷偷让 claim 自动推进到 `in_progress`，而是把 assignment / workflow / execution 三者明确呈现出来。

### 3. stale busy 比“显示错字”更严重，因为它会污染调度和认知

一旦 `active_session_id` 没释放，前端同事列表、详情、回跳 channel、甚至后续 trigger 行为都会被误导。这个问题必须在后端补偿，而不能只在前端忽略掉。

### 4. inbox 不能只靠浏览器本地状态推断

当前 inbox count 完全由 `localStorage` 的 `readMessageIds` 决定，切换菜单、切换设备、进入 server 页面都会出现不一致。短期不一定要做全服务端未读系统，但至少要把当前 feed signal 和 read marking 规则收敛。

---

## Phase 0: 固定问题边界与统一状态词典

### 目标

先把当前实现中的几套“状态”逐一命名，明确每个字段的语义和消费者，避免实现时继续混用。

### 任务清单

#### 0.1 列出当前状态来源与消费者矩阵

**描述：** 以 spec 表格形式整理以下字段和页面：

- `AgentPersistentState.runtime_status`
- `AgentPersistentState.active_session_id`
- `AgentPersistentState.active_task_id`
- channel task `status`
- task assignee 字段
- execution placeholder `content.execution_status`
- inbox `readMessageIds`

**涉及文件：**

- `frontend/features/servers/lib/agent-runtime-status.ts`
- `frontend/features/servers/ui/server-agent-detail-dialog.tsx`
- `frontend/features/servers/ui/server-conversation-page-client.tsx`
- `backend/app/services/agent_runtime_service.py`
- `backend/app/services/server_channel_task_service.py`
- `backend/app/repositories/server_channel_message_repository.py`

**验收标准：**

- [ ] 每个状态字段有明确“来源 / 更新时机 / 消费页面 / 是否直接展示”
- [ ] 明确哪些字段是原始状态，哪些字段是派生状态

#### 0.2 固定前端展示词典

**描述：** 明确用户可见的 agent runtime 标签仅保留以下集合：

- `idle`
- `busy`
- `failed`
- `stopped`
- `removed`
- `unknown`
- `stale`（仅当后端或前端检测到残留执行态时）

**验收标准：**

- [ ] 所有 agent 相关 UI 只显示同一套文案 key
- [ ] 原始 `runtime_status` 不再直接裸露给最终用户

---

## Phase 1: 收敛 agent runtime 单一状态源

### 目标

让同事列表、agent 详情、回跳 channel、执行抽屉共享同一派生结果，而不是各自推断。

### 任务清单

#### 1.1 引入前端统一 runtime summary mapper

**描述：** 把 `getAgentRuntimeStatus()` 扩展为完整 summary helper，输出：

- normalized status key
- tone
- active session id
- active task id
- active channel id（若可确定）
- stale hint（若 runtime 和执行占位信息冲突）

**涉及文件：**

- `frontend/features/servers/lib/agent-runtime-status.ts`
- `frontend/features/servers/model/types.ts`

**验收标准：**

- [ ] helper 输出结构化 summary，而不是只输出 labelKey/tone
- [ ] detail dialog 与 colleagues panel 都消费同一 helper

#### 1.2 用统一 summary 改造 agent 详情弹窗

**描述：** `server-agent-detail-dialog.tsx` 不能再直接显示 `persistentState.runtimeStatus`。顶部 badge、详情卡片、active task / active session 信息要同时展示“用户可见状态”和“调试字段”。

**涉及文件：**

- `frontend/features/servers/ui/server-agent-detail-dialog.tsx`
- `frontend/lib/i18n/locales/*/translation.json`

**验收标准：**

- [ ] 同一个 agent 在列表和详情里的主状态标签一致
- [ ] 原始 runtime 字段仅作为 secondary debug 信息出现

#### 1.3 稳定 active channel 回跳来源

**描述：** `activeChannelIdByAgentId` 不能只依赖当前内存里的 `sessionId -> channelId` 映射。需要优先消费后端返回的稳定字段；若后端暂时没有，至少补一层 placeholder / recent execution message 回填策略。

**涉及文件：**

- `frontend/features/servers/ui/server-conversation-page-client.tsx`
- `frontend/features/servers/api/servers-api.ts`
- `backend/app/schemas/agent_identity.py`
- `backend/app/services/agent_identity_service.py`

**验收标准：**

- [ ] agent 处于 busy 时，若后台已知 active channel，前端可稳定回跳
- [ ] 不再因为当前页面没加载某个 channel 的消息而丢失回跳入口

---

## Phase 2: 增加 stale runtime / stale executor 回收机制

### 目标

解决“确认没有任务在执行，但 executor 还显示卡死 / agent 仍是运行中”的残留状态问题。

### 任务清单

#### 2.1 提炼 runtime reconciliation 规则

**描述：** 对 persistent agent 增加后端 reconciliation 逻辑。若 `active_session_id` 指向的 session 已终态、run 不存在、queue item 全部终态，或 placeholder 全部终态，则把 runtime 从 `busy` 释放为 `idle` / `failed`。

**涉及文件：**

- `backend/app/services/agent_runtime_service.py`
- `backend/app/services/session_service.py`
- `backend/app/services/callback_service.py`
- `backend/app/repositories/session_repository.py`
- `backend/app/repositories/run_repository.py`
- `backend/app/repositories/session_queue_item_repository.py`

**验收标准：**

- [ ] callback 正常到达时仍走现有快速释放路径
- [ ] callback 缺失时，reconciliation 也能在后续读请求或轮询中清理残留状态

#### 2.2 在 agent list/get 读取路径上做被动修复

**描述：** `AgentIdentityService.list_agents()` / `get_agent()` 在返回前，对 persistent state 执行一次轻量 reconciliation，避免用户只能通过重启 agent 才恢复状态。

**涉及文件：**

- `backend/app/services/agent_identity_service.py`
- `backend/app/repositories/agent_identity_repository.py`
- `backend/tests/test_agent_runtime_service.py`
- `backend/tests/test_agent_identity_service.py`

**验收标准：**

- [ ] stale busy agent 打开 server 页面即可被纠正
- [ ] reconciliation 不会错误打断真实运行中的 session

#### 2.3 定义 stale 状态的前端降级展示

**描述：** 如果前端发现 summary 与后端原始字段仍短暂冲突，优先展示 `stale` / “syncing” 风格，而不是一处 active 一处 idle。

**涉及文件：**

- `frontend/features/servers/lib/agent-runtime-status.ts`
- `frontend/features/servers/ui/colleagues-panel.tsx`

**验收标准：**

- [ ] 冲突窗口期内 UI 以单一状态展示
- [ ] 用户能理解“正在回收/同步”，而不是看到矛盾结果

#### 2.4 修正 assignment 切 preset / mode 时的旧 session 残留

**描述：** `AgentAssignmentService.sync_issue_assignment()` 需要在更新 `preset_id` / `trigger_mode` 前保留旧值并比较，确保配置切换时能正确清空旧 `session_id`、`container_id`、`last_triggered_at`。

**涉及文件：**

- `backend/app/services/agent_assignment_service.py`
- `backend/tests/test_agent_assignment_service.py`

**验收标准：**

- [ ] 切换 preset 或 trigger mode 后，不会继续绑定旧 session/container
- [ ] 旧 assignment runtime 不会以新配置名义继续显示为活跃

---

## Phase 3: 对齐 task 分配、执行与 UI 状态语义

### 目标

把 issue 中“分配就去运行中？”和“待开始卡片 + 执行事件”混乱拆开。

### 任务清单

#### 3.1 固定 task 三层状态模型

**描述：** 文档和 UI 都明确区分：

- **assignee**：谁负责
- **workflow status**：`todo / in_progress / in_review / done`
- **execution activity**：是否存在活跃 agent execution placeholder / active session

**涉及文件：**

- `backend/app/services/server_channel_task_service.py`
- `frontend/features/channel-tasks/model/types.ts`
- `frontend/features/channel-tasks/ui/channel-task-detail-dialog.tsx`
- `frontend/features/channel-tasks/ui/channel-task-page-client.tsx`

**验收标准：**

- [ ] claim / unclaim 不自动改 workflow status
- [ ] 详情面板里能同时看到 assignee 和 execution activity

#### 3.2 为 task 提供 execution summary 或关联 session

**描述：** 若某个 task 当前正由 persistent agent 执行，需要让前端从结构化字段得知“这个 task 对应一个 active session”，而不是从消息流间接猜。

**涉及文件：**

- `backend/app/schemas/server_channel_task.py`
- `backend/app/services/server_channel_task_service.py`
- `backend/app/services/server_agent_trigger_service.py`
- `frontend/features/channel-tasks/api/channel-tasks-api.ts`
- `frontend/features/channel-tasks/model/types.ts`

**验收标准：**

- [ ] task 卡片或详情可显示“assigned but not running”与“assigned and executing”的区别
- [ ] 任务面板不再把“已分配”误解为“进行中”

#### 3.3 收敛 task 事件文案

**描述：** task event 文案需要明确是 `assigned`, `unassigned`, `status_changed`, `execution started`, `execution failed`, `execution completed` 中的哪一种，避免用户把 channel event 看成 workflow 列状态。

**涉及文件：**

- `backend/app/services/server_channel_task_service.py`
- `backend/app/services/callback_service.py`
- `frontend/features/servers/ui/conversation-message-row.tsx`
- `frontend/lib/i18n/locales/*/translation.json`

**验收标准：**

- [ ] “分配给 tttt” 不会在视觉上被解释成“任务已经运行”
- [ ] 运行相关事件只能来自 execution path，不由 claim path 冒充

#### 3.4 补齐 preset assignee 合法性校验

**描述：** 若本轮继续保留 `assignee_preset_id` 兼容路径，就必须显式校验 preset 是否存在、当前用户是否可见、是否允许作为当前 server/channel 的 task assignee；否则应拒绝写入，而不是让 UI 留下“找不到 preset”的悬挂状态。

**涉及文件：**

- `backend/app/services/server_channel_task_service.py`
- `backend/app/repositories/preset_repository.py`
- `backend/tests/test_server_channel_task_service.py`

**验收标准：**

- [ ] task claim/update 不能写入软删除或不可见 preset
- [ ] assignee summary 不再因为非法 preset 引用而退化为残缺展示

---

## Phase 4: 收敛 inbox、页面导航与 preset 删除反馈

### 目标

覆盖 issue 中剩余但仍与“状态一致性”强相关的几个表象问题。

### 任务清单

#### 4.1 重新定义 inbox signal 与 unread count

**描述：** 当前 `hasInboxSignal()` 过于宽松，只要 `replyCount > 0` 就进 inbox，且未读完全依赖本地 `readMessageIds`。本轮要至少做到：

- 统一 server/channel/search/inbox 之间的 read marking 规则
- 排除当前用户自己发出的普通 user message
- 为 event / execution placeholder 定义是否进入 inbox 的明确规则

**涉及文件：**

- `frontend/features/servers/lib/server-conversation-view.ts`
- `frontend/features/servers/ui/server-conversation-page-client.tsx`
- `frontend/features/servers/ui/conversation-panels.tsx`

**验收标准：**

- [ ] 左侧 inbox count 与 inbox 面板内 unread/all 统计一致
- [ ] 切换菜单后不会出现明显的 0 / 非 0 矛盾

#### 4.2 修复菜单切换时的错误 loading 态残留

**描述：** 从其他菜单进入 server 页面时，`mode`, `selectedChannel`, `drawer`, `isMobileDetailVisible` 和 thread load 的切换次序要收敛，避免长期显示“正在加载会话”。此外，server 下拉切换必须复用 URL-aware 的 `switchServer()` 路径，不能只改本地 state。

**涉及文件：**

- `frontend/features/servers/ui/server-conversation-page-client.tsx`
- `frontend/features/servers/ui/conversation-drawers.tsx`
- `frontend/features/servers/ui/server-workspace-sidebar.tsx`

**验收标准：**

- [ ] 从 search/tasks/colleagues/inbox 切回 server conversation 不会卡在 loading title
- [ ] drawer 切换不会保留上一状态的 root message
- [ ] server 下拉切换后不会保留上一个 server 的 `channelId` 路由参数

#### 4.3 收敛 task surface，只保留一套 server route 语义

**描述：** 当前 route 实际使用 `channel-tasks-workspace.tsx`，但旧的 `channel-task-page-client.tsx` 仍保留另一套拖拽和详情逻辑。本轮需要明确哪一套是 canonical surface，并把另一套改为复用或下线，避免未来继续引入双重状态模型。

**涉及文件：**

- `frontend/features/servers/ui/channel-tasks-workspace.tsx`
- `frontend/features/channel-tasks/ui/channel-task-page-client.tsx`
- `frontend/features/channel-tasks/index.ts`
- `frontend/features/servers/ui/server-workspace-types.ts`

**验收标准：**

- [ ] 服务器路由只存在一套 task 状态变更和详情交互语义
- [ ] 不再出现一套 UI 可以改 status、另一套 UI 只能改 assignee 的分裂行为

#### 4.4 为 preset 删除返回结构化占用原因

**描述：** `delete_preset()` 需要补依赖检查，并把失败原因结构化返回，例如：

- used as project default
- referenced by live server agent
- referenced by pending assignment / scheduled task

前端删除提示要能展示“为什么删不了”，而不是只有“删除失败”。

**涉及文件：**

- `backend/app/services/preset_service.py`
- `backend/app/repositories/preset_repository.py`
- `backend/app/schemas/preset.py`
- `backend/tests/test_preset_services.py`
- `backend/tests/test_agent_assignment_service.py`
- `frontend/features/capabilities/presets/api/presets-api.ts`
- `frontend/features/capabilities/presets/components/presets-page-client.tsx`

**验收标准：**

- [ ] 后端返回结构化 dependency reason
- [ ] 前端 toast / dialog 能说明具体阻塞项

---

## Phase 5: 验证、灰度检查与 spec 回写

### 目标

在不引入 websocket 的前提下，用针对性测试和手动回归保证状态收敛。

### 任务清单

#### 5.1 后端单元测试

**涉及文件：**

- `backend/tests/test_agent_runtime_service.py`
- `backend/tests/test_agent_identity_service.py`
- `backend/tests/test_server_channel_task_service.py`
- `backend/tests/test_preset_services.py`

**验收标准：**

- [ ] busy -> idle/failed/stale reconciliation 有测试
- [ ] task assignment 与 execution summary 解耦有测试
- [ ] preset deletion dependency reason 有测试

#### 5.2 前端单元测试

**涉及文件：**

- `frontend/features/servers/lib/agent-runtime-status.test.ts`
- `frontend/features/servers/lib/server-conversation-view.test.ts`
- `frontend/features/channel-tasks/lib/*.test.ts`

**验收标准：**

- [ ] 同一输入在列表/详情得到同一主状态
- [ ] inbox signal / unread count 规则稳定
- [ ] task assigned vs executing 的渲染规则稳定

#### 5.3 手动回归脚本

**场景：**

1. 创建 server agent，确认列表与详情都显示 idle
2. 在 channel 中 mention agent，确认状态变为 busy，并可回跳到正确 channel
3. 人工取消 / 失败 / callback 缺失模拟，确认 stale busy 被自动释放
4. 创建并分配 task，确认仍停留在 `todo`，但 assignee 已更新
5. 让 agent 真正执行 task，确认 execution activity 出现且不与 task column 混淆
6. 切换到 inbox / search / servers 菜单，确认 unread count 与页面内容一致
7. 删除被占用 preset，确认 UI 给出明确依赖原因

---

## 风险与权衡

- **读取时 reconciliation 会增加少量查询开销。**
  这是可接受的，因为当前最严重的问题是 stale busy 污染整个协作心智。可以先做轻量判断，再按需下钻 run / queue 状态。

- **task execution summary 若直接从消息流推导，仍会脆弱。**
  因此本 spec 倾向于在 task response 中返回结构化字段，而不是继续让前端用 event 或 placeholder 猜。

- **inbox 若继续保留完全本地未读模型，多端一致性仍有限。**
  本轮只要求前端规则内部一致，不把它升级成全服务端未读系统。

## 并行实施建议

为后续 `fix/issue-114-status-consistency` 分支上的并行开发，建议拆成三路：

- **Worker A: backend runtime reconciliation**
  负责 `agent_runtime_service.py`、`agent_identity_service.py`、callback / session 释放链路及相关测试。

- **Worker B: frontend runtime and inbox consistency**
  负责 `frontend/features/servers/*` 的 runtime summary、sidebar inbox count、menu/loading 状态与测试。

- **Worker C: task semantics and preset deletion feedback**
  负责 task execution summary、event 文案、preset dependency 校验与前端错误提示。

三路的写集基本可分离，最后只在 i18n 文案与类型定义上做小规模整合。

## 决策结论

这次 issue 的本质不是单个显示 bug，而是 persistent agent、channel task、execution placeholder、inbox feed 四套状态系统没有共享同一个语义层。修复策略应当是：

1. 先定义统一状态词典；
2. 再让后端补 runtime 回收；
3. 然后让前端所有 surface 复用同一个 summary；
4. 最后把 task / inbox / preset 删除这些边缘症状收束到同一模型里。
