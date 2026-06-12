# Chat share link and channel thread projection plan

## 元数据

| 字段 | 值 |
| --- | --- |
| **创建日期** | 2026-06-09 |
| **预期改动范围** | backend session share models / share and fork APIs / channel import service / frontend chat share UI / readonly share page / server thread timeline / tests |
| **改动类型** | feat |
| **优先级** | P1 |
| **状态** | review follow-up |
| **关联 constitution** | `specs/constitution/2026-06-09-chat-share-link-and-channel-thread-projection.md` |

## 实施阶段

- [x] Phase 0: 固定分享语义和实施计划
- [x] Phase 1: 后端支持 share link、只读快照和 fork
- [x] Phase 2: 后端支持分享到频道 thread projection
- [x] Phase 3: 前端支持 share link、频道分享和 timeline 展示
- [x] Phase 4: 验证、回归和 spec 回写
- [x] Phase 5: Browser 批注修正与只读分享体验对齐

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
- Share link 打开后应尽量复用普通聊天区布局：已登录用户保留应用 shell，匿名用户可查看同一只读聊天区；写操作不可用。
- Share to channel 的 event/thread 展示要保持频道语义：event actor 显示用户名，thread transcript 只显示正文，不显示 `User` / `Assistant` 这类角色 fallback。

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

- [x] Share 菜单提供 copy link 和 share to channel
- [x] copy link 创建 share token 并复制 URL
- [x] share to channel 可选择频道并调用后端 projection API

#### 3.2 只读 share 页面和 fork

**涉及文件：**

- `frontend/app/[lng]/share/[token]/page.tsx`
- `frontend/features/chat/components/share/*`

**验收标准：**

- [x] share 页面显示只读 transcript 和 timeline
- [x] fork 按钮创建普通聊天并跳转

#### 3.3 频道 thread timeline

**涉及文件：**

- `frontend/features/servers/ui/conversation-drawers.tsx`
- `frontend/features/servers/ui/server-conversation-page-client.tsx`
- `frontend/features/chat/components/layout/run-evolution-timeline.tsx`

**验收标准：**

- [x] imported thread 右侧显示 timeline
- [x] 频道右侧区域可显示当前 thread timeline
- [x] timeline 点击可以定位到 thread message 或打开 execution details

---

## Phase 4: 验证、回归和 spec 回写

### 目标

补齐关键测试，运行可用验证命令，并把实施状态回写到本 spec。

### 任务清单

#### 4.1 后端测试

**验收标准：**

- [x] share link create/read/fork 测试通过
- [x] share to channel 不触发 agent 测试通过

**验证记录：**

- `cd backend && uv run python -m unittest tests/test_session_share_service.py -v` 通过 7 个用例，覆盖 share create/read/fork、snapshot immutability、fork runtime config 清理、share-to-channel owner-only、artifact reference 边界和不触发 agent。
- `cd backend && uv run python -m py_compile app/models/session_share.py app/repositories/session_share_repository.py app/schemas/session_share.py app/services/session_share_service.py app/api/v1/session_shares.py app/api/v1/__init__.py` 通过。
- `cd backend && uv run ruff check app/models/session_share.py app/schemas/session_share.py app/services/session_share_service.py tests/test_session_share_service.py` 通过。
- `cd backend && uv run -m alembic heads` 输出 `2b7e4c91d6a0 (head)`。

#### 4.2 前端静态验证

**验收标准：**

- [x] `pnpm lint` 通过或记录阻塞原因
- [x] `pnpm build` 通过或记录阻塞原因

**验证记录：**

- `cd frontend && pnpm lint` 通过。
- `cd frontend && pnpm build` 通过；存在 Next.js workspace root 多 lockfile warning，不影响构建。
- `cd frontend && pnpm exec tsc --noEmit` 暴露既有测试类型问题：`features/channel-tasks/lib/channel-task-board.test.ts` 中 `displayNumber` 可为 `undefined`，与 `ChannelTask.displayNumber: number` 不匹配；本次 `pnpm build` 未受影响。

#### 4.3 Spec 状态回写

**验收标准：**

- [x] 所有已完成 phase 标记为 `[x]`
- [x] 状态更新为 `review`

#### 4.4 Review follow-up

**验收标准：**

- [x] share link 创建时冻结 session/messages/runs/timeline；只读页、fork、频道投影不再重新读取 source session live state。
- [x] channel projection 不盲拷普通聊天 artifact references；频道可见文件仍以后续 published artifacts 解析为边界。
- [x] public share snapshot 不返回 owner user id 或 source session id 等内部字段。
- [x] share-to-channel 只允许原 share owner 执行；持有 share link 的接收者如需再次传播，应先 fork 成自己的普通聊天。
- [x] `conversation.shared` event 在频道 UI 中使用专门 label，不再退化为 generic channel update。

## Phase 5: Browser 批注修正与只读分享体验对齐

### 目标

根据浏览器批注修正已经跑通但显示语义偏差的部分：share link 页面要成为普通聊天区的只读变体，频道 event/thread 要展示人类可读内容。

### 任务清单

#### 5.1 更新设计文档

**涉及文件：**

- `specs/constitution/2026-06-09-chat-share-link-and-channel-thread-projection.md`
- `specs/active/32-chat-share-link-and-channel-thread-projection-plan.md`

**验收标准：**

- [x] 明确 share link 不是独立全屏阅读页，而是普通聊天区只读变体
- [x] 明确匿名用户可查看但不能直接 fork
- [x] 明确 event actor 显示用户名而非 user id
- [x] 明确 imported thread 显示原消息正文而非 role fallback

#### 5.2 修正 share link 只读页面

**涉及文件：**

- `frontend/app/[lng]/share/[token]/page.tsx`
- `frontend/features/chat/components/share/session-share-page-client.tsx`
- `frontend/lib/i18n/locales/*/translation.json`

**验收标准：**

- [x] 已登录用户打开 share link 时保留 app shell，share transcript 替换普通聊天区域
- [x] 匿名用户可以只读查看 share transcript
- [x] 匿名用户不显示或不能触发 fork
- [x] 重新生成、新建分支、编辑和 composer 写入不可用
- [x] 移除 share 页面独立的简化 timeline rail，避免与普通聊天 timeline 语义冲突

#### 5.3 修正频道 event/thread 展示

**涉及文件：**

- `backend/app/services/session_share_service.py`
- `backend/tests/test_session_share_service.py`

**验收标准：**

- [x] `conversation.shared` event 的 actor label 使用用户显示名、邮箱或可读 fallback
- [x] 普通聊天嵌套 SDK message 能抽取正文，不再把 `User` / `Assistant` 当作 thread 正文
- [x] share to channel 仍不触发 agent

#### 5.4 验证和回写

**验收标准：**

- [x] 后端 session share 单测通过
- [x] 相关 Python 文件 py_compile / ruff 通过
- [x] 前端 lint / build 通过或记录阻塞原因
- [x] 本 Phase todo 状态回写为完成

**验证记录：**

- `cd backend && uv run python -m unittest tests/test_session_share_service.py -v` 通过 8 个用例，新增覆盖 nested SDK message 正文抽取和 `conversation.shared` actor label。
- `cd backend && uv run python -m py_compile app/services/session_share_service.py tests/test_session_share_service.py` 通过。
- `cd backend && uv run ruff check app/services/session_share_service.py tests/test_session_share_service.py` 通过。
- `cd frontend && pnpm lint` 通过。
- `cd frontend && pnpm build` 通过；仍存在既有 Next.js workspace root 多 lockfile warning，不影响构建。

## Phase 6: 只读 share 工作区文件预览补齐

### 目标

share link 打开后右侧工作区面板应与普通聊天保持同一套语义：Computer 展示执行摘要，Artifacts 展示文件树和文件预览。`.ts`、`.tsx`、`.md` 等文本文件不应在 share 场景退化成只有路径的 file change 列表。

### 设计约束

- public share snapshot 不暴露 `workspace_manifest_key`、`workspace_files_prefix` 或 source session 内部字段。
- share payload 不固化 presigned URL；打开 share 时由后端基于冻结在 `fork_runs` 中的 manifest key/prefix 动态生成只读 `workspace_files`。
- 前端 share Artifacts 复用普通聊天的 `FileSidebar` 和 `DocumentViewer`，保证 TypeScript 文件预览路径与普通聊天一致。
- 若旧 share 或未导出工作区没有 `workspace_files`，仍显示 file changes 作为降级视图。

### 任务清单

#### 6.1 后端 public snapshot 带出只读文件树

**涉及文件：**

- `backend/app/schemas/session_share.py`
- `backend/app/services/session_share_service.py`
- `backend/app/utils/workspace_export.py`
- `backend/app/api/v1/runs.py`
- `backend/app/api/v1/sessions.py`

**验收标准：**

- [x] `SharedRunSummary` 包含 `workspace_files`
- [x] share snapshot 读取时动态生成 fresh file URLs
- [x] 普通 run/session workspace files 与 share 使用同一 manifest 解析 helper

#### 6.2 前端 share Artifacts 复用普通文件预览

**涉及文件：**

- `frontend/features/chat/types/api/session-share.ts`
- `frontend/features/chat/api/session-share-api.ts`
- `frontend/features/chat/components/share/session-share-execution-panel.tsx`

**验收标准：**

- [x] share DTO 映射 `workspace_files -> workspaceFiles`
- [x] share Artifacts 显示文件树
- [x] 点击 `.ts` 文件进入 `DocumentViewer` 预览
- [x] 没有工作区导出时保留 file changes 降级视图

#### 6.3 验证和回写

**验收标准：**

- [x] 后端 session share 单测通过
- [x] 相关 Python 文件 py_compile 通过
- [x] 前端相关文件 lint/type 检查通过或记录阻塞原因

**验证记录：**

- `cd backend && uv run python -m unittest tests.test_session_share_service -v` 通过 9 个用例，新增覆盖 share snapshot 从 fork run manifest 生成 `.ts` 文件节点和只读 URL。
- `cd backend && uv run python -m py_compile app/utils/workspace_export.py app/api/v1/runs.py app/api/v1/sessions.py app/schemas/session_share.py app/services/session_share_service.py tests/test_session_share_service.py` 通过。
- `cd backend && uv run ruff check app/utils/workspace_export.py app/api/v1/runs.py app/api/v1/sessions.py app/schemas/session_share.py app/services/session_share_service.py tests/test_session_share_service.py` 通过。
- `cd frontend && pnpm lint` 通过。
- `cd frontend && pnpm exec tsc --noEmit --pretty false` 未通过；失败点为既有 `features/channel-tasks/lib/channel-task-board.test.ts` 中 `displayNumber?: number` 与 `ChannelTask.displayNumber: number` 类型不匹配，和本次 share Artifacts 变更无关。

## Phase 7: 只读 share 回放、标题生成和 TypeScript 预览回归修正

### 目标

根据 2026-06-10 的复查批注，补齐 share link 右侧 Computer 面板的真实回放能力，并修正标题生成和 `.ts` 文件预览在普通会话与 share 场景中的共同问题。

### 设计约束

- share link Computer 面板应复用普通会话 `ComputerPanel` 的 viewer、播放控制和步骤列表，不维护第二套只显示摘要的 UI。
- public share API 不要求匿名用户携带登录态，也不调用私有 run screenshot API；浏览器截图在读取 public snapshot 时由后端生成只读 presigned URL。
- public share payload 可包含 replay 所需的 `tool_output` 与 `browser_screenshot_url`，但不得返回 source session、owner、manifest key 或 workspace prefix。
- 标题生成与模型选择必须共用 provider/env 解析规则；只配置 GLM/MiniMax/DeepSeek 任一可识别 provider key 时，也应可生成标题。
- `.ts`、`.tsx` 等代码文件必须优先按文本预览处理；不能因 Python `mimetypes` 把 `.ts` 判为 `video/mp2t` 而进入视频路径。

### 任务清单

#### 7.1 share Computer 回放复用普通会话面板

**涉及文件：**

- `backend/app/schemas/session_share.py`
- `backend/app/services/session_share_service.py`
- `frontend/features/chat/components/execution/computer-panel/index.tsx`
- `frontend/features/chat/components/share/session-share-execution-panel.tsx`
- `frontend/features/chat/api/session-share-api.ts`
- `frontend/features/chat/types/api/session-share.ts`

**验收标准：**

- [x] share snapshot 返回 `tool_output`
- [x] browser replay step 返回只读 `browser_screenshot_url`
- [x] share Computer tab 复用 `ComputerPanel`，显示播放按钮、截图 viewer 和步骤 timeline
- [x] 旧 share snapshot 缺少 replay payload 时可从 source run 补齐只读展示数据

#### 7.2 标题生成 provider/env 解析修正

**涉及文件：**

- `backend/app/core/settings.py`
- `backend/app/services/model_config_service.py`
- `backend/app/services/session_title_service.py`
- `backend/tests/test_session_title_service.py`

**验收标准：**

- [x] `Settings` 声明 GLM/MiniMax/DeepSeek key 和 base URL 字段
- [x] provider spec 能从 `.env` settings 字段读取对应 key
- [x] `DEFAULT_MODEL=glm-*` 且只配置 `GLM_API_KEY` 时，标题生成 resolver 返回 GLM provider

#### 7.3 `.ts` 文件 MIME 预览修正

**涉及文件：**

- `backend/app/utils/mime.py`
- `backend/app/api/v1/sessions.py`
- `backend/app/services/agent_state_browser_service.py`
- `backend/app/services/local_mount_browser_service.py`
- `executor_manager/app/utils/mime.py`
- `executor_manager/app/services/workspace_export_service.py`
- `executor_manager/app/services/workspace_manager.py`
- `frontend/features/chat/components/execution/file-panel/document-viewer/index.tsx`

**验收标准：**

- [x] workspace export、local mount、agent state browser 都使用统一 MIME override
- [x] `.ts` 返回 `text/typescript`，不再继承 `mimetypes.guess_type(".ts") == "video/mp2t"` 的误判
- [x] 前端 `DocumentViewer` 在已识别文本后缀时不会再进入 video viewer

#### 7.4 验证和回写

**验收标准：**

- [x] 后端 share/title 单测通过
- [x] 后端与 executor_manager 定向 py_compile/ruff 通过
- [x] 前端 lint 通过
- [x] TypeScript 检查结果记录清楚

**验证记录：**

- `cd backend && uv run python -m unittest tests.test_session_share_service tests.test_session_title_service -v` 通过 14 个用例。
- `cd backend && uv run python -m py_compile app/services/session_share_service.py app/schemas/session_share.py app/services/session_title_service.py app/services/model_config_service.py app/core/settings.py app/utils/mime.py app/api/v1/sessions.py app/services/agent_state_browser_service.py app/services/local_mount_browser_service.py` 通过。
- `cd backend && uv run ruff check app/services/session_share_service.py app/schemas/session_share.py app/services/session_title_service.py app/services/model_config_service.py app/core/settings.py app/utils/mime.py app/api/v1/sessions.py app/services/agent_state_browser_service.py app/services/local_mount_browser_service.py tests/test_session_share_service.py tests/test_session_title_service.py` 通过。
- `cd executor_manager && uv run python -m py_compile app/utils/mime.py app/services/workspace_export_service.py app/services/workspace_manager.py` 通过。
- `cd executor_manager && uv run ruff check app/utils/mime.py app/services/workspace_export_service.py app/services/workspace_manager.py` 通过。
- `cd frontend && pnpm lint` 通过。
- `cd frontend && pnpm exec tsc --noEmit --pretty false` 未通过；失败点仍为既有 `features/channel-tasks/lib/channel-task-board.test.ts` 中 `displayNumber?: number` 与 `ChannelTask.displayNumber: number` 类型不匹配，和本次变更无关。

## Phase 8: Share to channel 发布独立频道文件夹

### 目标

分享到频道时，除了投影 transcript/thread/event，也把普通聊天最终 workspace 中可发布文件复制到频道 Artifacts 的 `/Shared/<share-id>/...` 文件夹。频道协作后续读取的是频道 artifact 副本，而不是原普通聊天 workspace 对象。

### 设计约束

- 目标 logical path 固定为 `/Shared/<share-id>/<relative-path>`，频道 Artifacts UI 中应表现为 `Shared / <share-id> / ...`。
- 发布必须复制对象到 `channel-artifacts/<server-id>/<channel-id>/Shared/<share-id>/...`，不能只引用原 workspace object key。
- 发布只使用 share snapshot 中冻结的 session workspace export；若 session 级 export 不存在，允许降级到最近 terminal run 的 export。
- 继续沿用 channel artifact 的 publishable path 规则，跳过 `/agent_state/` 和 `/.poco-local/`。
- `conversation.shared` event content 记录 `shared_artifacts_path` 和 `published_artifact_count`，作为审计和 UI 提示依据。

### 任务清单

#### 8.1 后端发布 share workspace 到频道 artifacts

**涉及文件：**

- `backend/app/services/storage_service.py`
- `backend/app/services/channel_artifact_service.py`
- `backend/app/services/session_share_service.py`

**验收标准：**

- [x] S3/RustFS 支持单对象复制
- [x] `ChannelArtifactService` 能从 workspace manifest 发布 `session_share` artifacts
- [x] share-to-channel 调用发布逻辑，并写入 `/Shared/<share-id>` 路径与发布数量

#### 8.2 测试覆盖独立发布语义

**涉及文件：**

- `backend/tests/test_channel_artifact_service.py`
- `backend/tests/test_session_share_service.py`

**验收标准：**

- [x] 发布时复制 object key 到 channel artifact namespace
- [x] 发布后的 artifact `source_session_id=None`，与原普通聊天 workspace 解耦
- [x] 频道 artifact tree 把 `session_share` 文件归入 `Shared / <share-id>`
- [x] share-to-channel event 包含 `shared_artifacts_path` 和 `published_artifact_count`

**验证记录：**

- `cd backend && uv run python -m unittest tests.test_channel_artifact_service tests.test_session_share_service -v` 通过 26 个用例。
- `cd backend && uv run ruff check app/services/storage_service.py app/services/channel_artifact_service.py app/services/session_share_service.py tests/test_channel_artifact_service.py tests/test_session_share_service.py` 通过。
- `cd backend && uv run python -m py_compile app/services/storage_service.py app/services/channel_artifact_service.py app/services/session_share_service.py tests/test_channel_artifact_service.py tests/test_session_share_service.py` 通过。

## Phase 9: Sidebar conversation menu share entrypoints

### 目标

只读 share 页面保留应用 shell 时，左侧普通聊天历史菜单也应提供和普通聊天顶部一致的 share 操作：复制分享链接、分享到频道。该入口面向“再次发布/转发已有普通聊天”的操作，不应引入第二套 share 语义。

### 设计约束

- 侧边栏菜单入口复用普通聊天顶部的 session share 创建、复制链接和 share-to-channel API。
- 分享到频道仍走 `sessionShareApi.shareToChannel()`，因此继续触发 Phase 8 的 `/Shared/<share-id>/...` 独立发布副本。
- 菜单项文案复用既有 `chat.copyShareLink` 与 `chat.shareToChannel` i18n key，避免只补中文/英文。
- 只读 share 页面里的菜单入口只是针对左侧会话历史中的普通聊天，不改变当前 share snapshot 的只读状态。

### 任务清单

#### 9.1 抽取 share action 和 channel dialog

**涉及文件：**

- `frontend/features/chat/hooks/use-session-share-actions.ts`
- `frontend/features/chat/components/share/share-to-channel-dialog.tsx`
- `frontend/features/chat/components/execution/chat-panel/chat-panel.tsx`

**验收标准：**

- [x] 普通聊天顶部分享菜单继续可复制链接和分享到频道
- [x] share token 创建、目标频道加载、channel projection 只维护一套前端逻辑

#### 9.2 侧边栏任务菜单增加分享入口

**涉及文件：**

- `frontend/features/projects/components/task-actions-dropdown.tsx`
- `frontend/components/shell/sidebar/task-history-list.tsx`

**验收标准：**

- [x] 任务菜单显示复制分享链接
- [x] 任务菜单显示分享到频道
- [x] 分享过程中禁用重复点击

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
| --- | --- | --- |
| share link 暴露私有上下文 | 用户隐私受损 | token 不可猜测，share 只由 owner 创建，fork 去除原 owner 身份 |
| 导入频道误触发 agent | 产生非预期 run | import service 不调用 `send_message()` 和 trigger service，测试覆盖 `@agent` 文本 |
| channel tools 污染 private fork | private chat 仍能操作频道 | fork 到普通聊天时不写入 server/channel/agent runtime config |
| timeline 成为第二事实源 | UI 状态不一致 | timeline 只引用 message/run/artifact id，不存储正文副本作为事实 |
