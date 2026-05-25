# 频道结构化 Mention 与上下文引用机制调研

## 元数据

| 字段 | 值 |
| --- | --- |
| 调研日期 | 2026-05-25 |
| 研究领域 | Server channel mention, shared artifacts, agent trigger protocol |
| 关联决策 | `specs/constitution/2026-05-05-channel-shared-context-and-artifacts.md`、`specs/constitution/2026-05-08-persistent-agent-message-passing-and-tool-injection.md`、`specs/constitution/2026-05-11-channel-task-collaboration-model.md` |
| 文档性质 | 主流交互模式调研与 Poco 改造建议 |

## 背景

当前频道聊天里的 `@` 机制已经承担了多种含义：

1. 在前端输入框中唤起 agent / human 成员候选项。
2. 在后端通过文本扫描 `@handle` 决定是否触发 agent。
3. 在消息渲染时把任意 `@token` 高亮成 mention 风格。

频道共享文件上传能力加入后，用户自然会希望在聊天过程中引用某个文件，例如“让 @agent 看一下 @design-doc”。如果继续只靠文本扫描，就会出现三个问题：

- `@xxx` 无法表达它到底是 agent 触发、人类用户通知、文件引用、任务引用，还是未来的工具/命令入口。
- 文件名、agent handle、人类 handle 可能冲突；即使不冲突，显示名和 handle 也可能随时间变化。
- agent 触发是有副作用的执行行为，文件引用只是上下文选择；把二者都压缩成纯文本 token 会让权限、审计和错误恢复都变弱。

本文调研主流 agent / chat 平台如何处理 mention 与上下文引用，并结合当前 Poco 实现提出改造建议。

## 调研范围

本次主要参考官方文档或一手开发者文档：

- Windsurf Chat：`@` 作为确定性上下文引入机制。
- Claude Code：交互式 CLI 中 `/`、`!`、`@` 的输入前缀分工。
- VS Code / GitHub Copilot Chat：`#` 用于上下文引用，`@` 用于 chat participant。
- Slack Developer Docs：用稳定 ID markup 表达 user/channel/group mention，并警告自动解析风险。
- Microsoft Bot Framework：message activity 使用 `entities` 数组携带 mention 等结构化上下文。

Cursor 也有类似 `@` 上下文符号的产品心智，但当前官方文档路径在本次验证时不可稳定获取，因此没有把它作为核心论据。

## 外部平台观察

### Windsurf：`@` 是确定性上下文选择

Windsurf Chat 把 `@-mention` 定义为把上下文显式带入对话的方式。可被 `@` 的对象包括函数、类、目录、文件、远端仓库、IDE terminal 内容，以及 `@diff` 这类特殊上下文项。

这个模型的关键点不是“扫描出一个字符串”，而是用户在输入时通过候选项选择了一个有类型的上下文对象。发送后该对象会被确定性地加入模型上下文。

对 Poco 的启发：

- 文件引用适合建模成“显式上下文选择”，不应该触发 agent。
- 如果继续允许 `@` 引用文件，候选项必须带 `kind=artifact` 和稳定 `artifact_id`，不能只发送 `@filename`。
- 对用户来说，mention 的 UI 可以统一；对系统来说，实体类型和动作必须分开。

### Claude Code：前缀负责不同交互模式

Claude Code 在交互式输入中使用不同前缀区分意图：

- `/` 位于开头时进入 command / skill 菜单。
- `!` 位于开头时进入 shell mode。
- `@` 用于 file path mention，并触发文件路径补全。

Claude Code 的场景是单用户本地 CLI。`@path` 的歧义较小，因为它主要面向当前工作目录中的文件路径；同时命令、shell、文件引用被拆到了不同输入模式里。

对 Poco 的启发：

- Poco 是多人频道和持久 agent 场景，`@token` 的歧义比本地 CLI 高很多。
- 即使选择保留 `@文件` 的体验，也不能照搬 CLI 的纯路径语义；必须落到结构化实体和权限校验。
- 命令类入口应继续独立于 mention，例如未来用 `/` 承载频道命令、agent 操作或系统动作。

### VS Code / GitHub Copilot Chat：`#` 引用上下文，`@` 选择参与者

VS Code Copilot Chat 明确把两类入口分开：

- `#-mentions` 用于加入上下文项，包括文件、文件夹、符号、工具、terminal 输出、source control changes 等。
- `@-mentions` 用于调用 chat participant，例如 `@vscode`、`@terminal` 这类领域助手。

这个设计很适合 Poco 当前的问题：agent 是“参与者/执行者”，文件是“上下文对象”。二者都可以在输入框里被搜索，但触发后的行为完全不同。

对 Poco 的启发：

- 最推荐的产品语义是：`@` 只保留给 human / agent / chat participant；文件、任务、共享 artifact 用 `#` 或独立 Add Context picker。
- 如果短期不想改变用户“艾特文件”的说法，也应该在系统层把文件实体标记为 `reference`，而不是 `mention trigger`。
- `#` 还能与未来 `#task-123`、`#artifact`、`#thread` 这类引用入口自然扩展。

### Slack：mention 使用稳定 ID，并避免自动解析用户输入

Slack app 消息中提到用户时使用类似 `<@U012AB3CD>` 的稳定 ID markup；频道引用使用 `<#C123ABC456>`；特殊通知使用 `<!here>` 等显式格式。Slack 文档还提醒，自动解析用户输入可能把普通文本里的 `@everyone` 变成真实通知，从而产生意外副作用。

对 Poco 的启发：

- 触发 agent 与通知用户都属于副作用行为，必须基于稳定 ID 和显式实体，而不是名字扫描。
- 渲染层可以展示最新 display name，但存储层要保留当时选择的 target id 和 fallback display text。
- 后端应该避免对新消息做无条件 regex 自动触发；regex 只能作为旧消息兼容路径。

### Microsoft Bot Framework：message text 与 entities 分离

Bot Framework 的 activity message 支持 `entities` 数组。mention entity 会携带 entity type、被 mention 的账号对象，以及 message text 中代表该 mention 的文本片段。文档还建议 bot 在判断用户真实意图时可以忽略 mention 本身那段文本。

对 Poco 的启发：

- `content.text` 负责人类可读文本；`content.entities` 负责机器可执行语义。
- 是否触发 agent、通知用户、引用文件、携带地理位置或其它上下文，都应该由 `entities` 表达。
- agent prompt 构建时可以把 mention 文本和引用实体分开处理，避免模型把“@agent”本身误解为用户意图的一部分。

## 模式总结

主流平台在细节上不完全一致，但方向比较一致：

1. **UI 前缀只是唤起机制，不是最终协议。** 用户输入 `@`、`#`、`/` 后选择候选项；系统存储的是候选项的类型、ID 和动作。
2. **副作用行为必须显式。** 通知用户、触发 agent、执行命令都不能只靠自由文本里看起来像 mention 的 token。
3. **上下文引用与执行者选择需要分离。** 文件、目录、网页、任务属于 context reference；agent / participant 属于 actor routing。
4. **渲染和路由不要共享同一套 regex。** 渲染可以对旧文本做 fallback 高亮，但路由应读取结构化实体。
5. **稳定 ID 优先于 handle/display name。** handle 是用户体验层，不能作为唯一事实源。

## 当前 Poco 实现观察

### 前端输入层

当前 mention 候选类型定义在 `frontend/features/servers/lib/server-conversation-view.ts`：

```ts
type MentionCandidate = {
  id: string;
  label: string;
  handle: string;
  kind: "agent" | "human";
  description?: string | null;
};
```

输入框使用类似 `/(?:^|\s)@([^\s@]*)$/u` 的正则检测正在输入的 mention token，然后组合 agent 和 human 候选项。选择候选项后，只把 `@handle` 或 `@label` 插入到普通文本里，没有同步创建结构化 mention 数据。

这里存在一个隐藏风险：agent 插入文本时会优先使用无空格的 display label，否则才使用 handle；但后端触发匹配的是 agent handle。这会导致某些 display name 与 handle 不一致的 agent 被插入后无法触发。

线程回复抽屉里也复制了一套相似逻辑，后续改造需要避免继续双写。

### 前端消息渲染

`frontend/features/servers/ui/server-message-content.tsx` 当前使用正则把任意 `@token` 高亮。这个逻辑不解析实体，也不知道 token 指向 agent、人类用户、文件还是普通文本。

因此它只能提供视觉高亮，不能支撑 hover 卡片、权限提示、文件预览、agent profile 或可靠跳转。

### 消息发送协议

`frontend/features/servers/api/servers-api.ts` 的 `sendMessage()` 发送的是：

```json
{
  "message_type": "user",
  "text_preview": "...",
  "content": {
    "text": "...",
    "attachments": [],
    "as_task": false
  }
}
```

协议里没有 `mentions`、`entities` 或 `references` 字段。上传共享文件后返回的 attachment 有 `id`，但这个 id 只作为附件存在，没有被表达为“本条消息引用了该 artifact”。

### 后端触发层

`backend/app/services/server_agent_trigger_service.py` 当前使用后端 regex 从 `content.text` 或 `text_preview` 中提取 `@handle`，再与频道内 active agent membership 的 handle 做大小写不敏感匹配。

这个逻辑目前有两个优点：

- 对旧消息和纯文本输入兼容性好。
- 多个 `@agent` 可以自然触发多个 agent。

但它已经不适合作为正式协议：

- 无法区分 `@agent` 与 `@file`。
- 无法表达人类 mention、artifact reference、task reference 等非触发实体。
- 无法记录用户在发送时到底选择了哪个对象。
- 未来如果 display name、handle 或 file name 变化，历史消息语义不可恢复。

### 共享 artifact 与触发上下文

Poco 已经有很好的基础，不需要从零开始：

- `AgentTriggerEnvelope.references` 已经支持 `message_ids`、`artifact_ids`、`task_ids`。
- channel runtime tools 已经支持 agent 使用 `list_channel_artifacts`、`read_channel_artifact`、`search_channel_artifacts`。
- agent collaboration 工具已经能传 `reference_artifact_ids`。
- constitution 中已经明确 channel DB 是共享上下文事实源，artifact 应通过 id / logical path / metadata 被引用，内容按需读取。

现在的缺口是：用户在频道消息里选择的 artifact 没有被结构化写入 message content，也没有进入 trigger envelope 的 `references.artifact_ids`。

## 目标模型建议

建议把频道消息中的 mention / reference / command 统一建模成 **message entity**。短期可以直接放在 `server_channel_messages.content.entities`，等查询、通知和审计需求变强后再拆成独立表。

建议的前端/协议形态如下：

```ts
type ChannelMessageEntityKind =
  | "agent"
  | "user"
  | "artifact"
  | "task"
  | "channel"
  | "command";

type ChannelMessageEntityAction =
  | "trigger"
  | "mention"
  | "reference"
  | "invoke";

type ChannelMessageEntity = {
  id: string;
  kind: ChannelMessageEntityKind;
  action: ChannelMessageEntityAction;
  targetId: string;
  displayText: string;
  insertedText: string;
  range?: {
    start: number;
    end: number;
  };
  metadata?: {
    handle?: string;
    logicalPath?: string;
    sourceKind?: string;
    mimeType?: string | null;
  };
};
```

字段语义：

- `kind` 表达目标类型，例如 agent、user、artifact。
- `action` 表达本条消息想做什么，例如 trigger agent、mention human、reference artifact。
- `targetId` 是后端事实源 ID，例如 `agent_identity_id`、`user_id`、`artifact_id`。
- `displayText` 是发送时的展示快照，用于历史消息 fallback。
- `insertedText` 是文本框中插入的可读 token，例如 `@alice`、`#design-doc.md`。
- `range` 只用于渲染定位和编辑器体验，不应作为后端事实源。
- `metadata` 只保存低风险辅助信息，权限和对象存在性仍由后端校验。

如果后续需要更强的查询能力，可以增加表：

```text
server_channel_message_entities
- id
- message_id
- kind
- action
- target_id
- display_text
- inserted_text
- range_start
- range_end
- metadata_json
- created_at
```

短期不建议先上独立表。当前更重要的是先把发送协议和触发逻辑从 regex 迁到 entity-first。

## 路由语义建议

建议明确以下规则：

| Entity | Action | 行为 |
| --- | --- | --- |
| `kind="agent"` | `action="trigger"` | 后端校验 agent 是频道 active member 后触发该 agent |
| `kind="user"` | `action="mention"` | 仅用于人类用户通知、渲染、hover profile，不触发 agent |
| `kind="artifact"` | `action="reference"` | 写入 trigger envelope 的 `references.artifact_ids`，不触发 agent |
| `kind="task"` | `action="reference"` | 写入 `references.task_ids`，不触发 agent |
| `kind="command"` | `action="invoke"` | 未来频道命令入口；需要单独权限和命令 schema |

直接私信 agent 的语义不需要依赖文本 mention：direct channel 仍然由 `direct_agent_identity_id` 决定目标 agent。

对于新消息：

- 如果存在 `content.entities`，后端触发只读取结构化实体。
- 如果不存在 `content.entities`，才走旧的 `@handle` regex 兼容逻辑。
- 如果存在实体但文本里还有额外 `@token`，额外 token 不应自动触发 agent；最多作为普通文本或 unresolved mention 渲染。

这个规则能避免“用户说了一个文件名或普通 @token，却意外触发 agent”的问题。

## 前缀与交互建议

### 推荐方案：`@` 给参与者，`#` 给上下文

最干净的交互模型是参考 VS Code：

- `@`：agent / human / chat participant。
- `#`：artifact / file / task / thread / code symbol / context。
- `/`：频道命令或 agent 操作。

这种设计的优点是语义稳定，未来扩展空间足够大。用户想“艾特文件”时，产品文案可以叫“引用文件”，交互上使用 `#` 或 Add Context 按钮。这样不会把“触发一个执行者”和“给执行者看一个对象”混在一起。

### 兼容方案：继续 `@`，但必须分组和结构化

如果短期希望保留 `@文件` 的心智，也可以让 `@` 候选菜单分组展示：

```text
Agents
Humans
Files
Tasks
```

但选择 `Files` 里的候选项时，前端必须创建 `kind="artifact", action="reference"` 的实体。后端不能根据 `@filename` 自己猜测文件。

这个方案对已有用户更顺，但长期会让 `@` 菜单变重。尤其当 agent、成员、文件、任务、工具都放进同一个候选列表时，搜索排序和权限提示会变得复杂。

### 文件引用的候选来源

建议分两层做：

1. **已上传到当前草稿的附件。** 上传接口已经返回 `InputFile.id`，可以直接创建 artifact reference entity。
2. **频道已有共享 artifacts。** 当前树形文件节点面向 UI 浏览，叶子节点还不稳定暴露 `artifact_id`；需要扩展文件树节点或增加 flat list/search API，让前端能拿到 `artifact_id`、`logical_path`、`mime_type`、`source_kind`。

对于同名文件，候选项必须展示路径或来源，例如：

```text
design.md
/Uploads/design.md

design.md
/Exports/run-123/design.md
```

发送时以 `artifact_id` 为准，`logical_path` 只作为展示和模型提示辅助。

## 对当前项目的改造建议

### 1. 消息协议先支持 `content.entities`

在 `backend/app/schemas/server_channel_message.py` 和前端 message DTO 中加入 `entities`。不要直接新增顶层 `mentions` 字段，原因是这些对象不都是 mention；artifact 和 task 更准确地说是 reference。

建议请求体允许：

```json
{
  "content": {
    "text": "请 @frontend-agent 看一下 #design.md",
    "attachments": [],
    "entities": [
      {
        "kind": "agent",
        "action": "trigger",
        "targetId": "agent-uuid",
        "displayText": "Frontend Agent",
        "insertedText": "@frontend-agent"
      },
      {
        "kind": "artifact",
        "action": "reference",
        "targetId": "artifact-uuid",
        "displayText": "design.md",
        "insertedText": "#design.md",
        "metadata": {
          "logicalPath": "/Uploads/design.md",
          "mimeType": "text/markdown"
        }
      }
    ]
  }
}
```

后端保存前要做 canonicalization：

- agent entity：确认 agent 存在且是该 server/channel 的 active member。
- user entity：确认用户是 server/channel 可见成员，或按产品规则允许跨 server mention。
- artifact entity：确认 artifact 属于当前 channel，且当前发送者可见。
- task entity：确认 task 与当前 server/channel 关联。
- command entity：短期可以拒绝或忽略，等命令系统设计完成再启用。

保存时可以保留前端传入的 `displayText` 作为历史快照，但 `metadata` 应由后端补齐或清洗，避免前端伪造敏感信息。

### 2. 后端触发改成 entity-first

`ServerAgentTriggerService._collect_target_agents()` 应改成：

1. direct channel：继续使用 `direct_agent_identity_id`。
2. channel message with entities：只读取 `kind="agent" && action="trigger"` 的实体。
3. channel message without entities：走当前 regex `@handle` 兼容旧消息。

这样可以保留已有文本 mention 行为，又让新消息不会被额外 `@token` 意外触发。

同时需要从 entities 收集引用：

```text
artifact_ids = entities where kind == artifact and action == reference
task_ids = entities where kind == task and action == reference
message_ids = 当前触发消息 id + 显式引用消息 id
```

`ChannelSharedContextService.build_trigger_envelope()` 当前只填当前 message id，建议扩展为把结构化 reference 一并写入 `TriggerReferences`。executor prompt 已经理解 `reference_artifact_ids`，channel runtime tools 也已能按 id 读取 artifact，因此这一步能直接把“频道里提到的文件”传给 agent。

### 3. 前端输入状态维护 draft entities

当前 textarea 只有 `draftText`。建议加：

```ts
const [draftEntities, setDraftEntities] = useState<ChannelMessageEntity[]>([]);
```

候选项选择后：

- 插入可读 token 到 `draftText`。
- 同步追加对应 entity。
- 如果用户删除或编辑了 token，前端应删除或标记该 entity 为 stale。

如果继续使用纯 textarea，range 维护会比较脆弱。短期可以采取保守策略：

- 只在发送时保留仍能在文本中找到 `insertedText` 的 entity。
- 找不到时丢弃该 entity，避免后端执行错误对象。
- 同名 token 多次出现时按选择时记录的范围尽量匹配；匹配失败就要求用户重新选择。

中期可以考虑 chip editor：候选项插入后成为可删除的 inline chip，底层再序列化成文本 + entities。这样最适合 hover card、文件 preview 和稳定删除体验。

### 4. 候选项模型扩展并去重

当前 `MentionCandidate.kind` 只有 `agent | human`。建议抽成通用 picker candidate：

```ts
type ChannelReferenceCandidate = {
  id: string;
  kind: "agent" | "user" | "artifact" | "task";
  action: "trigger" | "mention" | "reference";
  label: string;
  handle?: string;
  subtitle?: string;
  description?: string | null;
  icon?: string;
  insertedText: string;
  metadata?: Record<string, unknown>;
};
```

如果采用推荐方案，可以实现两个 picker：

- `@` picker：只返回 agent / user。
- `#` picker：返回 artifact / task / thread 等 context reference。

如果采用兼容方案，一个 picker 里也要按 group 分区，不要只靠排序混在一起。

### 5. 消息渲染使用 entities，而不是只扫文本

`server-message-content.tsx` 应优先读取 `content.entities` 渲染：

- agent trigger：显示 agent mention，hover 展示 agent 名称、描述、加入时间、状态；点击沿用当前跳转到 agent 详情。
- user mention：显示用户 mention，hover 展示名称、加入时间或 server role；点击打开用户资料或保持当前行为。
- artifact reference：显示文件 chip，hover 展示文件名、logical path、大小、mime type、上传者、上传时间；点击打开 artifact preview 或下载。
- unresolved entity：显示 fallback `displayText`，并给出“对象已删除/无权限”的弱提示。

旧消息没有 entities 时，仍然可以用 regex 做轻量高亮，但不应该给它触发级语义。

### 6. 文件列表 API 暴露 artifact id

上传附件已经能返回 `InputFile.id`，但频道已有共享文件的树形节点需要能被 picker 使用。建议二选一：

1. 扩展 `FileNode` 叶子节点，增加 `artifactId`、`logicalPath`、`sourceKind`、`mimeType`、`sizeBytes`。
2. 新增 `GET /servers/{server_id}/channels/{channel_id}/artifacts/search?q=`，返回 flat artifact summary。

更推荐第二种，因为 picker 本质是搜索候选，不是树浏览；可以同时服务 `#` 输入、Add Context 弹窗和未来文件 quick switch。

### 7. 兼容策略

为了避免一次性破坏现有体验，建议按以下规则兼容：

- 旧消息没有 `content.entities`：渲染继续 regex 高亮；后端触发继续 regex `@handle`。
- 新消息有 `content.entities`：后端只相信 entities，不额外扫描文本触发。
- 前端暂时仍可插入 `@handle` 文本，但同时发送 entity。
- 后端发现 entity 不合法时，推荐 400 拒绝发送，而不是静默降级为纯文本；否则用户会以为 agent/file 被成功引用。

## 渐进落地路径

建议分四步推进：

1. **协议与后端 entity-first。** 给消息 content 加 `entities`，后端校验并保存；触发链路优先读 entity，regex 只兼容无 entity 旧消息。
2. **agent / human mention 先结构化。** 现有 `@` picker 不改变视觉，但选择候选项时生成 entity；顺手修复 agent 插入 display label 导致 handle 不匹配的问题。
3. **文件 reference 接入。** 先支持草稿已上传附件引用，再接入频道已有 artifact search/list；引用文件进入 `references.artifact_ids`。
4. **渲染与 hover card。** 用 entity 驱动消息 mention 渲染、agent/user hover card、artifact hover card；旧 regex 渲染保留为 fallback。

这条路径能先解决“误触发”和“文件引用进不了 agent 上下文”的核心问题，再补完整交互细节。

## 验证建议

### 后端测试

需要覆盖：

- 发送文本 `@some-file` 但没有 agent entity 时，不触发 agent。
- 发送 `kind=agent/action=trigger` entity 时，触发对应 agent。
- 发送 `kind=artifact/action=reference` entity 时，trigger envelope 包含 `artifact_ids`。
- 新消息同时有合法 entity 和额外 `@other-agent` 文本时，只触发 entity 指定 agent。
- 旧消息没有 entities 时，现有 `@handle` regex 仍能触发。
- entity 指向不在当前 channel 的 artifact / agent 时，发送失败。

### 前端测试

需要覆盖：

- 选择 agent 候选项后，payload 中包含 `kind=agent/action=trigger/targetId`。
- 选择文件候选项后，payload 中包含 `kind=artifact/action=reference/targetId`，且不触发 agent 语义。
- 删除已插入 token 后，对应 entity 不再发送。
- message content 优先按 entities 渲染，旧文本消息仍 fallback 高亮。
- agent/user/avatar hover card 与点击跳转互不冲突。

## 风险与开放问题

- **textarea range 维护脆弱。** 纯文本编辑器很难稳定维护实体范围；短期可发送前校验，长期建议引入 inline chip。
- **`#` 与 task 编号可能冲突。** constitution 中已有 `#42` 作为任务编号展示的语义。如果用 `#` 做 context picker，需要定义 `#task-42`、`#artifact` 或候选选择后的展示格式。
- **多 agent 触发是否保持。** 当前 regex 可触发多个 agent。结构化实体可以保留多目标，但 UI 上需要清晰展示“本条消息会触发 N 个 agent”。
- **权限变化后的历史消息。** 历史 entity 的 target 可能被删除或当前用户失去权限；渲染层应显示 fallback 快照，并弱化交互。
- **通知与执行审计。** human mention 未来如果产生通知，需要单独记录 delivery 状态；不要和 agent trigger 的 run 状态混用。

## 建议结论

Poco 不应继续把 `@token` 文本扫描作为频道 mention 的主协议。更稳妥的方向是：

1. 把 mention / reference / command 统一抽象成 `content.entities`。
2. 明确 `agent trigger`、`human mention`、`artifact reference`、`task reference` 的不同动作。
3. 后端触发链路 entity-first，regex 只兼容旧消息。
4. UI 上优先采用 `@` 选择参与者、`#` 选择上下文；如果保留 `@文件`，也必须在候选项选择时写入结构化 artifact entity。
5. 把 artifact reference 接入 `AgentTriggerEnvelope.references.artifact_ids`，复用已经存在的 channel runtime artifact tools。

这样改造后，上传共享文件、频道中引用文件、触发 agent、hover 查看人/agent/文件信息会共用同一套实体协议，而不是继续堆叠多套文本扫描规则。

## 参考资料

- Windsurf Chat Overview: <https://docs.windsurf.com/chat/overview>
- Windsurf Web and Docs Search: <https://docs.windsurf.com/windsurf/cascade/web-search>
- Claude Code Interactive Mode: <https://code.claude.com/docs/en/interactive-mode>
- Claude Code Common Workflows: <https://code.claude.com/docs/en/common-workflows>
- VS Code Copilot Chat Context: <https://code.visualstudio.com/docs/copilot/chat/copilot-chat-context>
- Slack Developer Docs, Formatting Message Text: <https://docs.slack.dev/messaging/formatting-message-text/>
- Microsoft Bot Framework, Entities and Activity Types: <https://learn.microsoft.com/en-us/azure/bot-service/bot-service-activities-entities?view=azure-bot-service-4.0>
