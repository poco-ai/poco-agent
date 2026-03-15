## Poco IM Service (Standalone)

This service is used to:

- Start tasks, continue conversations, and answer AskQuestion/Plan Approval requests through IM platforms (currently Telegram / DingTalk / Feishu)
- Receive Backend push events and send IM notifications (completed / failed / input required)

Design goals:

- **Fully decoupled from the Backend database**: IM uses its own database (default: `sqlite:///./im.db`)
- **No impact on standalone Backend operation**: if IM is not enabled, the existing system continues to work as usual
- **Extensible across multiple IM platforms**: integrate different platforms through a unified message model and delivery gateway

### Run

From the `im/` directory:

```bash
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

### Environment Variables (Example)

```bash
# IM service
DATABASE_URL=sqlite:///./im.db
BACKEND_URL=http://localhost:8000
BACKEND_USER_ID=default
FRONTEND_PUBLIC_URL=http://localhost:3000
FRONTEND_DEFAULT_LANG=zh
BACKEND_EVENT_TOKEN=change-this-token

# Telegram
TELEGRAM_BOT_TOKEN=123:abc
TELEGRAM_WEBHOOK_SECRET_TOKEN=

# DingTalk
DINGTALK_ENABLED=true
DINGTALK_WEBHOOK_TOKEN=
# Stream mode (recommended for receiving messages, event push, and card callbacks; no public webhook required)
DINGTALK_STREAM_ENABLED=true
# Optional: subscribe to all events (EVENT topic="*"), default is false because the event volume can be high
DINGTALK_STREAM_SUBSCRIBE_EVENTS=false
# OpenAPI (recommended for proactive messages and notifications; does not depend on sessionWebhook)
DINGTALK_CLIENT_ID=
DINGTALK_CLIENT_SECRET=
DINGTALK_ROBOT_CODE=
DINGTALK_OPEN_BASE_URL=https://api.dingtalk.com
# Optional: fixed outbound-only webhook (fallback / notification use, usually a group custom bot webhook)
DINGTALK_WEBHOOK_URL=

# Feishu
FEISHU_ENABLED=false
FEISHU_STREAM_ENABLED=true
FEISHU_APP_ID=
FEISHU_APP_SECRET=
FEISHU_VERIFICATION_TOKEN=
FEISHU_BASE_URL=https://open.feishu.cn
```

### Webhook

- Telegram: `POST /api/v1/webhooks/telegram`
- DingTalk (optional in Webhook mode): `POST /api/v1/webhooks/dingtalk` (no public callback is needed when using Stream mode)
- Feishu (optional fallback in webhook mode): `POST /api/v1/webhooks/feishu`
- Backend internal events: `POST /api/v1/internal/backend-events`

To enable notifications, configure the Backend to dispatch IM events to this endpoint and
use the same `BACKEND_EVENT_TOKEN`.

Feishu notes:

- Use a self-built Feishu app with bot capability enabled
- Long connection is recommended and enabled by default with `FEISHU_STREAM_ENABLED=true`
- With long connection enabled, no public Feishu callback URL is required for inbound messages
- If you choose webhook mode instead, configure the event subscription callback URL to `POST /api/v1/webhooks/feishu`
- `FEISHU_VERIFICATION_TOKEN` is only needed for webhook mode
- Webhook mode currently supports plaintext callbacks only, so callback encryption must stay disabled

### IM Commands

- `/help`: Show the full command list
- `/list [n]`: Show recent sessions (default: 10)
- `/connect <session_id|index>`: Connect to a session (and subscribe automatically)
- `/new <task>`: Create a new session and connect automatically
- `/watch <session_id>`: Subscribe to a session
- `/watches`: Show all subscriptions
- `/unwatch <session_id|index>`: Cancel a subscription
- `/link`: Show the currently connected session
- `/clear`: Clear the current session binding
- `/answer <request_id> {...}`: Answer an AskQuestion request
- `/answer <request_id> {"approved":"true|false"}`: Answer a Plan Approval request

Plain text: if a session is currently connected, the message will be sent as a follow-up.

Tip: in a group chat, mentioning only `@bot` with no additional content will automatically return the command help (equivalent to `/help`).
