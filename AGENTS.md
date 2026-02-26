# AGENTS.md

This file provides guidance for AI coding agents working with code in this repository.

## Project Overview

Poco is a multi-service AI agent execution platform that orchestrates Claude AI agents to perform coding tasks. The system consists of four main components:

- **Frontend** (Next.js 16) - Web UI for task management and monitoring
- **Backend** (FastAPI) - API server, database management, and session orchestration
- **Executor** (FastAPI + Claude Agent SDK) - Agent execution engine with hook-based extensibility
- **Executor Manager** (FastAPI + APScheduler) - Task scheduling and dispatch service

## Architecture Flow

1. User creates task via Frontend
2. Executor Manager receives task, creates session via Backend
3. Executor Manager schedules task with APScheduler
4. Task Dispatcher sends task to Executor with callback URL
5. Executor runs Claude Agent SDK with configured hooks
6. Hooks send progress callbacks to Executor Manager during execution
7. Executor Manager forwards callbacks to Backend for persistence
8. Frontend polls Backend for session status updates

## Development Commands

### Frontend (Next.js)

```bash
cd frontend
pnpm install        # Install dependencies
pnpm dev            # Development server
pnpm build          # Build for production
pnpm start          # Start production server
pnpm lint           # ESLint
pnpm format         # Prettier
```

### Python Services (Backend, Executor, Executor Manager)

Each Python service has its own directory with a `pyproject.toml`. Run commands from within the service directory:

```bash
cd <service>        # backend/, executor/, or executor_manager/
uv sync             # Install dependencies
uv run python -m app.main    # Run development server
# Or directly with uvicorn:
uvicorn app.main:app --reload
```

### Database Migrations (Backend)

```bash
cd backend
uv run -m alembic revision --autogenerate -m "description"  # Autogenerate migration (review and adjust)
uv run -m alembic upgrade head                               # Apply migrations
uv run -m alembic downgrade -1                               # Rollback one migration
```

Guideline: Always start migrations with `--autogenerate` + `upgrade head`, then manually review and adjust the generated revision file. Do not hand-write a migration from scratch as the first step.

### Pre-commit Hooks

```bash
pre-commit install      # Install hooks
pre-commit run --all-files  # Run manually
```

## Technology Stack

**Frontend:** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4, shadcn/ui, pnpm

**Backend Services:** Python 3.12+, FastAPI, Uvicorn, SQLAlchemy 2.0, Alembic, Pydantic Settings, PostgreSQL

**Executor:** claude-agent-sdk, FastAPI

**Executor Manager:** APScheduler, httpx, FastAPI

**Package Managers:** UV for Python, pnpm for Node.js

**Python Package Index:** Tsinghua mirror (<https://pypi.tuna.tsinghua.edu.cn/simple>)

## Code Organization

### Backend (`backend/app/`)

- `api/v1/` - API endpoints (sessions, callback)
- `core/` - Settings, error handlers, middleware, observability
- `models/` - SQLAlchemy models (agent_session, agent_message, tool_execution, usage_log)
- `repositories/` - Data access layer (session_repository, message_repository, etc.)
- `schemas/` - Pydantic schemas (session, callback, response)
- `services/` - Business logic (session_service, callback_service)
- `main.py` - FastAPI app factory

### Executor (`executor/app/`)

- `core/` - AgentExecutor engine, workspace management, callback client
- `hooks/` - Hook system for extensibility (base, manager, callback, todo, workspace)
- `utils/` - Serializer, git platform clients (GitHub, GitLab)
- `schemas/` - Request, response, callback, state schemas and enums
- `api/v1/` - Task execution callback endpoint

### Executor Manager (`executor_manager/app/`)

- `core/settings.py` - Service configuration
- `scheduler/` - APScheduler config and task dispatcher
- `services/` - Backend and executor API clients
- `schemas/` - Task and callback schemas
- `api/v1/` - Task creation, status, and callback endpoints

### Frontend (`frontend/`)

- `app/` - App Router routes, layouts, loading states, proxy routes
- `features/` - Domain modules (chat, projects, capabilities, scheduled-tasks, etc.)
- `components/` - Cross-feature shared components (`ui/`, `shared/`, `shell/`)
- `hooks/` - Cross-feature reusable hooks only
- `lib/` - Framework-agnostic utilities, i18n setup, startup preload logic
- `services/` - Global infrastructure only (e.g., API client); do not put feature business logic here
- `types/` - Global shared types only; feature-specific types stay in each feature

## Key Design Patterns

- **Repository Pattern** - Data access abstraction in `backend/app/repositories/`
- **Service Layer** - Business logic in `backend/app/services/`
- **Hook Pattern** - Plugin-based extensibility in `executor/app/hooks/`
- **Abstract Base Classes** - Git platform clients extend `BaseGitClient`

## Environment Configuration

Each Python service requires a `.env` file. See `backend/.env.example` for the Backend template.

**Backend:** DATABASE_URL, HOST, PORT, CORS_ORIGINS, SECRET_KEY, DEBUG
**Executor Manager:** backend_url, executor_url, callback_base_url, max_concurrent_tasks, callback_token
**Executor:** DEFAULT_MODEL, workspace mount path

## Development Standards

### Code Comments

- All comments must be in English
- Keep comments concise - omit obvious comments
- Follow Google Python Style Guide for docstrings

### Type Annotations (Python 3.12+)

All Python code MUST use proper type annotations. Since we use Python 3.12+, prefer built-in generic types over `typing` module (e.g., `list[T]` instead of `List[T]`, `T | None` instead of `Optional[T]`).

### Backend Layer Separation

**Repositories (`backend/app/repositories/`):**

- Database operations only (CRUD)
- No business logic
- Return SQLAlchemy model instances

**Services (`backend/app/services/`):**

- Business logic
- Transaction management
- Orchestrate multiple repository calls
- **Return types:** SQLAlchemy models OR Pydantic schemas
- **DO NOT** return `dict[str, Any]` - use explicit schemas for type safety

**Database Injection:**

Database sessions MUST be injected via FastAPI dependency injection at the API endpoint level, then passed as parameters to service/repository methods. Each request gets its own db session from the connection pool.

**Schemas (`backend/app/schemas/`):**

- Data transfer objects
- Define API request/response contracts
- Pydantic models for validation and serialization
- **Naming:** `{Entity}{Action}Request` / `{Entity}Response` (e.g., `SessionCreateRequest`, `CallbackResponse`)
- Internal/nested models use descriptive names (e.g., `TaskConfig`, `AgentCurrentState`)

### API Endpoint Exception Handling

Global handlers in `app/core/errors/exception_handlers.py` process:

- `AppException` -> 400 with error code
- `HTTPException` -> preserve status code
- `Exception` -> 500 with stack trace logged

**Rules:**

- **DO NOT** catch `Exception` to re-raise as `HTTPException(500, ...)` (redundant)
- **DO** raise `AppException` for business errors, `HTTPException` for HTTP-specific errors
- **DO NOT** log errors - global handler uses `logger.exception()`

### Frontend Styling

Use Tailwind CSS v4 utility classes with CSS variables. All colors, shadows, and spacing should reference the design system variables in `app/globals.css`:

- Colors: `var(--background)`, `var(--foreground)`, `var(--primary)`, `var(--border)`, etc.
- Shadows: `var(--shadow-sm)`, `var(--shadow-md)`, `var(--shadow-lg)`, etc.
- Border radius: `var(--radius)`

**DO NOT** hardcode colors like `#ffffff` or write raw CSS without using these variables.

### Frontend Internationalization (i18n)

All user-facing text MUST use i18n translations, NOT hardcoded strings:

```tsx
import { useT } from "@/lib/i18n/client";
const { t } = useT();

// ✅ Correct
<Button>{t("sidebar.newTask")}</Button>

// ❌ Wrong
<Button>New Task</Button>
```

Translation files: `frontend/lib/i18n/locales/{lng}/translation.json` | Config: `frontend/lib/i18n/settings.ts`

### Frontend Architecture and Boundaries

Use feature-first organization with internal layering:

- Recommended internal layout for each feature: `api/`, `model/`, `ui/`, `lib/`, `index.ts`
- `api/`: backend calls and DTO mapping only
- `model/`: business state, domain types, feature hooks/actions
- `ui/`: feature UI components/pages
- `lib/`: pure utility functions scoped to the feature
- `index.ts`: public surface of the feature

Boundary rules:

- `app/` should compose feature public APIs and should not import deep internals from other features
- Cross-feature imports should go through `features/<feature>/index.ts` whenever possible
- Do not import from `features/*/services/*`; use `features/*/api/*` instead
- Do not let low-level features depend on shell/container modules (avoid reverse dependencies)

### Frontend Component Standards

- Prefer one primary component per file
- Split large components into container + presentational parts
- If a component exceeds ~300 lines or mixes unrelated responsibilities, split it
- Keep render logic declarative; move heavy data shaping into hooks or `lib/`
- Reuse shared UI primitives from `components/ui` and shared composites from `components/shared`

### Frontend State and Data Flow

- Keep server data access in feature `api` modules
- Keep feature state in feature hooks/context (`model` layer), not in route files
- Avoid duplicated derived state; compute from source state with memoization
- Use optimistic updates only with rollback handling for failures
- Co-locate domain-specific state with the owning feature

### Frontend Type Safety

- No `any` unless absolutely unavoidable; use explicit interfaces/types
- Keep API request/response types near the feature consuming them
- Validate untrusted external input with schema validation (e.g., `zod`) before mutation calls
- Avoid component-to-component type coupling through container modules

### Next.js App Router Conventions

- Default to Server Components; add `"use client"` only when interactivity is required
- Place route-specific loading UI in `loading.tsx`
- Keep route files thin; delegate business logic to feature modules
- Use proxy route `app/api/v1/[...path]/route.ts` for browser-side API forwarding

### Frontend Performance Guidelines

- Dynamic-import heavy viewers/editors and browser-only libraries
- Memoize expensive computations and stable callbacks in hot rendering paths
- Virtualize or paginate long lists when item count is large
- Avoid unnecessary re-renders caused by unstable object/array literals in props

### Frontend Quality Gates

Before submitting frontend changes:

- `pnpm lint` must pass
- `pnpm build` must pass
- Manually verify key flows impacted by changes (create task, chat execution, project switching, capabilities CRUD)

## Linting and Formatting

**Python:**

- Ruff for linting and formatting
- Pyrefly for type checking
- Configured in root `pyproject.toml` and `.pre-commit-config.yaml`

**TypeScript/React:**

- ESLint with Next.js config
- Prettier for formatting
- Configured in `.pre-commit-config.yaml`

## Important Notes

- The workspace mount path in `executor/app/core/engine.py` is hardcoded to `/Users/qychen/01-Develop/toto`

- APScheduler uses in-memory job storage (jobs lost on restart)
- Callback endpoints use token-based authentication
- Git operations support GitHub and GitLab platforms
- All services can run independently for local development
