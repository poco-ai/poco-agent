## Poco IM 服务（独立）

该服务用于：

- 通过 IM（当前实现：Telegram / 飞书 / 钉钉）发起任务、续聊、回答 AskQuestion/Plan Approval
- 通过轮询 Backend 的公开 API 发送通知（完成/失败/需要输入）

设计目标：

- **与 Backend 数据库完全解耦**：IM 使用独立数据库（默认 `sqlite:///./im.db`）
- **Backend 单独运行不受影响**：不启用 IM 时，现有系统照常工作
- **多 IM 可扩展**：通过统一消息模型和发送网关接入不同平台

### 运行

在 `im/` 目录：

```bash
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

### 环境变量（示例）

```bash
# IM service
DATABASE_URL=sqlite:///./im.db
BACKEND_URL=http://localhost:8000
BACKEND_USER_ID=default
FRONTEND_PUBLIC_URL=http://localhost:3000
FRONTEND_DEFAULT_LANG=zh

# Polling
POLL_USER_INPUT_INTERVAL_SECONDS=2
POLL_SESSIONS_RECENT_INTERVAL_SECONDS=5
POLL_SESSIONS_FULL_INTERVAL_SECONDS=300
POLL_HTTP_TIMEOUT_SECONDS=10

# Telegram
TELEGRAM_BOT_TOKEN=123:abc
TELEGRAM_WEBHOOK_SECRET_TOKEN=

# Feishu
FEISHU_ENABLED=true
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_VERIFICATION_TOKEN=
FEISHU_OPEN_BASE_URL=https://open.feishu.cn

# DingTalk
DINGTALK_ENABLED=true
DINGTALK_WEBHOOK_TOKEN=
DINGTALK_WEBHOOK_URL=
```

### Webhook

- Telegram: `POST /api/v1/webhooks/telegram`
- 飞书: `POST /api/v1/webhooks/feishu`
- 钉钉: `POST /api/v1/webhooks/dingtalk`

### IM 命令

- `/list [n]`：查看最近会话（默认 10 条）
- `/connect <session_id|序号>`：连接会话（会自动订阅）
- `/new <任务>`：创建新会话并自动连接
- `/watch <session_id>`：订阅某个会话
- `/unwatch <session_id>`：取消订阅
- `/subscribe all`：订阅当前用户全部会话
- `/unsubscribe all`：取消订阅全部会话
- `/link`：查看当前连接会话
- `/clear`：清除当前会话绑定
- `/answer <request_id> {...}`：回答 AskQuestion
- `/approve <request_id>` / `/reject <request_id>`：Plan Approval

普通文本：如果当前已连接会话，会作为续聊消息发送。
