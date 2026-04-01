[Root](../CLAUDE.md) > **executor_manager**

# Executor Manager Service

> Runtime dispatch, container pool management, polling, and callback forwarding service. Acts as the bridge between Backend (task queue) and Executor (task execution).

## Changelog

| Date       | Action  | Summary                  |
| ---------- | ------- | ------------------------ |
| 2026-03-31 | Created | Initial module CLAUDE.md |

---

## Module Responsibilities

- Pull queued runs from Backend's run queue and claim them
- Stage runtime assets (skills, plugins, attachments, claude.md, slash commands, sub-agents)
- Manage Docker container pool for executor instances
- Resolve model provider credentials and configuration
- Forward execution callbacks from Executor to Backend
- Schedule and dispatch cron-based recurring tasks
- Workspace lifecycle management (creation, cleanup, archival to S3)
- User input request forwarding
- Memory and computer use request forwarding

## Entry and Startup

- **Entry**: `app/main.py` -- `create_app()` factory -> FastAPI instance
- **Startup**: `app/core/lifespan.py` -- Starts APScheduler, container pool initialization
- **Config**: `app/core/settings.py` -- Pydantic Settings with extensive configuration
- **Scheduler**: `app/scheduler/` -- APScheduler configuration and task dispatchers

## API Interface

All endpoints under `/api/v1/`. Router registry in `app/api/v1/__init__.py`.

| Domain              | Router File              | Key Operations                   |
| ------------------- | ------------------------ | -------------------------------- |
| Tasks               | `tasks.py`               | Create, get status, cancel tasks |
| Executor            | `executor.py`            | Executor container management    |
| Callback            | `callback.py`            | Forward callbacks to Backend     |
| Computer            | `computer.py`            | Computer use forwarding          |
| Workspace           | `workspace.py`           | Workspace operations             |
| Skills Upload       | `skills_upload.py`       | Upload skill files               |
| Schedules           | `schedules.py`           | Schedule management              |
| User Input Requests | `user_input_requests.py` | Forward user input requests      |
| Memories            | `memories.py`            | Memory operations                |

## Key Architecture

### Task Dispatch Flow

1. `RunPullService` (`app/services/run_pull_service.py`) polls Backend for queued runs
2. `ConfigResolver` (`app/services/config_resolver.py`) resolves model provider credentials
3. Various stagers prepare runtime assets:
   - `SkillStager` -- Stage skill files
   - `PluginStager` -- Stage plugin configs
   - `AttachmentStager` -- Stage user attachments
   - `ClaudeMdStager` -- Stage CLAUDE.md content
   - `SlashCommandStager` -- Stage slash commands
   - `SubAgentStager` -- Stage sub-agent configs
4. `TaskDispatcher` (`app/scheduler/task_dispatcher.py`) claims the run, allocates container, sends task to Executor
5. `ContainerPool` (`app/services/container_pool.py`) manages Docker container lifecycle

### Scheduler System

- `app/scheduler/scheduler_config.py` -- APScheduler setup
- `app/scheduler/task_dispatcher.py` -- Main dispatch logic
- `app/scheduler/pull_job_registry.py` -- Registry of pull jobs per queue mode
- `app/scheduler/pull_schedule_config.py` -- Schedule configuration management
- `app/scheduler/pull_schedule_state.py` -- Schedule state tracking

### Pull Modes

Three queue-based pull modes:

- **Immediate** -- Real-time task dispatch (`TASK_PULL_IMMEDIATE_*`)
- **Scheduled** -- Cron-based dispatch (`TASK_PULL_SCHEDULED_*`)
- **Nightly** -- Off-peak batch processing (`TASK_PULL_NIGHTLY_*`)

## Key Dependencies and Configuration

**Dependencies** (from `pyproject.toml`):

- FastAPI, Uvicorn, Pydantic Settings
- APScheduler -- Job scheduling
- Docker SDK -- Container management
- boto3 -- S3-compatible storage
- httpx -- HTTP client

**Critical Configuration** (`app/core/settings.py`):

| Setting                                                             | Default                              | Description                         |
| ------------------------------------------------------------------- | ------------------------------------ | ----------------------------------- |
| `ANTHROPIC_API_KEY`                                                 | (required)                           | Anthropic API key                   |
| `DEFAULT_MODEL`                                                     | `claude-sonnet-4-20250514`           | Default LLM model                   |
| `BACKEND_URL`                                                       | `http://localhost:8000`              | Backend service URL                 |
| `CALLBACK_BASE_URL`                                                 | `http://localhost:8001`              | This service's URL for callbacks    |
| `MAX_EXECUTOR_CONTAINERS`                                           | 10                                   | Container pool limit                |
| `EXECUTOR_IMAGE`                                                    | `ghcr.io/poco-ai/poco-executor:lite` | Executor Docker image               |
| `EXECUTOR_BROWSER_IMAGE`                                            | `ghcr.io/poco-ai/poco-executor:full` | Browser-enabled executor image      |
| `WORKSPACE_ROOT`                                                    | `/var/lib/opencowork/workspaces`     | Workspace storage path              |
| `S3_*`                                                              | (varies)                             | S3-compatible storage config        |
| `TASK_PULL_*`                                                       | (varies)                             | Pull mode intervals                 |
| `SCHEDULED_TASKS_ENABLED`                                           | true                                 | Enable cron dispatch                |
| Multi-provider keys: `GLM_*`, `MINIMAX_*`, `DEEPSEEK_*`, `OPENAI_*` | --                                   | Additional LLM provider credentials |

## Service Layer

| Service                                                                                                              | File                                 | Purpose                              |
| -------------------------------------------------------------------------------------------------------------------- | ------------------------------------ | ------------------------------------ |
| `BackendClient`                                                                                                      | `backend_client.py`                  | HTTP client to Backend API           |
| `ExecutorClient`                                                                                                     | `executor_client.py`                 | HTTP client to Executor containers   |
| `ContainerPool`                                                                                                      | `container_pool.py`                  | Docker container pool management     |
| `ConfigResolver`                                                                                                     | `config_resolver.py`                 | Multi-provider credential resolution |
| `RunPullService`                                                                                                     | `run_pull_service.py`                | Background run polling and dispatch  |
| `TaskService`                                                                                                        | `task_service.py`                    | Task business logic                  |
| `CallbackService`                                                                                                    | `callback_service.py`                | Callback forwarding                  |
| `WorkspaceManager`                                                                                                   | `workspace_manager.py`               | Workspace CRUD                       |
| `WorkspaceExportService`                                                                                             | `workspace_export_service.py`        | Workspace archival to S3             |
| `StorageService`                                                                                                     | `storage_service.py`                 | S3 operations                        |
| `CleanupService`                                                                                                     | `cleanup_service.py`                 | Workspace cleanup                    |
| `ComputerService`                                                                                                    | `computer_service.py`                | Computer use forwarding              |
| `ScheduledTaskDispatchService`                                                                                       | `scheduled_task_dispatch_service.py` | Cron task dispatch                   |
| Stagers: `SkillStager`, `PluginStager`, `AttachmentStager`, `ClaudeMdStager`, `SlashCommandStager`, `SubAgentStager` | Various                              | Asset staging for executor           |

## Schemas

| Schema File             | Purpose                       |
| ----------------------- | ----------------------------- |
| `task.py`               | Task request/response         |
| `callback.py`           | Callback payloads             |
| `computer.py`           | Computer use schemas          |
| `memory.py`             | Memory operation schemas      |
| `schedule.py`           | Schedule schemas              |
| `user_input_request.py` | User input schemas            |
| `workspace.py`          | Workspace schemas             |
| `response.py`           | Standardized response wrapper |

## Testing and Quality

- **Framework**: pytest + pytest-asyncio + pytest-cov
- **Test directory**: `tests/`
- **36 test files** -- most comprehensive test coverage in the project:
  - API tests: `test_tasks_api.py`, `test_executor_api.py`, `test_callback_service.py`, etc.
  - Service tests: `test_run_pull_service.py`, `test_backend_client.py`, `test_executor_client.py`, etc.
  - Stager tests: `test_skill_stager.py`, `test_plugin_stager.py`, `test_attachment_stager.py`, etc.
  - Infrastructure: `test_container_pool.py`, `test_workspace_manager.py`, `test_storage_service.py`
  - Config: `test_config_resolver.py`, `test_pull_schedule_config.py`
  - Conftest: `conftest.py` with shared fixtures

## FAQ

**Q: How does container pool management work?**
A: `ContainerPool` manages a pool of Docker containers, reusing them when possible. Containers are created with the executor image, workspace mounted, and environment variables injected.

**Q: How does multi-provider support work?**
A: `ConfigResolver` checks the run's model config, resolves the appropriate provider credentials (Anthropic, GLM, MiniMax, DeepSeek, OpenAI), and injects them as environment variables into the executor container. The executor uses `ANTHROPIC_API_KEY` and `ANTHROPIC_BASE_URL` universally.

**Q: What happens on restart?**
A: APScheduler uses in-memory job storage -- scheduled jobs are lost on restart. The pull-based architecture ensures tasks are re-discovered from Backend's persistent queue.

## Related Files

- `pyproject.toml` -- Dependencies
- `app/main.py` -- FastAPI app factory
- `app/core/settings.py` -- Extensive configuration
- `app/core/lifespan.py` -- Startup/shutdown lifecycle
- `app/scheduler/` -- Scheduling system
- `app/services/` -- Business logic layer
- `app/api/v1/__init__.py` -- Router registrations
- `tests/` -- Comprehensive test suite
