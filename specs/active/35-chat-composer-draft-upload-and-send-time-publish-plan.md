# 聊天 Composer 草稿上传与发送确认发布计划

## 元数据

| 字段 | 值 |
| --- | --- |
| **创建日期** | 2026-06-13 |
| **预期改动范围** | frontend ordinary chat composer / frontend server conversation composer + thread drawer / chat and server message rendering / draft upload API usage / ordinary task enqueue payload / server channel message create path / channel artifact publish flow / tests |
| **改动类型** | feat |
| **优先级** | P1 |
| **状态** | review |
| **关联 spec** | `specs/active/30-structured-channel-mentions-and-context-references-plan.md`, `specs/active/34-ordinary-chat-input-file-reference-plan.md` |

## 实施阶段

- [ ] Phase 0: 固定当前两条链路差异与统一原则
- [ ] Phase 1: 定义聊天草稿上传契约与前端状态模型
- [ ] Phase 2: 普通聊天 composer 改为 token-first 草稿确认
- [ ] Phase 3: 频道聊天 composer 改为发送时发布
- [ ] Phase 4: 后端 finalize / publish / canonicalize 链路落地
- [ ] Phase 5: 验证、回归与文档回写

---

## 背景

### 问题陈述

当前普通聊天和频道聊天的文件上传语义不一致：

- 普通聊天在用户选择/粘贴文件时会立即上传到私有存储，但只有发送消息并进入 run 后，这些文件才会成为本轮 `input_files`，后续由 executor manager staging 到 `/workspace/inputs/...`。
- 频道聊天在用户选择/粘贴文件时会直接调用 `/artifacts/upload`，立即创建已发布的 channel artifact，逻辑路径落在 `/uploads/...`，并额外产生 `artifact.uploaded` 事件消息。

这会带来三个实际问题：

1. 用户在频道聊天里只是临时粘贴了一张图片，尚未发送消息就已经发布了 artifact；如果随后删除图片或放弃发送，频道里仍然会留下共享文件和事件噪音。
2. “粘贴图片自动插入 `#filename.png`” 只在普通聊天链路上容易成立；频道侧如果继续即时发布，`#` token 和最终 artifact 的确认时点会分裂。
3. 当前频道 composer 的“上传草稿文件”实现实际上更接近“立即发布共享文件”，而不是“当前消息的附件草稿”，这与普通聊天的草稿心智不一致。

本计划要统一的不是“什么时候开始传文件字节”，而是**什么时候确认文件进入最终域**。物理上传可以提前完成，但语义上的发布/纳入执行上下文必须以“发送消息”为确认点。

### 目标

- 普通聊天与频道聊天 composer 都支持选择文件或粘贴图片后立即做临时上传。
- 用户在输入框中通过快捷键（如 `Cmd+V` / `Ctrl+V`）粘贴图片时，会自动触发上传。
- 文件上传按钮入口继续复用现有文件上传链路。
- 对于 composer 内上传的文件，自动在光标处插入人类可读的 `#filename` token。
- 只有用户最终发送消息时，仍然保留在正文中的 `#filename` 所对应文件才会被确认纳入最终域。
- 普通聊天中，被确认的文件进入该条消息关联的 run 语义，并在执行时 staging 到 `/workspace/inputs/...`。
- 频道聊天中，被确认的文件在发送消息时才真正发布为 channel artifact，逻辑路径落在 `/uploads/...`。
- 发送前删除 token 或删除附件 pill，会取消该文件的最终发布/执行纳入。
- 主频道 composer 与 thread drawer composer 使用同一套草稿上传和 token 规则。

### 非目标

- 不把普通聊天改造成真正的多模态消息协议；图片仍然是文件引用，不直接作为 `image_url` / image block 注入模型消息。
- 不改动独立文件面板、显式“上传共享文件”按钮或非 composer 入口的发布语义；这些入口仍可保留即时发布。
- 不在本轮引入完整富文本编辑器；继续使用 textarea + 草稿状态。
- 不支持未发送草稿跨刷新、跨设备恢复。
- 不在本轮把 local mount 文件纳入同一套自动 `#` 上传引用流程。
- 不回填或迁移历史消息的数据结构。

### 关键洞察

#### 1. 物理上传可以提前，语义发布必须延后

为了避免发送时卡顿、失败时丢失文件、或浏览器内存持有大 Blob，文件字节仍然可以在粘贴/选择后立刻传到后端临时存储。但这个对象在发送前只是 draft upload，不属于 `inputs/`，也不属于 `/uploads/`。

#### 2. `#token` 是 inclusion contract，不是纯展示文案

对 composer 上传文件而言，正文里保留的 `#filename` 不只是 UX 装饰，而是“这份草稿文件应当随本消息一起提交”的显式确认。发送前如果 token 被删掉，该文件就不应进入最终域。

#### 3. 最终 materialization 目标按聊天域区分

- 普通聊天：发送时确认进入该条任务请求，最终执行侧暴露在 `/workspace/inputs/...`
- 频道聊天：发送时确认发布为 channel artifact，最终逻辑路径暴露在 `/uploads/...`

临时上传对象不应提前占用这两个目录语义。

#### 4. composer 来源的频道文件不应再额外制造独立上传事件噪音

如果文件是通过“发送一条消息”发布出来的，那么用户消息本身就是主要审计记录。继续额外生成独立 `artifact.uploaded` 事件，会放大噪音并打断对话流。显式文件面板上传仍可保留原事件行为，但 composer confirm-on-send 链路不应再复制这一事件。

#### 5. 自动插 token 不能只覆盖图片粘贴

如果系统定义“只有正文里保留的 `#token` 才确认发布”，那么 composer 内通过选择文件上传的普通文件也必须自动插入 token。否则同一个 composer 会同时存在“需要 token 确认”的图片和“没有 token 的文件”，心智会分裂。

#### 6. 图片自动上传只绑定输入框 paste 快捷键路径，文件选择继续复用现有上传入口

本计划里的“粘贴图片自动上传”特指用户在聊天输入框内通过系统粘贴快捷键（如 `Cmd+V` / `Ctrl+V`）把 clipboard 中的图片粘贴进来时，系统识别到图片文件对象并走自动上传。另一条入口不是额外定义新的 paste 变体，而是继续复用当前文件上传按钮链路。两条入口最终都收敛到同一套 draft upload 与 `#token` 确认逻辑。

---

## 统一生命周期契约

### 术语

- **draft upload**：用户在 composer 中选择文件或粘贴图片后生成的临时上传对象，仅对当前用户可见，尚未进入最终域。
- **draft attachment pill**：composer 下方展示的文件卡片，用于表示这份 draft upload 当前仍处于待提交状态。
- **confirmation token**：正文中自动插入的 `#filename` 文本，表示该 draft upload 会随消息一起确认提交。
- **materialize**：发送消息时把 draft upload 转化为最终域对象。普通聊天转为 run input；频道聊天转为 published artifact。

### 统一原则

1. 所有聊天 composer 内上传的文件，先落到临时上传存储。
2. 上传成功后，UI 立即展示 attachment pill，并在光标处插入 `#filename`。
3. 前端发送前先过滤 stale token；后端发送时再次校验，只有正文仍包含 `#filename` 的 draft upload 才会被 materialize。
4. 如果用户删除 token 或删除 pill，则该 draft upload 不会随消息确认提交。
5. 如果消息发送失败，draft upload 保持未发布状态，用户可继续重试或删除。

### 临时上传对象

第一版不要求前端知道临时上传对象的真实存储目录。它只是一个私有 draft handle，最小字段可沿用 `InputFile` 形态：

```ts
type DraftUploadHandle = {
  id: string;
  type: "file";
  name: string;
  source: string;
  size?: number | null;
  content_type?: string | null;
  path?: string | null;
};
```

约束：

- `source` 是临时对象的后端事实源，不是最终 `inputs/` 路径，也不是 `/uploads/...` 逻辑路径。
- `name` 是 draft display name；若同一草稿中重名，前端应在插 token 前先做草稿内去重，保持 token 唯一。
- `path` 在 draft 阶段可以为空；最终路径由 materialization 阶段决定。
- 频道 composer 的草稿上传应复用普通聊天的私有临时上传入口，或在后端抽出共享 draft upload API；它不应继续直接调用 `/servers/{serverId}/channels/{channelId}/artifacts/upload`。

### 普通聊天 finalization

普通聊天发送时：

1. 仅保留正文中仍存在 `#token` 的 draft upload。
2. 这些对象进入 `TaskConfig.input_files` / `file_references` 语义。
3. 它们在真正 dispatch 到 executor 时由现有 attachment staging 落到 `/workspace/inputs/...`。
4. 发送前删除的文件不进入 run，也不会出现在消息后续渲染附件中。

### 频道聊天 finalization

频道聊天发送时：

1. 仅保留正文中仍存在 `#token` 的 draft upload。
2. 后端在创建用户消息的同一条业务链路里，把这些对象发布成 channel artifact。
3. artifact 逻辑路径使用现有 `/uploads/<display_name>` 规则与去重策略。
4. 持久化后的消息 `content.attachments` 存放的是已发布 artifact 对应的 canonical `InputFile` 形态；`content.entities` 存放 canonical `artifact/reference` entity。
5. composer confirm-on-send 这条链路不额外生成独立 `artifact.uploaded` 事件消息。

---

## 方案比较

### 方案 A：保持频道即时发布，只给图片补自动 `#token`

优点：

- 改动最小。
- 复用当前 `/artifacts/upload`。

缺点：

- 发送前删除图片仍会留下已发布 artifact。
- `#token` 与真实发布时点不一致。
- 频道和普通聊天的草稿心智继续分裂。

结论：不采用。

### 方案 B：发送时才真正上传文件字节

优点：

- 最严格的“未发送即不存在”语义。

缺点：

- 发送时延迟、失败面和大文件风险明显更高。
- 无法复用当前上传成功后的附件预览与重复选择体验。

结论：不采用。

### 方案 C：临时上传 + 发送时 materialize

优点：

- 满足“发送才确认发布”的产品语义。
- 保留提前上传带来的性能与容错优势。
- 能统一普通聊天与频道聊天的 composer 心智。

缺点：

- 需要新增 draft upload finalization 逻辑。
- 频道消息创建链路会比当前多一层 canonicalization。

结论：采用。

---

## Phase 0: 固定当前两条链路差异与统一原则

### 任务

- 记录普通聊天当前“立即上传、发送后纳入 run”的真实链路。
- 记录频道聊天当前“立即发布 artifact”的真实链路。
- 固定 composer 文件上传的新总原则：`early upload, late publish`。
- 固定“只有正文里保留的 `#token` 才确认提交”这一不变量。

### 验收

- spec 中明确区分“临时上传对象”和“最终域对象”。
- 不再把普通聊天的临时对象误认为已经在 `inputs/`。
- 不再把频道 composer 上传误认为普通消息附件草稿。

## Phase 1: 定义聊天草稿上传契约与前端状态模型

### 任务

- 为普通聊天与频道聊天抽出共享的 composer draft upload 状态模型。
- 固定以下草稿状态：
  - `draftUploads`
  - `draftTokens`
  - `draftAttachments`
- 约定文件选择和图片粘贴都走同一条上传入口。
- 约定输入框 paste 快捷键触发的图片上传与文件上传按钮入口，共享同一套 draft upload 状态模型。
- 约定上传成功后自动插入 `#filename`；重名时先做草稿内 display name 去重，再插 token。
- 约定删除 token 或删除 pill 会移除对应 draft upload 的“待确认”状态。
- 约定发送按钮是否可用，应基于“正文非空或仍有 active draft upload”判断，而不是原始上传列表长度。

### 涉及文件

- `frontend/features/chat/components/chat/chat-input.tsx`
- `frontend/features/servers/ui/server-conversation-page-client.tsx`
- `frontend/features/servers/ui/conversation-drawers.tsx`
- `frontend/components/shared/file-card.tsx`
- 新增或抽取共享 composer helper / token sync helper

### 验收

- 粘贴图片与手动选文件都自动插入 `#token`。
- 输入框内通过 `Cmd+V` / `Ctrl+V` 粘贴图片会自动上传并插入 `#token`。
- 文件上传按钮入口继续可用，并与图片 paste 共享同一套 draft upload / token 确认逻辑。
- 同一条草稿中两个同名文件不会生成冲突 token。
- attachment pill 和正文 token 不会长期脱节。
- 删除最后一个 active token 且没有其他正文时，composer 不能再以“隐藏附件”名义发送空消息。

## Phase 2: 普通聊天 composer 改为 token-first 草稿确认

### 任务

- 在普通聊天中，把现有上传后的附件列表改造成“draft upload + auto token”模型。
- 发送时仅提交正文里仍保留 token 的 draft upload。
- 继续复用 `spec 34` 中的 `file_references` / `input_file` 语义，不另起新协议。
- 更新历史消息渲染，让自动上传确认过的图片/文件继续显示为附件与 file chip。

### 涉及文件

- `frontend/features/chat/components/chat/chat-input.tsx`
- `frontend/features/chat/api/chat-api.ts`
- `frontend/features/chat/services/message-parser.ts`
- `backend/app/services/file_reference_service.py`
- `backend/app/services/session_queue_service.py`

### 验收

- 普通聊天中，删除 `#token` 后对应文件不会进入本轮 run。
- 只保留图片 token、不写其他正文时，仍可发送该条消息。
- 发送成功后的 run 仍通过现有 staging 链路落到 `/workspace/inputs/...`。

## Phase 3: 频道聊天 composer 改为发送时发布

### 任务

- 频道主 composer 和 thread drawer 停止直接使用 `/artifacts/upload` 作为草稿上传入口。
- 频道主 composer 和 thread drawer 改为复用私有 draft upload handle，而不是提前拿到 artifact id。
- composer 内文件上传改为生成 draft upload，而不是立即发布 artifact。
- 发送消息时，将正文中仍保留 token 的 draft upload 一次性带给后端 finalize。
- 发送成功后，消息中展示的是 canonical published artifact 附件和 `artifact/reference` entities。
- composer confirm-on-send 链路不再额外写入独立 `artifact.uploaded` 事件消息。

### 涉及文件

- `frontend/features/servers/ui/server-conversation-page-client.tsx`
- `frontend/features/servers/ui/conversation-drawers.tsx`
- `frontend/features/servers/api/servers-api.ts`
- `frontend/features/servers/lib/server-conversation-view.ts`
- `frontend/features/servers/ui/conversation-message-row.tsx`
- `backend/app/schemas/server_channel_message.py`
- `backend/app/services/server_channel_message_service.py`
- `backend/app/services/channel_artifact_service.py`

### 验收

- 在频道聊天中粘贴图片后，发送前不会在 artifacts 列表中出现新共享文件。
- 删除 token 或删除 pill 后发送消息，不会产生 `/uploads/...` artifact。
- 发送成功后，artifact 才出现在 channel artifact 列表中，并与该条消息的 canonical entity 对齐。
- 不会新增独立 `artifact.uploaded` 事件消息噪音。

## Phase 4: 后端 finalize / publish / canonicalize 链路落地

### 任务

- 引入“draft upload ownership + finalization”后端校验逻辑。
- 频道消息创建入口在 request `content.attachments` 中先接收 draft upload handle，持久化前再 canonicalize 成最终附件与 entities。
- 普通聊天发送时：
  - 校验 temp upload 归属当前用户。
  - 只保留正文中仍出现 token 的对象。
  - 输出现有 `input_files` / `file_references`。
- 频道聊天发送时：
  - 校验 temp upload 归属当前用户与当前 channel send 请求。
  - 将确认对象发布为 channel artifact。
  - 复用现有 `/uploads/...` logical path 去重规则。
  - 将持久化消息内容 canonicalize 为：
    - `content.attachments`: published artifact `InputFile[]`
    - `content.entities`: `artifact/reference` entities
- 失败处理：
  - 若消息创建失败，不应留下半发布 artifact。
  - draft upload 仍可用于用户重试发送或手动删除。

### 设计约束

- finalization 只发生在发送消息的后端业务入口，不能由前端自行“先发布再发消息”拼接事务。
- composer 上传入口的 temp upload 不能直接伪装成 artifact id。
- channel artifact 的 `target_id` 必须仍然是 canonical artifact UUID，而不是 draft upload id。

### 验收

- 频道消息创建接口可以在单次请求内完成 publish + canonical message persist。
- 普通聊天不会因为 token 删除但前端遗漏清理附件而错误纳入 run；后端会再次过滤。
- channel message persisted content 不保留未确认 draft upload handle。

## Phase 5: 验证、回归与文档回写

### 验证命令

- `cd frontend && pnpm lint`
- `cd frontend && pnpm build`
- `cd frontend && node --test --experimental-strip-types --experimental-specifier-resolution=node features/chat/services/message-parser.test.ts features/servers/lib/server-conversation-messages.test.ts`
- `cd backend && uv run python -m unittest tests.test_session_queue_service tests.test_server_channel_message_service tests.test_channel_artifact_service`
- `cd executor && uv run python -m unittest tests.test_engine_input_hint`
- `uv run ruff check <changed-python-files>`
- `python3 -m py_compile <changed-python-files>`

### 手动验收

- 普通聊天里粘贴一张图片，自动插入 `#filename.png`，发送前删除 token，再发送：不会进入本轮 run。
- 普通聊天里通过 `Cmd+V` / `Ctrl+V` 粘贴一张图片时，会自动上传并插入 `#filename.png`，发送前删除 token 则不会进入本轮 run。
- 普通聊天里粘贴图片后保留 token 并发送：执行时可在 `/workspace/inputs/...` 使用它。
- 频道聊天里粘贴图片后不发送：artifacts 列表中不应出现新共享文件。
- 频道聊天里通过 `Cmd+V` / `Ctrl+V` 粘贴一张图片时，会自动上传 draft handle 并插入 `#filename.png`；发送前不发布，发送后才 materialize 为 `/uploads/...` artifact。
- 频道聊天里粘贴图片后删除 token 再发送：不会发布 `/uploads/...` artifact。
- 频道聊天里粘贴图片后保留 token 并发送：消息发送成功后才出现 `/uploads/...` artifact，且该消息展示附件与 `#` 引用一致。
- 频道 thread drawer 与主 composer 行为一致。

---

## 后续影响与边界说明

### 对 `spec 34` 的影响

本计划不替代普通聊天会话文件引用模型，而是补足其“composer 上传文件如何变成可确认的 `#file` 引用”这一生命周期。`spec 34` 仍负责会话文件引用的统一事实源与 runtime 路径语义。

### 对 `spec 30` 的影响

本计划不改变频道 `artifact/reference` 的最终契约；它只把“artifact id 在什么时候产生”从 upload-time 改成 send-time。发送成功后的 persisted entity 仍然必须符合 `spec 30` 的 canonical artifact reference 约束。

### 显式发布入口保持不变

独立的 channel artifact 面板、用户显式点击的“上传共享文件”等入口仍可继续使用即时发布和 `artifact.uploaded` 事件。这些入口表达的是“现在就把文件发布给频道”，与 composer 草稿语义不同。
