# 普通聊天分享与频道 Thread 投影决策

## 元数据

| 字段 | 值 |
| --- | --- |
| **决策日期** | 2026-06-09 |
| **关联 spec** | `specs/active/32-chat-share-link-and-channel-thread-projection-plan.md` |
| **关联决策** | `2026-05-05-channel-shared-context-and-artifacts.md`、`2026-05-25-structured-channel-mentions-and-context-references.md` |

## 决策摘要

Poco 的普通聊天分享采用两条不同语义：

- **Share link**：生成只读会话快照链接。其他用户打开后只能查看；如需继续，必须 fork 到自己的普通聊天。
- **Share to channel**：把普通聊天投影成频道中的一个 topic/thread。频道主消息来自普通聊天第一条用户输入，后续 transcript 进入 thread，频道内后续交互继续使用原有 channel/thread 语义。

分享不是运行态迁移。普通聊天的 live workspace、SDK session、local mount 和用户私有权限不会因为分享而进入频道或他人账号。

2026-06-09 review 后补充：share link 的页面形态不是独立的全屏阅读页，而是普通聊天区域的只读变体。已登录用户打开 share link 时应尽量保留应用 shell，让只读 transcript 替换普通聊天区；匿名用户仍可查看同一只读聊天区，但不能直接 fork。

## 背景

当前普通聊天只有前端导出图片能力，适合传播截图，但不适合让其他用户查看完整上下文、fork 继续，也不适合沉淀到频道协作流中。

频道侧已经具备 thread、event、shared artifacts、structured entities 和 channel runtime tools。把普通聊天导入频道时，最自然的形态不是复制一个私有聊天入口，而是在频道中创建一个可被成员讨论和引用的 thread。

## 最终决策

- **产品决策**：
  - 普通聊天 share link 打开后展示普通聊天区的只读变体，而不是脱离 app shell 的全屏页面。
  - 只读页面允许当前登录用户 fork 到自己的普通聊天中继续；匿名用户可查看，但 fork 动作必须隐藏或禁用，不能触发用户信息缺失错误。
  - 分享到频道默认不触发 agent，不创建 channel run。
  - 分享到频道会写入一条 channel event，并创建一个 thread projection。
  - 频道 thread 和频道右侧区域都显示对应 timeline，帮助定位 turn/run/artifact。
  - 分享到频道的 `conversation.shared` event 必须显示人类可读用户名，不得把 user id 当作 actor label。
  - 频道 thread 中导入的普通聊天 transcript 应展示原消息正文；`user` / `assistant` 只作为来源元数据，不作为正文 fallback。
  - 暂不提供通用 `Copy to my chats` 作为频道 thread 的主动作；如未来需要 private follow-up，必须显式去除 channel runtime tools，并只复制 transcript summary 与选定 artifacts。
- **技术决策**：
  - 新增 share link 持久化对象，使用不可猜测 token 作为只读入口。
  - share link fork 复用普通聊天 branch/copy 语义，但 fork 后 owner 变成当前用户，且不继承原 SDK session。
  - channel projection 使用独立 import service 直接创建 `server_channel_messages`，不调用 `send_message()` 和 agent trigger 链路。
  - imported user turns 可以使用 `message_type="user"`，但必须带 `content.source="imported_chat_session"`；import service 不触发 agent。
  - imported assistant turns 使用 `message_type="system"` + `content.source="imported_agent_session"`。
  - 分享到频道产生 `message_type="event"` + `event_type="conversation.shared"`，作为审计和频道时间线提示。

## 不变量

- Share link 是快照入口，不是原会话的实时镜像。
- Fork 到普通聊天后不会保留 channel runtime tools。
- Share to channel 只能由原普通聊天 share owner 执行；share link 接收者需要先 fork，才能以自己的聊天再次分享。
- Share to channel 不会把普通聊天的 local mount、persistent state、private workspace 原样暴露给频道。
- 频道可见文件仍以 `published artifacts` 为边界；thread 只引用或展示已发布 artifacts。
- 导入 transcript 中出现的 `@agent` 不得被解释为 trigger entity。
- Timeline 是导航和证据视图，不是新的消息事实源。
- Share link 只读页的重新生成、新建分支、编辑、输入框等写操作必须不可用。
- Share link 的 fork 入口只对已登录用户可见或可用；匿名查看不得要求注册，也不得在点击 fork 后报错。
- Channel event 的 actor label 必须来自用户显示名、邮箱或其他可读 fallback，而不是裸 user id。
- Imported thread message 的正文必须来自原普通聊天消息内容；抽取失败时允许使用空态/截断提示，但不得显示 `User`、`Assistant` 这类角色名作为正文。

## 关键用户叙事

### 只读分享

1. Alice 在普通聊天点击 Share。
2. 系统生成 share link。
3. Bob 打开链接，只读查看 transcript、runs、artifacts 和 timeline。
4. 如果 Bob 已登录，Bob 可以点击 Fork，系统创建属于 Bob 的普通聊天副本，之后 Bob 在自己的聊天中继续。
5. 如果 Bob 未登录，Bob 可以继续只读查看；fork 入口不显示或保持禁用。

### 分享到频道

1. Alice 在普通聊天点击 Share to channel。
2. 系统让 Alice 选择 server/channel 和标题。
3. 频道中出现一条 `conversation.shared` event。
4. 频道主消息显示普通聊天第一条用户输入和来源摘要。
5. Thread 中展示完整 transcript，右侧 timeline 可跳转消息、run 和 artifact。
6. 频道成员在 thread 中继续回复；如果他们 `@agent`，才按频道原有语义触发 agent。

## 暂不采用的方案

| 方案 | 不采用原因 |
| --- | --- |
| 分享时默认 fork | 会在只想展示成果的场景制造多余 private session 和双真相源 |
| 频道 thread 通用 Copy to my chats | 需要决定是否复制 channel tools、artifacts 和 workspace，语义复杂且容易权限污染 |
| Share to channel 走普通 send_message | `message_type="user"` 会触发 agent，无法保证导入 transcript 时不误触发 |
| 把频道 artifacts 当普通聊天文件树复用 | channel artifact 是频道协作资源，普通聊天 input/workspace 是个人执行资源，边界不同 |
