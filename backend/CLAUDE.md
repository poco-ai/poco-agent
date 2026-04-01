[Root](../CLAUDE.md) > **backend**

# Backend Service

> FastAPI-based central API server with PostgreSQL persistence, session orchestration, and multi-provider LLM support.

## Changelog

| Date       | Action  | Summary                  |
| ---------- | ------- | ------------------------ |
| 2026-03-31 | Created | Initial module CLAUDE.md |

---

## Module Responsibilities

- REST API for all frontend operations (sessions, tasks, projects, capabilities, etc.)
- Session and Run lifecycle management (create, queue, track, complete)
- Callback endpoint for Executor Manager to persist execution results
- User configuration: skills, plugins, MCP servers, env vars, slash commands, sub-agents
- IM integration (Telegram, DingTalk, Feishu) for multi-end messaging
- Memory management (via mem0 + Neo4j + pgvector)
- Scheduled task and cron management
- Search (BM25-based) across sessions and messages
- Storage service (S3-compatible: RustFS, R2, etc.)
- Usage analytics and deliverable tracking

## Entry and Startup

- **Entry**: `app/main.py` -- `create_app()` factory -> FastAPI instance
- **Startup**: Lifespan handler in `app/lifecycle/lifespan.py`
- **Config**: `app/core/settings.py` -- Pydantic Settings, reads `.env`
- **Database**: `app/core/database.py` -- SQLAlchemy engine, `SessionLocal`, `Base`, `TimestampMixin`
- **Dependency Injection**: `app/core/deps.py` -- `get_db()`, `get_current_user_id()`, `require_internal_token()`

## API Interface

All endpoints under `/api/v1/`. Router registry in `app/api/v1/__init__.py`.

### Public Endpoints (frontend-facing)

| Domain                     | Router File                         | Key Operations                   |
| -------------------------- | ----------------------------------- | -------------------------------- |
| Sessions                   | `sessions.py`                       | CRUD, list by user/project       |
| Session Queue              | `session_queue.py`                  | Queue queries within a session   |
| Tasks                      | `tasks.py`                          | Create task (message + run)      |
| Runs                       | `runs.py`                           | List, get status                 |
| Messages                   | `messages.py`                       | List messages by session         |
| Callback                   | `callback.py`                       | Receive execution callbacks      |
| Projects                   | `projects.py`                       | CRUD, reorder                    |
| Attachments                | `attachments.py`                    | Upload files                     |
| Audio                      | `audio.py`                          | Speech-to-text                   |
| Memories                   | `memories.py`                       | CRUD                             |
| Search                     | `search.py`                         | Full-text search                 |
| MCP Servers                | `mcp_servers.py`                    | CRUD                             |
| Skills                     | `skills.py`, `skill_marketplace.py` | CRUD, marketplace                |
| Plugins                    | `plugins.py`                        | CRUD                             |
| Slash Commands             | `slash_commands.py`                 | CRUD                             |
| Sub-agents                 | `subagents.py`                      | CRUD                             |
| Env Vars                   | `env_vars.py`                       | CRUD                             |
| Claude MD                  | `claude_md.py`                      | User CLAUDE.md config            |
| Scheduled Tasks            | `scheduled_tasks.py`                | CRUD, cron                       |
| Tool Executions            | `tool_executions.py`                | List by session/run              |
| Usage                      | `usage.py`                          | Usage logs, analytics            |
| User Input Requests        | `user_input_requests.py`            | List, respond                    |
| Models                     | `models.py`                         | Available model list             |
| IM                         | `im.py`                             | Telegram/DingTalk/Feishu webhook |
| Deliverables               | `deliverables.py`                   | List by session                  |
| Capability Recommendations | `capability_recommendations.py`     | Suggest capabilities             |
| Pending Skill Creations    | `pending_skill_creations.py`        | Review AI-generated skills       |

### Internal Endpoints (Executor Manager -> Backend)

Prefixed with `internal_*`, secured by `X-Internal-Token` header:

- `internal_claude_md.py`, `internal_env_vars.py`, `internal_memories.py`
- `internal_mcp_config.py`, `internal_plugin_config.py`, `internal_skill_config.py`
- `internal_scheduled_tasks.py`, `internal_slash_commands.py`, `internal_subagents.py`
- `internal_user_input_requests.py`, `internal_skills.py`

## Key Dependencies and Configuration

**Dependencies** (from `pyproject.toml`):

- FastAPI, Uvicorn, SQLAlchemy 2.0, Alembic, Pydantic Settings
- PostgreSQL (psycopg2-binary)
- anthropic SDK, mem0ai, langchain-neo4j
- boto3 (S3), httpx, croniter, cryptography
- DingTalk/Lark SDKs for IM

**Configuration** (`app/core/settings.py`):

- `DATABASE_URL` -- PostgreSQL connection string
- `HOST` / `PORT` -- Service binding (default 0.0.0.0:8000)
- `CORS_ORIGINS` -- Allowed origins
- `SECRET_KEY`, `INTERNAL_API_TOKEN` -- Auth tokens
- `EXECUTOR_MANAGER_URL` -- Executor Manager service URL
- `BOOTSTRAP_ON_STARTUP` -- Auto-create DB tables on startup
- IM tokens: `TELEGRAM_BOT_TOKEN`, `DINGTALK_*`, `LARK_*`

## Data Model

SQLAlchemy models in `app/models/`. Key entities:

| Model                                                          | Table                                   | Description                                       |
| -------------------------------------------------------------- | --------------------------------------- | ------------------------------------------------- |
| `AgentSession`                                                 | `agent_sessions`                        | Chat/execution sessions, linked to user & project |
| `AgentRun`                                                     | `agent_runs`                            | Individual execution runs within a session        |
| `AgentMessage`                                                 | `agent_messages`                        | Chat messages (user/assistant/tool)               |
| `AgentScheduledTask`                                           | `agent_scheduled_tasks`                 | Cron-based recurring tasks                        |
| `AgentSessionQueueItem`                                        | `session_queue_items`                   | Queued queries within a session                   |
| `Project`                                                      | `projects`                              | User projects for organizing sessions             |
| `ToolExecution`                                                | `tool_executions`                       | Tool use records                                  |
| `UsageLog`                                                     | `usage_logs`                            | Token usage tracking                              |
| `UserInputRequest`                                             | `user_input_requests`                   | Pending user confirmations                        |
| `Skill`                                                        | `skills`                                | Custom skills                                     |
| `Plugin`                                                       | `plugins`                               | Plugin definitions                                |
| `McpServer`                                                    | `mcp_servers`                           | MCP server configs                                |
| `SlashCommand`                                                 | `slash_commands`                        | Custom slash commands                             |
| `SubAgent`                                                     | `sub_agents`                            | Sub-agent definitions                             |
| `UserEnvVar`                                                   | `user_env_vars`                         | Environment variables                             |
| `UserClaudeMdSetting`                                          | `user_claude_md_settings`               | User CLAUDE.md config                             |
| `Deliverable` / `DeliverableVersion`                           | `deliverables` / `deliverable_versions` | Task output artifacts                             |
| `MemoryCreateJob`                                              | `memory_create_jobs`                    | Async memory creation jobs                        |
| `UserModelProviderSetting`                                     | `user_model_provider_settings`          | Per-user model provider config                    |
| IM models: `Channel`, `ChannelDelivery`, `ImEventOutbox`, etc. | Embedded IM tables                      | Multi-end messaging                               |

**Migrations**: `alembic/` with 25+ migration files. Use `alembic revision --autogenerate` then review.

## Testing and Quality

- **Framework**: pytest with pytest-cov
- **Test directory**: `tests/`
- **28 test files** covering:
  - Services: `test_callback_service.py`, `test_session_service.py`, `test_task_service.py`, `test_model_config_service.py`, `test_deliverable_service.py`, etc.
  - Repositories: `test_session_repository.py`, `test_run_repository.py`, `test_project_repository.py`, etc.
  - IM: `test_im_providers.py`

## FAQ

**Q: How is auth handled?**
A: Currently placeholder -- `X-User-Id` header or `DEFAULT_USER_ID`. Internal APIs use `X-Internal-Token`.

**Q: How does the callback flow work?**
A: Executor Manager calls `/api/v1/callback` with structured payload -> `CallbackService` persists messages, tool executions, usage logs.

## Related Files

- `pyproject.toml` -- Dependencies and tool config
- `app/main.py` -- FastAPI app factory
- `app/core/settings.py` -- Configuration
- `app/core/database.py` -- SQLAlchemy setup
- `app/api/v1/__init__.py` -- All router registrations
- `app/models/__init__.py` -- All model imports
- `alembic/` -- Database migrations
- `tests/` -- Test suite
