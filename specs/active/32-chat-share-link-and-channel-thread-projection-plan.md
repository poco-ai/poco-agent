# Chat share link and channel thread projection plan

## 元数据

| 字段 | 值 |
| --- | --- |
| **创建日期** | 2026-06-09 |
| **预期改动范围** | backend session share models / share and fork APIs / channel import service / frontend chat share UI / readonly share page / server thread timeline / tests |
| **改动类型** | feat |
| **优先级** | P1 |
| **状态** | in-progress |
| **关联 constitution** | `specs/constitution/2026-06-09-chat-share-link-and-channel-thread-projection.md` |

## 实施阶段

- [x] Phase 0: 固定分享语义和实施计划
- [x] Phase 1: 后端支持 share link、只读快照和 fork
- [x] Phase 2: 后端支持分享到频道 thread projection
- [ ] Phase 3: 前端支持 share link、频道分享和 timeline 展示
- [ ] Phase 4: 验证、回归和 spec 回写

---

## 背景

### 问题陈述

当前普通聊天的 Share 更接近图片导出，无法生成可打开的只读会话，也无法让其他用户 fork 到自己的普通聊天继续。另一方面，频道协作已经具备 thread、event、shared artifacts 和 channel runtime；普通聊天成果应能以 thread 形式沉淀到频道，而不是复制成另一个私有聊天入口。

### 目标

- 普通聊天可生成 share link。
- 其他用户打开 share link 后看到只读页面。
- 只读页面可 fork 到当前用户的普通聊天继续。
- 普通聊天可分享到频道，频道中显示 event、主消息和对应 thread。
- Thread drawer 和频道右侧区域能显示对应 timeline，并复用普通聊天 timeline 的视觉和定位思路。

### 非目标

- 不在本轮实现通用 `Copy to my chats` for any thread。
- 不把 channel runtime tools 带入普通 private fork。
- 不支持导入时自动触发 agent。
- 不把 local mount、agent persistent state 或私有 workspace 自动发布到频道。

---

## Phase 0: 固定分享语义和实施计划

### 目标

把产品语义、对象边界和实施顺序写入 constitution 与 active spec，作为后续提交依据。

### 任务清单

#### 0.1 写入 constitution

**涉及文件：**

- `specs/constitution/2026-06-09-chat-share-link-and-channel-thread-projection.md`

**验收标准：**

- [x] 明确 share link 是只读快照，不是 live mirror
- [x] 明确 fork 是普通聊天副本，不继承 channel runtime
- [x] 明确 share to channel 是 thread projection，不自动触发 agent

#### 0.2 写入 active plan

**涉及文件：**

- `specs/active/32-chat-share-link-and-channel-thread-projection-plan.md`

**验收标准：**

- [x] Phase 划分可以对应至少 3 个提交
- [x] 后续每个 Phase 完成后同步勾选 todo

---

## Phase 1: 后端支持 share link、只读快照和 fork

### 目标

建立普通聊天 share link 的后端对象和 API，使登录用户可以打开只读快照并 fork 到自己的普通聊天。

### 任务清单

#### 1.1 增加 session share 数据模型和迁移

**涉及文件：**

- `backend/app/models/session_share.py`
- `backend/app/models/__init__.py`
- `backend/alembic/versions/*.py`

**验收标准：**

- [x] share token 不可猜测且唯一
- [x] share 记录关联 source session 和 owner
- [x] soft revoke / disabled 状态可表达

#### 1.2 增加 share/fork service 和 API

**涉及文件：**

- `backend/app/services/session_share_service.py`
- `backend/app/api/v1/session_shares.py`
- `backend/app/schemas/session_share.py`
- `backend/app/api/v1/__init__.py`

**验收标准：**

- [x] owner 可以为自己的普通聊天创建 share link
- [x] share token 可读取只读 snapshot，包括 session、messages、runs
- [x] 登录用户可从 share token fork 出自己的普通聊天
- [x] fork 后 `sdk_session_id=None`，不会继续原 SDK thread

---

## Phase 2: 后端支持分享到频道 thread projection

### 目标

让普通聊天可以被投影到频道，形成 event、root message、thread replies 和 timeline 数据，不触发 agent。

### 任务清单

#### 2.1 增加 channel import service

**涉及文件：**

- `backend/app/services/channel_conversation_import_service.py`
- `backend/app/schemas/session_share.py`
- `backend/app/api/v1/session_shares.py`

**验收标准：**

- [x] 分享到频道时校验当前用户是频道成员
- [x] 创建 `conversation.shared` event
- [x] 创建 root message 和完整 thread replies
- [x] 导入 transcript 中的 `@agent` 不产生 run / queue item

#### 2.2 提供 thread timeline 数据

**涉及文件：**

- `backend/app/schemas/session_share.py`
- `backend/app/services/channel_conversation_import_service.py`
- `backend/app/services/server_channel_message_service.py`

**验收标准：**

- [x] timeline item 能关联 imported message、source run、artifact reference
- [x] thread 页面可根据 root message id 读取 timeline

---

## Phase 3: 前端支持 share link、频道分享和 timeline 展示

### 目标

普通聊天 UI 增加 share link 与 share to channel；新增只读 share 页面；频道 thread 和右侧区域显示 timeline。

### 任务清单

#### 3.1 普通聊天 Share UI

**涉及文件：**

- `frontend/features/chat/components/execution/chat-panel/chat-panel.tsx`
- `frontend/features/chat/api/chat-api.ts`
- `frontend/lib/i18n/locales/*/translation.json`

**验收标准：**

- [ ] Share 菜单提供 copy link 和 share to channel
- [ ] copy link 创建 share token 并复制 URL
- [ ] share to channel 可选择频道并调用后端 projection API

#### 3.2 只读 share 页面和 fork

**涉及文件：**

- `frontend/app/[lng]/share/[token]/page.tsx`
- `frontend/features/chat/components/share/*`

**验收标准：**

- [ ] share 页面显示只读 transcript 和 timeline
- [ ] fork 按钮创建普通聊天并跳转

#### 3.3 频道 thread timeline

**涉及文件：**

- `frontend/features/servers/ui/conversation-drawers.tsx`
- `frontend/features/servers/ui/server-conversation-page-client.tsx`
- `frontend/features/chat/components/layout/run-evolution-timeline.tsx`

**验收标准：**

- [ ] imported thread 右侧显示 timeline
- [ ] 频道右侧区域可显示当前 thread timeline
- [ ] timeline 点击可以定位到 thread message 或打开 execution details

---

## Phase 4: 验证、回归和 spec 回写

### 目标

补齐关键测试，运行可用验证命令，并把实施状态回写到本 spec。

### 任务清单

#### 4.1 后端测试

**验收标准：**

- [ ] share link create/read/fork 测试通过
- [ ] share to channel 不触发 agent 测试通过

#### 4.2 前端静态验证

**验收标准：**

- [ ] `pnpm lint` 通过或记录阻塞原因
- [ ] `pnpm build` 通过或记录阻塞原因

#### 4.3 Spec 状态回写

**验收标准：**

- [ ] 所有已完成 phase 标记为 `[x]`
- [ ] 状态更新为 `review`

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
| --- | --- | --- |
| share link 暴露私有上下文 | 用户隐私受损 | token 不可猜测，share 只由 owner 创建，fork 去除原 owner 身份 |
| 导入频道误触发 agent | 产生非预期 run | import service 不调用 `send_message()` 和 trigger service，测试覆盖 `@agent` 文本 |
| channel tools 污染 private fork | private chat 仍能操作频道 | fork 到普通聊天时不写入 server/channel/agent runtime config |
| timeline 成为第二事实源 | UI 状态不一致 | timeline 只引用 message/run/artifact id，不存储正文副本作为事实 |
