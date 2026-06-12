# 普通聊天会话文件引用计划

## 元数据

| 字段 | 值 |
| --- | --- |
| **创建日期** | 2026-06-11 |
| **修订日期** | 2026-06-12 |
| **预期改动范围** | frontend chat input / task composer input / chat message rendering / session file APIs / task enqueue payload / backend task schema and message metadata / executor workspace reference hint / tests |
| **改动类型** | feat |
| **优先级** | P1 |
| **状态** | review |
| **关联 spec** | `specs/active/30-structured-channel-mentions-and-context-references-plan.md` |

## 修订说明

上一版把普通聊天 `#` 文件引用收窄成“当前草稿上传附件选择器”。这不符合产品目标。真正目标是：普通聊天里 `#` 能引用当前会话中的文件，包括用户上传文件、历史消息输入文件，以及 agent 在 workspace export 中生成的文件。

本版保留已完成的 textarea 交互基础，但重置协议和后端语义：引用对象是统一的会话文件引用，不是仅指向本轮 `input_files` 的轻量注释。

## 实施阶段

- [x] Phase 0: 保留前端 `#` 输入交互基线
- [x] Phase 1: 固定统一会话文件引用契约
- [x] Phase 2: 前端候选源扩展为当前会话文件索引
- [x] Phase 3: 后端解析引用并保留 workspace path 语义
- [x] Phase 4: 历史消息渲染、编辑、重跑和队列项兼容
- [x] Phase 5: 验证、回归和文档回写

---

## 背景

### 问题陈述

频道聊天已经有 `@` / `#` 双入口，`#` 可以引用 channel artifact、task、thread 等频道上下文对象。普通聊天也需要类似的文件引用能力，但普通聊天没有频道 runtime tools，也没有 published artifact scope。

普通聊天中用户真正想引用的是“这个会话里能看到的文件”：

- 当前草稿刚上传的文件。
- 之前用户消息带入的 input files。
- agent 在当前会话 workspace 中创建、修改并通过 workspace export 暴露的文件。

因此，普通聊天 `#file` 不能只绑定到当前草稿的附件，也不能只把正文 token 传给模型。它必须先解析成结构化会话文件引用。对于 agent 已经写入当前 session workspace 的文件，引用语义是“用户正在讨论 `/workspace/...` 中的这个路径”，不是重新上传或复制成 input；只有用户上传附件、历史输入文件这类本来就不在 workspace 正文路径上的对象，才继续走 `input_files` staging。

### 目标

- 普通聊天输入框支持输入 `#` 后选择当前会话中的文件。
- 文件候选统一展示，不要求用户知道文件来自上传、历史输入还是 agent workspace 输出。
- 选择文件后正文插入人类可读 token，例如 `#report.md`。
- 发送时携带结构化 references；后端解析 references，校验 workspace path 或补齐上传 input。
- workspace 文件引用在 runtime 中以 `/workspace/<path>` 为准，不让模型把它猜成 `/inputs/<path>`；上传/历史 input 文件仍以 staged `input_files.path` 为准。
- 历史消息可以把已验证的 `#file` 渲染为 file chip。
- 编辑、重跑和 queued query 更新不能让正文 token 与实际 runtime inputs 脱节。

### 非目标

- 不把普通聊天强行改造成频道 artifact runtime。
- 不让 executor 直接读取任意 OSS key 或浏览器预签名 URL。
- 不在 prompt 中塞文件内容全文。
- 不支持跨会话文件引用。
- 不把 local mount 的任意文件默认纳入第一版引用范围；local mount 文件需要单独权限和读取策略。
- 不引入完整富文本编辑器；第一版继续使用 textarea + draft reference 状态。

### 关键洞察

#### 1. UI 对象应统一，但 runtime 路径语义不能混成 `input_files`

用户看到的是统一文件对象，但不同来源的 runtime 语义不同：workspace 文件已经位于会话 workspace，应作为 `/workspace/...` 路径提示给 agent；上传文件和历史 input 文件才需要通过 `input_files` staging 暴露到 `/workspace/inputs/...`。

#### 2. workspace 文件已经有事实源

session/run workspace export 已经记录 `workspace_manifest_key` 和 `workspace_files_prefix`，并通过 `/sessions/{session_id}/workspace/files`、`/runs/{run_id}/workspace/files` 暴露 `FileNode`。manifest 中的 file entry 包含 workspace path、OSS object key、size、mime type，可用于生成 synthetic `InputFile`。

#### 3. 不能让前端预签名 URL 成为执行事实源

前端 artifacts panel 能拿到 preview URL，但 runtime 不应该依赖这个 URL。后端必须从 session ownership 和 workspace manifest 校验引用，再使用 object key 构造 `InputFile.source`。

#### 4. 默认引用 session latest workspace

继续聊天时默认引用当前会话最新 workspace export，而不是当前 UI 选中的历史 run 快照。run-scoped workspace 文件可以用于浏览，但发送下一轮时应以 session latest 为默认事实源，避免旧 run 文件覆盖当前 workspace 语义。

---

## 统一契约

### Frontend `ChatFileReference`

```ts
type ChatFileReference =
  | {
      id: string;
      kind: "input_file";
      source: string;
      insertedText: string;
      displayName: string;
      range?: { start: number; end: number };
      metadata?: {
        inputFileId?: string | null;
        size?: number | null;
        contentType?: string | null;
        path?: string | null;
      };
    }
  | {
      id: string;
      kind: "workspace_file";
      sessionId: string;
      path: string;
      insertedText: string;
      displayName: string;
      range?: { start: number; end: number };
      metadata?: {
        size?: number | null;
        contentType?: string | null;
        sourceKind?: string | null;
      };
    };
```

第一版保留 discriminated union，避免把 workspace path 和 upload source 混成一个字段。UI 层可以统一展示为文件候选，后端按 `kind` 做权限校验和 runtime input 生成。

### Backend `FileReference`

后端 schema 与前端字段同构，接收 `TaskConfig.file_references`。为兼容 `ae3623a3` 已落地的前端基线，短期可以继续接受 `input_file_references` 作为 alias，但内部服务应统一转成 `file_references`。

### Runtime 解析

后端创建 run snapshot 前执行：

1. 合并 project inputs、当前上传 attachments、历史/引用需要的 synthetic inputs。
2. 对 `input_file` reference，要求 `source` 能在合并后的 input files 中找到。
3. 对 `workspace_file` reference，要求 session 属于当前用户、workspace export ready、manifest 中存在该 path。
4. `workspace_file` 不构造 `InputFile`，不触发 EM attachment staging；仅保存规范化后的 `/path`。
5. executor prompt hint 把 `workspace_file` 映射为 `/workspace/<path>`，并明确禁止 agent 猜测 `/inputs/<path>`。
6. 保存 `input_files`（仅上传/历史/project inputs）和 `file_references` 到 run config snapshot。

---

## Phase 1: 固定统一会话文件引用契约

### 任务

- 将前端 `ChatInputFileReference` 扩展或重命名为统一 `ChatFileReference`。
- 后端新增 `FileReference` schema，支持 `input_file` 与 `workspace_file`。
- `TaskConfig` 增加 `file_references`，兼容旧的 `input_file_references` 入参。
- 更新 executor manager / executor schema 只透传已解析后的 references。

### 验收

- `input_file` 与 `workspace_file` 不共用含义模糊的 `source` 字段。
- 旧前端基线可继续发送当前上传引用。
- 新字段命名反映“会话文件”，不再暗示只支持本轮 input files。

## Phase 2: 前端候选源扩展为当前会话文件索引

### 任务

- 复用已落地的 `#` trigger、候选菜单和键盘选择。
- 新增 session file candidate 构建逻辑：
  - 当前 draft attachments。
  - 历史消息 attachments。
  - session latest workspace files。
- 去重策略：同一 `kind + source/path` 只显示一次；同名文件用路径或来源说明区分。
- 首页 task composer 没有 session 上下文时，仅显示当前 draft attachments。

### 验收

- 在已有会话继续输入 `#` 时可以看到 agent 生成的 workspace 文件。
- 新建任务首页不会请求不存在的 session workspace。
- 删除正文 token 或删除 draft attachment 会过滤对应 stale reference。

## Phase 3: 后端解析引用并保留 workspace path 语义

### 任务

- 新增 file reference resolver service。
- 从 session workspace manifest 解析 workspace file reference。
- workspace file reference 只校验并保存路径，不合并进 run snapshot `input_files`。
- 确保 executor manager 只 staging 上传/历史 input，不 staging workspace reference。
- 让 queued item update 同步过滤/解析 references。

### 验收

- 引用不存在的 workspace path 返回 400。
- 引用其他用户/其他 session 文件返回 403 或 400。
- workspace reference 不出现在本轮 `input_files`，executor hint 直接指向 `/workspace/...`。
- 不依赖 preview URL。

## Phase 4: 历史消息渲染、编辑、重跑和队列项兼容

### 任务

- user message metadata 保存 `file_references`。
- parser 解析 snake_case / camelCase references。
- chip 渲染统一展示 upload/workspace 文件。
- edit/regenerate 复用原 run references，并按新 prompt 过滤删除的 token。

### 验收

- 历史 user message 中 `#file` 渲染为 chip。
- 编辑删除 `#file` 后 references 不再进入新 run。
- regenerate 原消息会保留当时引用过的文件。

## Phase 5: 验证、回归和文档回写

### 验证命令

- `cd frontend && node --test --experimental-strip-types --experimental-specifier-resolution=node features/chat/lib/input-file-reference.test.ts features/chat/services/message-parser.test.ts`
- `cd frontend && pnpm lint`
- `cd frontend && pnpm build`
- `cd backend && uv run python -m unittest tests.test_task_service tests.test_session_queue_service`
- `cd executor && uv run python -m unittest tests.test_engine_input_hint`
- `uv run ruff check <changed-python-files>`
- `python3 -m py_compile <changed-python-files>`

### 手动验收

- 在已有会话中让 agent 创建文件。
- 继续输入下一条消息，输入 `#`，能看到刚创建的文件。
- 选择该文件发送后，agent 的 prompt hint 指向 `/workspace/<path>`，agent 首次读取应使用 workspace 路径而不是 `/inputs/...`。
- 历史消息中该引用在正文内显示为与频道 artifact 一致的 inline file chip。
