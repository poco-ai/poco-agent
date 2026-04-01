[Root](../CLAUDE.md) > **executor**

# Executor Service

> Agent execution engine running Claude Agent SDK with a hook-based extensibility system. Runs inside Docker containers managed by Executor Manager.

## Changelog

| Date       | Action  | Summary                  |
| ---------- | ------- | ------------------------ |
| 2026-03-31 | Created | Initial module CLAUDE.md |

---

## Module Responsibilities

- Execute AI agent tasks using Claude Agent SDK (`claude-agent-sdk`)
- Manage workspace (clone repos, stage files)
- Provide hook-based extensibility for callbacks, computer use, memory, todo tracking
- Send progress callbacks to Executor Manager during execution
- Handle browser/computer use tool execution
- User input requests (permissions, confirmations)
- Git platform operations (GitHub, GitLab)

## Entry and Startup

- **Entry**: `app/main.py` -- FastAPI app on port 8080
- **Core Engine**: `app/core/engine.py` -- `AgentExecutor` class
- **Config**: Environment variables (inherited from Executor Manager container)

## API Interface

All endpoints under `/api/v1/`. Single router: `app/api/v1/task.py`.

| Endpoint            | Description                    |
| ------------------- | ------------------------------ |
| `POST /api/v1/task` | Receive task execution request |
| `GET /health`       | Health check                   |

The task endpoint receives a `TaskConfig` with session ID, prompt, model config, hooks, workspace info, and callback URL.

## Key Architecture: Hook System

The hook system provides plugin-based extensibility during agent execution.

**Base**: `app/hooks/base.py`

- `AgentHook` (ABC) with lifecycle methods: `on_setup`, `on_agent_response`, `on_teardown`, `on_error`
- `ExecutionContext` carries session ID, working directory, and current state

**Manager**: `app/hooks/manager.py`

- `HookManager` orchestrates hook execution in sequence (teardown in reverse)

**Built-in Hooks**:

| Hook            | File              | Purpose                                     |
| --------------- | ----------------- | ------------------------------------------- |
| CallbackHook    | `callback.py`     | Send progress callbacks to Executor Manager |
| ComputerHook    | `computer.py`     | Browser/computer use tool execution         |
| TodoHook        | `todo.py`         | Track todo list progress                    |
| WorkspaceHook   | `workspace.py`    | Workspace file operations                   |
| RunSnapshotHook | `run_snapshot.py` | Capture run state snapshots                 |

## Key Dependencies and Configuration

**Dependencies** (from `pyproject.toml`):

- `claude-agent-sdk==0.1.48` -- Core AI agent SDK
- FastAPI, httpx, SQLAlchemy, uvicorn, websockets

**Environment** (set by Executor Manager):

- `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` -- LLM provider credentials
- `ANTHROPIC_BASE_URL` -- API base URL
- `DEFAULT_MODEL` -- Model to use
- Workspace mount paths

## Core Components

### AgentExecutor (`app/core/engine.py`)

The main engine that:

1. Creates a `ClaudeSDKClient` with configured options
2. Sets up `HookManager` with selected hooks
3. Manages execution context with session ID, trace IDs
4. Handles environment variable overrides for multi-provider support
5. Supports sub-agent spawning

### WorkspaceManager (`app/core/workspace.py`)

Manages workspace directories for task execution.

### Memory (`app/core/memory.py`)

Integration with mem0 for persistent agent memory across sessions.

### User Input (`app/core/user_input.py`)

Handles permission requests and user confirmations during execution.

### Prompts (`app/prompts/`)

- `prompt_append.py` -- Build prompt appendix with context, instructions

### Git Utils (`app/utils/git/`)

- `base.py` -- `BaseGitClient` abstract class
- `github.py` -- GitHub API client
- `gitlab.py` -- GitLab API client
- `operations.py` -- Git operations (clone, branch, etc.)

### Browser (`app/utils/browser.py`)

Viewport size parsing and formatting for computer use.

## Data Model / Schemas

All schemas in `app/schemas/`:

| Schema File   | Purpose                                                     |
| ------------- | ----------------------------------------------------------- |
| `request.py`  | Task execution request (`TaskConfig`)                       |
| `response.py` | Standardized response wrapper                               |
| `callback.py` | Callback payload structures                                 |
| `state.py`    | Agent execution state (`AgentCurrentState`, `BrowserState`) |
| `enums.py`    | Status and type enumerations                                |

## Testing and Quality

- **Framework**: pytest + pytest-asyncio + pytest-cov
- **Test directory**: `tests/`
- **3 test files**:
  - `test_engine.py` -- AgentExecutor tests
  - `test_workspace.py` -- Workspace management tests
  - `test_prompt_append.py` -- Prompt building tests

## FAQ

**Q: How does multi-provider support work?**
A: `ConfigResolver` in Executor Manager resolves provider credentials and sets environment variables before spawning the executor container. The executor reads `ANTHROPIC_API_KEY` and `ANTHROPIC_BASE_URL` regardless of actual provider.

**Q: Can the executor run standalone?**
A: Yes, but it's designed to run inside a Docker container managed by Executor Manager. For local dev, run directly with `uvicorn app.main:app --reload --port 8080`.

## Related Files

- `pyproject.toml` -- Dependencies
- `app/main.py` -- FastAPI app
- `app/core/engine.py` -- Core execution engine
- `app/hooks/` -- Hook system
- `app/schemas/` -- Data schemas
- `app/utils/git/` -- Git platform clients
- `tests/` -- Test suite
