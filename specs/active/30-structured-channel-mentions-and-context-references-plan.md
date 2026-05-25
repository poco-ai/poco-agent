# Structured channel mentions and context references plan

## 元数据

| 字段 | 值 |
| --- | --- |
| **创建日期** | 2026-05-25 |
| **预期改动范围** | backend channel message schema / message validation / agent trigger service / trigger envelope references / channel artifact and task candidate APIs / frontend server conversation composer / message rendering / hover cards / i18n / tests |
| **改动类型** | feat |
| **优先级** | P1 |
| **状态** | completed |
| **关联 constitution** | `specs/constitution/2026-05-25-structured-channel-mentions-and-context-references.md` |
| **关联 research** | `specs/research/2026-05-25-structured-mention-and-channel-context-research.md` |

## 实施阶段

- [x] Phase 0: 固定当前实现边界与实体契约
- [x] Phase 1: 后端支持 message entities 与 scope 校验
- [x] Phase 2: Agent 触发改为 entity-first 并传播引用
- [x] Phase 3: 提供 `#` 上下文引用候选 API
- [x] Phase 4: 前端 composer 改造为 `@` / `#` 双 picker
- [x] Phase 5: 消息渲染、hover card 与旧消息兼容
- [x] Phase 6: 验证、回归与 spec 回写

---

## 背景

### 问题陈述

频道聊天当前的 mention 协议仍然主要依赖文本扫描。前端检测 `@token` 后把文本插入 textarea；后端再扫描 `@handle` 来触发 agent；消息渲染层也只根据 regex 高亮 `@token`。这个模型已经无法支持频道共享文件引用，也无法为后续 task/thread/reference/command 扩展提供稳定边界。

现在用户已经可以上传频道共享文件，但在聊天中很难自然地把某个文件传给 agent。用户希望表达的是：“触发 `@reviewer`，并让它参考 `#design.md`”。这需要把执行者路由和上下文引用拆开，而不是继续把所有语义压进同一个 `@` 文本扫描。

### 目标

本计划目标是把频道输入和触发链路升级为结构化协议：

- `@` 只用于 agent / human 等参与者。
- `#` 用于 artifact/file、task、thread/message 等上下文引用。
- 消息发送 payload 支持 `content.entities`。
- 后端保存前校验并规范化 entities。
- agent trigger 只从 structured agent entity 收集目标，regex 仅兼容旧消息。
- artifact/task/message references 被写入 `AgentTriggerEnvelope.references`。
- 前端消息渲染与 hover card 基于 entities，而不是只扫文本。

### 非目标

- 不在本轮引入完整富文本编辑器；第一版可以继续使用 textarea + `draftEntities`。
- 不在本轮新增 `server_channel_message_entities` 独立表；先使用 `server_channel_messages.content.entities`。
- 不改变 agent-to-agent collaboration tool 的显式触发原则。
- 不把 `#` 设计成执行命令入口；命令入口继续预留给 `/`。
- 不把频道 artifacts 映射成容器本地路径；agent 仍通过 channel runtime tools 读取。

### 关键洞察

#### 1. 前缀是交互入口，不是后端协议

`@` 和 `#` 只负责帮助用户在输入框里找到目标。发送后真正可靠的是 entity 的 `kind`、`action`、`target_id` 和后端校验结果。

#### 2. Agent trigger 和 artifact reference 是不同副作用

Agent trigger 会创建执行任务；artifact reference 只是把文件 id 传给运行上下文。二者不能共享同一条 regex 路由。

#### 3. JSON content 足以支撑第一阶段

当前 `server_channel_messages.content` 已经是 JSON payload。第一阶段可以在 content 内新增 `entities`，先完成协议、路由、渲染和测试；后续通知/审计/搜索需要增强时再拆独立表。

#### 4. 文件候选需要 flat search，不应依赖树 UI

公共成果树适合浏览和预览，但 `#` picker 需要快速搜索并拿到稳定 `artifact_id`。后端需要提供 picker 友好的 flat candidates API。

#### 5. Artifact 读取必须以稳定 id 为主

`#` 在输入框中插入的是人类可读 token，例如 `#design.md`；真正可读、可校验、可审计的运行时标识是 `artifact_id`。`display_name` 只用于展示和搜索，不是读取 id；`logical_path` 只有在来自 artifact API 返回的完整值时才能作为备选读取参数。

---

## Phase 0: 固定当前实现边界与实体契约

### 目标

在动代码前确认当前 mention、message content、artifact、task、trigger envelope 的真实接口，避免实施时和现有半成品冲突。

### 任务清单

#### 0.1 对齐当前 mention 和发送链路

**描述：** 梳理并记录当前 `@` 输入、消息发送、后端触发、消息渲染的入口，确认哪些逻辑要迁移、哪些保留为旧消息 fallback。

**涉及文件：**

- `frontend/features/servers/lib/server-conversation-view.ts` - 当前 mention candidate、trigger regex、insert text helper
- `frontend/features/servers/ui/server-conversation-page-client.tsx` - 主频道 composer 和上传附件逻辑
- `frontend/features/servers/ui/conversation-drawers.tsx` - thread drawer composer 的重复 mention 逻辑
- `frontend/features/servers/api/servers-api.ts` - `sendMessage()` payload
- `frontend/features/servers/ui/server-message-content.tsx` - 当前 regex mention 渲染
- `backend/app/services/server_agent_trigger_service.py` - 当前 `@handle` regex trigger

**验收标准：**

- [ ] 明确新消息和旧消息的分界：有 `content.entities` 的消息走 entity-first，无 entities 的旧消息走 regex fallback
- [ ] 明确主 composer 和 thread drawer composer 需要共享同一套 candidate/entity helper
- [ ] 明确 agent insert text 必须使用 handle，不再优先插入 display label

#### 0.2 固定 `ChannelMessageEntity` 契约

**描述：** 在 spec 和类型草稿中固定第一阶段 entity kind/action/字段名，避免前后端命名漂移。

**建议契约：**

```ts
type ChannelMessageEntityKind =
  | "agent"
  | "user"
  | "artifact"
  | "task"
  | "message"
  | "thread";

type ChannelMessageEntityAction =
  | "trigger"
  | "mention"
  | "reference";

type ChannelMessageEntity = {
  id: string;
  kind: ChannelMessageEntityKind;
  action: ChannelMessageEntityAction;
  targetId: string;
  displayText: string;
  insertedText: string;
  range?: { start: number; end: number };
  metadata?: Record<string, unknown>;
};
```

**涉及文件：**

- `frontend/features/servers/model/types.ts`
- `backend/app/schemas/server_channel_message.py`

**验收标准：**

- [ ] 前端使用 camelCase，后端 schema 支持 API alias 并规范化为 snake_case 或统一 JSON 输出策略
- [ ] `agent/trigger`、`user/mention`、`artifact/reference`、`task/reference` 的合法组合明确
- [ ] 非法组合会被后端拒绝或清洗，不会静默参与路由

---

## Phase 1: 后端支持 message entities 与 scope 校验

### 目标

让 channel message create path 接受、校验、规范化并持久化 `content.entities`，为后续触发和渲染提供事实源。

### 任务清单

#### 1.1 增加 message entity schemas

**描述：** 在 schema 层定义 message entity 的 Pydantic models，并让 create request 能解析 `content.entities`。第一阶段仍把完整 content 存为 JSON，不新增独立表。

**涉及文件：**

- `backend/app/schemas/server_channel_message.py` - 新增 `ServerChannelMessageEntity`、`ServerChannelMessageEntityRange`、metadata schema 或受控 dict
- `backend/app/models/server_channel_message.py` - 确认 content JSON 字段无需迁移
- `backend/tests/test_server_channel_message_api.py`
- `backend/tests/test_server_channel_message_service.py`

**验收标准：**

- [ ] API 接受 `content.entities` 数组
- [ ] response 原样返回后端规范化后的 `content.entities`
- [ ] 无 entities 的旧 payload 继续可发送
- [ ] 字段 alias 覆盖前端 camelCase 输入

#### 1.2 实现 entity validation / canonicalization

**描述：** 保存消息前按 channel scope 校验 entity target。后端应补齐 canonical display metadata，并移除前端伪造或不可信字段。

**涉及文件：**

- `backend/app/services/server_channel_message_service.py` - 保存前调用 entity 校验
- `backend/app/repositories/server_channel_agent_member_repository.py` - 校验 agent 是当前频道 active member
- `backend/app/repositories/server_channel_member_repository.py` 或现有 member repository - 校验 human user 可见性
- `backend/app/repositories/channel_artifact_repository.py` - 校验 artifact 属于当前 channel
- `backend/app/repositories/server_channel_task_repository.py` - 校验 task 属于当前 channel
- `backend/app/repositories/server_channel_message_repository.py` - 校验 message/thread 属于当前 channel
- `backend/tests/test_server_channel_message_service.py`

**验收标准：**

- [ ] `agent/trigger` 只能指向当前 channel active agent
- [ ] `user/mention` 只能指向当前 server/channel 可见用户
- [ ] `artifact/reference` 只能指向当前 channel artifact
- [ ] `task/reference` 只能指向当前 channel task
- [ ] `message/reference` 或 `thread/reference` 只能指向当前 channel message/thread
- [ ] 非法或越权 entity 返回 400，不静默降级为普通文本

#### 1.3 保留发送正文和附件兼容

**描述：** 保持 `content.text`、`content.attachments`、`content.as_task` 的既有行为。附件上传本身不自动等价于 `artifact/reference`，只有用户通过 `#` 选择或 UI 明确加入上下文时才生成 reference entity。

**涉及文件：**

- `backend/app/services/server_channel_message_service.py`
- `backend/tests/test_server_channel_message_service.py`

**验收标准：**

- [ ] 上传文件后发送普通消息仍保留附件展示
- [ ] 没有 reference entity 的附件不会自动进入 trigger envelope artifact refs
- [ ] 旧的 as task 创建行为不被 entities 改造破坏

---

## Phase 2: Agent 触发改为 entity-first 并传播引用

### 目标

让 agent trigger 和 trigger envelope references 消费结构化 entities，彻底区分 agent 触发与文件/task/thread 引用。本阶段的关键不是“从消息里多拿几个 id”，而是固定 `content.entities` 到 `AgentTriggerEnvelope` 的投影契约：message entity 记录用户在消息中选择的对象，trigger envelope 记录 agent run 可依赖的目标 agent 和引用 id。

### 任务清单

#### 2.0 固定 entity -> trigger envelope 投影契约

**描述：** 在后端实现前先明确每类 entity 如何投影到 trigger envelope，避免 `targetId` 只停留在前端渲染或 message content 层。

**投影规则：**

- `agent/trigger` -> `target_agent_identity_id`、`target_agent_handle`
- `artifact/reference` -> `references.artifact_ids`
- `task/reference` -> `references.task_ids`
- `message/reference` -> `references.message_ids`
- `thread/reference` -> `references.message_ids` 中的 thread root message id
- `user/mention` -> 不进入 trigger envelope，仅服务渲染、profile 和未来通知

**涉及文件：**

- `backend/app/schemas/server_channel_message.py` - entity schema 和合法组合
- `backend/app/schemas/agent_trigger.py` - trigger envelope references
- `backend/app/services/server_agent_trigger_service.py` - entity 到 envelope 的投影入口
- `backend/app/services/channel_shared_context_service.py` - envelope 构造和去重
- `backend/tests/test_agent_trigger_envelope_schema.py`
- `backend/tests/test_server_agent_trigger_service.py`

**验收标准：**

- [ ] 每类 entity 的 envelope 投影有单元测试
- [ ] `displayText`、`insertedText`、handle、logical path 不作为 envelope 事实源
- [ ] 后端只在 scope 校验通过后把 target id 写入 envelope
- [ ] user mention 不会污染 agent trigger references

#### 2.1 改造 target agent 收集逻辑

**描述：** `ServerAgentTriggerService._collect_target_agents()` 优先读取 `content.entities` 中的 `agent/trigger`。只有消息没有 entities 时才走旧 `@handle` regex。

**涉及文件：**

- `backend/app/services/server_agent_trigger_service.py`
- `backend/tests/test_server_agent_trigger_service.py`

**验收标准：**

- [ ] 有 `agent/trigger` entity 时触发指定 agent
- [ ] 有 entities 且文本中额外出现 `@other-agent` 时，不触发额外 agent
- [ ] 文本中 `@some-file` 不会触发 agent
- [ ] 无 entities 的旧消息仍能用 `@handle` 触发 agent
- [ ] Direct message channel 继续使用 `direct_agent_identity_id`，不依赖正文 mention

#### 2.2 从 entities 收集 trigger references

**描述：** 把 `artifact/reference`、`task/reference`、`message/thread reference` 收集进 trigger envelope。当前触发消息 id 仍必须始终进入 `references.message_ids`。这一步是把用户在频道消息中通过 `#` 选择的上下文对象投影到 agent runtime，而不是简单把 token 文本传给 prompt。

**涉及文件：**

- `backend/app/services/server_agent_trigger_service.py`
- `backend/app/services/channel_shared_context_service.py`
- `backend/app/schemas/agent_trigger.py`
- `backend/tests/test_channel_shared_context_service.py`
- `backend/tests/test_agent_trigger_envelope_schema.py`
- `backend/tests/test_server_agent_trigger_service.py`

**验收标准：**

- [ ] `artifact/reference` entity 进入 `TriggerReferences.artifact_ids`
- [ ] `task/reference` entity 进入 `TriggerReferences.task_ids`
- [ ] `message/thread reference` entity 进入 `TriggerReferences.message_ids`
- [ ] 当前触发消息 id 不会因额外 references 被覆盖
- [ ] 重复引用会去重并保持稳定顺序
- [ ] envelope 中的 id 均来自 canonicalized entity target，而不是从 `insertedText` 反解析

#### 2.3 确认 executor prompt 与 runtime tools 消费 refs

**描述：** 检查 executor 当前对 `reference_artifact_ids`、`reference_task_ids`、`reference_message_ids` 的提示和 tool contract，必要时补充 prompt wording，确保 agent 知道被引用文件应通过 channel tools 读取。对 artifact 来说，`reference_artifact_ids` 中的值就是 `read_channel_artifact` 的 `artifact_id`；agent 不应把 `#displayName` 或正文里的文件名当作读取标识。

**涉及文件：**

- `executor/app/core/engine.py`
- `executor/app/core/channel_runtime.py`
- `executor_manager/app/api/v1/agent_channel_artifacts.py`
- `backend/app/services/channel_runtime_service.py`
- `backend/tests/test_channel_runtime_service.py`
- `backend/tests/test_internal_channel_runtime_api.py`
- `executor/tests/test_channel_runtime_tools.py`
- `executor_manager/tests/test_agent_channel_artifacts_api.py`

**验收标准：**

- [ ] trigger context 中的 artifact refs 能被 agent prompt 看见
- [ ] prompt 不暗示 artifact 是 `/workspace` 本地路径
- [ ] agent 可继续通过 `read_channel_artifact(artifact_id=...)` 读取引用文件
- [ ] `logical_path` 只能使用 artifact 工具返回的完整值，不能使用 display name 或 composer token
- [ ] Executor Manager 转发 artifact runtime API 时保留 Backend 的 4xx/5xx 语义和错误正文，不把 `Channel artifact not found` 这类业务错误包装成通用 500
- [ ] executor tool 输出使用 Backend `message` 作为结构化错误文本，便于 agent 判断是参数错误、未找到还是服务不可用

---

## Phase 3: 提供 `#` 上下文引用候选 API

### 目标

为前端 `#` picker 提供稳定候选来源。第一阶段至少支持当前频道 artifacts 和 tasks；thread/message 可以先留接口设计或轻量实现。

### 任务清单

#### 3.1 增加 artifact flat search/list API

**描述：** 为 channel artifacts 增加 picker 友好的 flat candidate API，返回 artifact id 和展示元数据。不要让 picker 解析公共成果树节点来猜 id。

**建议接口：**

```text
GET /api/v1/servers/{server_id}/channels/{channel_id}/artifacts/candidates?q=&limit=
```

**涉及文件：**

- `backend/app/schemas/channel_artifact.py` - 新增 picker candidate response
- `backend/app/services/channel_artifact_service.py` - 新增 search/list candidates
- `backend/app/api/v1/server_channel_artifacts.py` - 新增 endpoint
- `backend/tests/test_channel_artifact_service.py`
- `backend/tests/test_server_channel_artifact_api.py`

**验收标准：**

- [ ] candidate 包含 `artifact_id`、`display_name`、`logical_path`、`mime_type`、`size_bytes`、`source_kind`、publisher summary、created_at
- [ ] `q` 可按文件名和 logical path 搜索
- [ ] 返回结果只包含当前 channel 可见 artifacts
- [ ] 同名文件能通过 logical path/source 展示区分
- [ ] picker 选择 artifact 后 entity 的 `targetId` 使用 `artifact_id`；`display_name` 只进入 `insertedText` / 展示 metadata

#### 3.2 增加 task candidates API 或复用现有 task list

**描述：** 为 `#task` 候选提供可搜索 task summary。优先复用现有 channel task API；如果现有 list 不适合 picker，新增轻量 candidates endpoint。

**涉及文件：**

- `backend/app/schemas/server_channel_task.py`
- `backend/app/services/server_channel_task_service.py`
- `backend/app/api/v1/server_channel_tasks.py` 或现有 task API 文件
- `backend/tests/test_server_channel_task_service.py`
- `backend/tests/test_server_channel_task_api.py`

**验收标准：**

- [ ] candidate 包含 `task_id`、`display_number`、`title`、`status`、assignee summary
- [ ] 搜索可以匹配 task number 和 title
- [ ] `#task-42` 或等价展示格式与现有 task 编号语义一致

#### 3.3 确认 FileNode 是否需要补 artifact id

**描述：** 公共成果树 UI 仍使用 `FileNode[]`。如果文件树里的某个文件也要能一键“引用到输入框”，叶子节点需要携带 artifact id；否则引用入口只来自 flat candidates API。

**涉及文件：**

- `backend/app/schemas/workspace.py`
- `backend/app/services/channel_artifact_service.py`
- `frontend/features/chat/types/api/file.ts`
- `frontend/features/servers/ui/shared-artifacts-drawer.tsx`

**验收标准：**

- [ ] 决定第一阶段是否扩展 `FileNode`，并在代码中保持一致
- [ ] 即使不扩展 `FileNode`，`#` picker 也能通过 flat API 引用已有 artifacts

---

## Phase 4: 前端 composer 改造为 `@` / `#` 双 picker

### 目标

把频道主 composer 和 thread drawer composer 从纯文本 mention 改成 `draftText + draftEntities`，并引入 `@` 与 `#` 分工。

### 任务清单

#### 4.1 抽取通用 picker detection 与 candidate model

**描述：** 将当前 `MentionCandidate` 扩展为通用 candidate，并支持检测当前输入的是 `@` 还是 `#`。尽量把主 composer 和 drawer 共享的逻辑放到 lib/model 层，减少重复。

**涉及文件：**

- `frontend/features/servers/lib/server-conversation-view.ts`
- `frontend/features/servers/model/types.ts`
- `frontend/features/servers/lib/server-conversation-view.test.ts`（如新增）

**验收标准：**

- [ ] `@` trigger 只返回 agent/user candidates
- [ ] `#` trigger 返回 artifact/task candidates
- [ ] 候选项包含 `kind`、`action`、`targetId`、`label`、`insertedText`、metadata
- [ ] agent candidate 插入文本稳定使用 handle

#### 4.2 扩展 servers API 类型与调用

**描述：** 前端 `sendMessage()` 支持发送 `content.entities`。新增 artifact/task candidates API client。

**涉及文件：**

- `frontend/features/servers/api/servers-api.ts`
- `frontend/features/servers/model/types.ts`
- `frontend/features/chat/types/api/file.ts`（如扩展 FileNode）

**验收标准：**

- [ ] `sendMessage()` 支持传入 entities
- [ ] artifact candidates API 可被 composer 调用
- [ ] task candidates API 或现有 task list 可被 composer 调用
- [ ] TypeScript 类型不使用 `any` 承接 entities

#### 4.3 主频道 composer 维护 draft entities

**描述：** 在主频道输入框中新增 `draftEntities` 状态。选择 `@` 或 `#` 候选项时同时更新文本和 entity；发送前过滤 stale entity。

**涉及文件：**

- `frontend/features/servers/ui/server-conversation-page-client.tsx`
- `frontend/lib/i18n/locales/en/translation.json`
- `frontend/lib/i18n/locales/zh/translation.json`

**验收标准：**

- [ ] 选择 agent 后 payload 包含 `agent/trigger`
- [ ] 选择 human 后 payload 包含 `user/mention`
- [ ] 选择 artifact 后 payload 包含 `artifact/reference`，且 `targetId` 是 `artifact_id`
- [ ] 选择 task 后 payload 包含 `task/reference`
- [ ] 删除 token 后不会发送 stale entity
- [ ] 发送成功后清空 text、attachments 和 entities

#### 4.4 Thread drawer composer 复用同一套逻辑

**描述：** thread reply drawer 当前有一套复制的 mention candidate 逻辑。需要迁移为共享 helper，避免主频道和 thread 回复行为不一致。

**涉及文件：**

- `frontend/features/servers/ui/conversation-drawers.tsx`
- `frontend/features/servers/lib/server-conversation-view.ts`

**验收标准：**

- [ ] thread drawer 支持 `@` participant picker
- [ ] thread drawer 支持 `#` context picker
- [ ] thread reply 发送 payload 同样带 entities
- [ ] 现有 thread target agent 继承提示不被破坏

#### 4.5 上传附件与 `#` 引用联动

**描述：** 上传到草稿的频道文件已经返回 `InputFile.id`。如果用户在上传后从 `#` picker 选择该文件，应生成 `artifact/reference` entity；但单纯作为附件发送不自动生成 reference。

**涉及文件：**

- `frontend/features/servers/ui/server-conversation-page-client.tsx`
- `frontend/features/servers/lib/server-conversation-view.ts`

**验收标准：**

- [ ] 上传文件后能在 `#` candidates 中找到该文件
- [ ] 选择上传文件后 entity 的 `targetId` 使用 returned `InputFile.id`
- [ ] 只上传不选择时，仍按现有附件展示，不进入 `references.artifact_ids`

---

## Phase 5: 消息渲染、hover card 与旧消息兼容

### 目标

让消息内容展示从 regex mention 高亮升级为 entity-driven 渲染，并为 agent/user/artifact/task 提供 hover 信息。

### 任务清单

#### 5.1 Entity-driven message content renderer

**描述：** `server-message-content.tsx` 优先读取 `content.entities` 渲染 chip。旧消息无 entities 时保留当前 regex mention fallback。

**涉及文件：**

- `frontend/features/servers/ui/server-message-content.tsx`
- `frontend/features/servers/model/types.ts`
- `frontend/features/servers/lib/server-message-text.ts`（如抽取文本/实体渲染 helper）

**验收标准：**

- [ ] 有 entities 的消息按 entity kind/action 渲染
- [ ] 无 entities 的旧消息仍保留弱高亮
- [ ] 未解析或无权限 entity 显示 fallback 文本和弱提示
- [ ] 普通 `@token` / `#token` 不会被渲染成强交互对象

#### 5.2 Agent/user hover card

**描述：** hover 到 agent/user mention 或头像时展示轻量资料卡。点击行为保持当前 agent 详情跳转；human 点击可以保持现状或进入用户资料入口。

**涉及文件：**

- `frontend/features/servers/ui/conversation-message-row.tsx`
- `frontend/features/servers/ui/server-agent-avatar.tsx`
- `frontend/features/servers/ui/server-message-content.tsx`
- `frontend/features/servers/ui/server-agent-detail-dialog.tsx`
- `frontend/lib/i18n/locales/en/translation.json`
- `frontend/lib/i18n/locales/zh/translation.json`

**验收标准：**

- [ ] agent hover card 展示 display name、handle、description、joined/created time、runtime status
- [ ] human hover card 展示 display name、user id 或 role、joined time
- [ ] hover 不影响点击进入 agent detail 的现有行为
- [ ] 移动端或无 hover 环境下不阻塞点击主流程

#### 5.3 Artifact/task hover card 与跳转

**描述：** hover 到 `#artifact` / `#task` 时展示上下文摘要；点击进入已有 preview / task drawer。

**涉及文件：**

- `frontend/features/servers/ui/server-message-content.tsx`
- `frontend/features/servers/ui/shared-artifacts-drawer.tsx`
- `frontend/features/servers/ui/server-conversation-page-client.tsx`
- `frontend/features/servers/ui/channel-tasks-workspace.tsx`
- `frontend/lib/i18n/locales/en/translation.json`
- `frontend/lib/i18n/locales/zh/translation.json`

**验收标准：**

- [ ] artifact hover card 展示 name、logical path、mime type、size、publisher、created time
- [ ] artifact click 打开预览或下载入口
- [ ] task hover card 展示 `#number`、title、status、assignee
- [ ] task click 打开对应 task drawer 或详情面板

---

## Phase 6: 验证、回归与 spec 回写

### 目标

完成后端、前端、手动交互和文档状态验证，确保结构化 mention 不破坏现有频道工作流。

### 任务清单

#### 6.1 后端测试

**描述：** 覆盖 entities 校验、agent trigger、references 传播、旧 regex fallback 和越权拒绝。

**建议命令：**

```bash
cd backend
uv run pytest tests/test_server_channel_message_service.py \
  tests/test_server_channel_message_api.py \
  tests/test_server_agent_trigger_service.py \
  tests/test_channel_shared_context_service.py \
  tests/test_channel_artifact_service.py \
  tests/test_server_channel_artifact_api.py
```

**验收标准：**

- [ ] 新增/更新测试全部通过
- [ ] `@some-file` 不会触发 agent
- [ ] `agent/trigger` entity 能触发 agent
- [ ] `artifact/reference` 进入 trigger envelope artifact ids
- [ ] 旧 `@handle` 无 entities 消息仍兼容触发

#### 6.2 前端类型、lint 和单元测试

**描述：** 覆盖 picker helper、entity stale 过滤、API 类型和 message renderer。

**建议命令：**

```bash
cd frontend
pnpm lint
pnpm build
```

如果新增 Vitest 测试，按项目现有 test 命令补充执行。

**验收标准：**

- [ ] TypeScript 编译通过
- [ ] lint 通过
- [ ] picker/helper 单元测试覆盖 `@` 与 `#`
- [ ] renderer 测试覆盖 entity 渲染和旧消息 fallback

#### 6.3 手动交互验证

**描述：** 在本地 dev 环境验证关键频道流程。

**验收标准：**

- [ ] `@agent` 触发 agent，消息 payload 带 `agent/trigger`
- [ ] `@human` 只生成 mention，不触发 agent
- [ ] `#uploaded-file` 引用文件并进入 trigger envelope
- [ ] 被引用文件可通过 trigger context 中的 `reference_artifact_ids` 直接用 `read_channel_artifact(artifact_id=...)` 读取
- [ ] 用 display name 或不完整 logical path 读取 artifact 时返回清晰的 not found/invalid 参数错误，不出现 Executor Manager 包装出的 500
- [ ] 仅输入普通 `@text` 或 `#text` 不产生强实体
- [ ] agent/user/artifact/task hover card 显示基本信息
- [ ] 点击 agent mention 仍进入 agent detail
- [ ] 点击 artifact reference 能打开预览或下载

#### 6.4 文档回写与状态更新

**描述：** 实施完成后回写本 spec 的 phase checkbox 和状态；如发现 constitution 需要修正，在历史变更中追加记录。

**涉及文件：**

- `specs/active/30-structured-channel-mentions-and-context-references-plan.md`
- `specs/constitution/2026-05-25-structured-channel-mentions-and-context-references.md`

**验收标准：**

- [ ] 已完成 phase 标记为 `[x]`
- [ ] 文档中的实际文件路径与实现保持一致
- [ ] 若方案发生变化，constitution 有历史变更记录

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
| --- | --- | --- |
| textarea 中维护 range 容易失效 | 可能触发用户已经删除的对象 | 第一版发送前校验 `insertedText` 和 range，无法匹配就丢弃 entity 或提示重选 |
| `#` 与 task 编号展示冲突 | 用户不清楚 `#42` 是 task 还是普通文本 | task 引用统一展示为 `#task-42` 或带 task icon/chip，候选菜单中明确分组 |
| 新 entity schema 与旧消息兼容冲突 | 旧频道消息触发行为被破坏 | 只有无 entities 的消息走 regex fallback；测试覆盖旧 `@handle` |
| Artifact tree 没有 artifact id | 前端无法引用已有共享文件 | 增加 flat candidates API；是否扩展 FileNode 单独决策 |
| Agent 把 display name 当 artifact 读取 id | 同名/路径不完整时读取失败，甚至被代理层误包装为 500 | Prompt 明确优先 `artifact_id`；Manager 透传 Backend 错误；测试覆盖 not found 语义 |
| 后端静默忽略非法 entity | 用户以为触发或引用成功但实际没有 | 非法/越权 entity 返回 400，前端展示明确错误 |
| 多 agent 触发带来误解 | 用户不知道一条消息会触发多个 agent | picker 和发送前状态可显示多个 agent chips；后端按 entities 精确触发 |

---

## 总结

本计划把频道 mention 从“文本扫描”升级为“结构化实体协议”。`@` 负责参与者，`#` 负责上下文；前端用 picker 生成 entities，后端校验并据此触发 agent 或传播 artifact/task references。这样既能解决共享文件在聊天中难以引用的问题，也为后续 thread、message、command、通知和 hover profile 留出稳定扩展点。
