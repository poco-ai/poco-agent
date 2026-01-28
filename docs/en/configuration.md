# Configuration Guide (Environment Variables)

This project includes 4 services: `backend` / `executor-manager` / `executor` / `frontend`, plus 2 dependencies: `postgres` / `rustfs` (S3-compatible storage).

Below are common environment variables for each service (with meaning and defaults). In production, replace all `change-this-*`, weak passwords, and default secrets.

## Backend (FastAPI)

Required (otherwise it will not start or key features will fail):

- `DATABASE_URL`: PostgreSQL connection string, e.g. `postgresql://postgres:postgres@postgres:5432/poco`
- `SECRET_KEY`: backend secret key (security-related logic)
- `INTERNAL_API_TOKEN`: internal auth token (Executor Manager uses it to call Backend internal APIs)
- `S3_ENDPOINT`: S3-compatible endpoint, e.g. `http://rustfs:9000`
- `S3_ACCESS_KEY` / `S3_SECRET_KEY`: S3 credentials
- `S3_BUCKET`: bucket name (must exist; Compose can create via init container)

Common:

- `HOST` (default `0.0.0.0`), `PORT` (default `8000`)
- `CORS_ORIGINS`: allowed origins list (JSON array), e.g. `[
  "http://localhost:3000",
  "http://127.0.0.1:3000"
]`
- `EXECUTOR_MANAGER_URL`: Executor Manager URL, e.g. `http://executor-manager:8001`
- `S3_PUBLIC_ENDPOINT`: public S3 URL for browser presigned URLs (local: `http://localhost:9000`). If unset, falls back to `S3_ENDPOINT`.
- `S3_REGION` (default `us-east-1`)
- `S3_FORCE_PATH_STYLE` (default `true`, required for MinIO/RustFS)
- `S3_PRESIGN_EXPIRES`: presigned URL expiry in seconds (default `300`)
- `OPENAI_API_KEY`: optional (used for session title generation; disabled if not set)
- `OPENAI_BASE_URL`: optional (custom OpenAI-compatible gateway)
- `OPENAI_DEFAULT_MODEL` (default `gpt-4o-mini`)
- `MAX_UPLOAD_SIZE_MB` (default `100`)

Logging (shared by all three Python services):

- `DEBUG` (default `false`)
- `LOG_LEVEL` (default changes with DEBUG; recommended `INFO`)
- `UVICORN_ACCESS_LOG` (default `false`)
- `LOG_TO_FILE` (default `false`): write logs to local files
- `LOG_DIR` (default `./logs`), `LOG_BACKUP_COUNT` (default `14`)
- `LOG_SQL` (default `false`): log SQLAlchemy SQL (be careful with sensitive data)

## Executor Manager (FastAPI + APScheduler)

Required (otherwise it will not start or cannot dispatch tasks):

- `BACKEND_URL`: Backend URL, e.g. `http://backend:8000`
- `INTERNAL_API_TOKEN`: must match Backend `INTERNAL_API_TOKEN`
- `CALLBACK_BASE_URL`: **must be reachable from executor containers**; Compose default `http://host.docker.internal:8001`
- `EXECUTOR_IMAGE`: executor image name (manager launches it via Docker API)
- `EXECUTOR_PUBLISHED_HOST`: host used to access executor containers mapped to host ports (bare metal: `localhost`; in Compose: `host.docker.internal`)
- `WORKSPACE_ROOT`: workspace root (**must be a host path**, bind-mounted into executor containers)
- `S3_ENDPOINT` / `S3_ACCESS_KEY` / `S3_SECRET_KEY` / `S3_BUCKET`: used to export workspaces to object storage

Execution model (required to run tasks):

- `ANTHROPIC_AUTH_TOKEN`: Claude API token
- `ANTHROPIC_BASE_URL` (default `https://api.anthropic.com`)
- `DEFAULT_MODEL` (default `claude-sonnet-4-20250514`)

Scheduling & pulling:

- `TASK_PULL_ENABLED` (default `true`): whether to pull tasks from Backend run queue
- `MAX_CONCURRENT_TASKS` (default `5`)
- `TASK_PULL_INTERVAL_SECONDS` (default `2`)
- `TASK_CLAIM_LEASE_SECONDS` (default `180`): claim lease duration. It must cover the time from claim to start_run (including skill/attachment staging, launching executor containers, etc.) to avoid duplicate scheduling.
- `SCHEDULE_CONFIG_PATH`: optional TOML/JSON schedule config, treated as source of truth

Workspace cleanup (optional):

- `WORKSPACE_CLEANUP_ENABLED` (default `false`)
- `WORKSPACE_CLEANUP_INTERVAL_HOURS` (default `24`)
- `WORKSPACE_MAX_AGE_HOURS` (default `24`)
- `WORKSPACE_ARCHIVE_ENABLED` (default `true`)
- `WORKSPACE_ARCHIVE_DAYS` (default `7`)
- `WORKSPACE_IGNORE_DOT_FILES` (default `true`)

## Executor (FastAPI + Claude Agent SDK)

Required (when running tasks):

- `ANTHROPIC_AUTH_TOKEN`: Claude API token
- `ANTHROPIC_BASE_URL`: optional (same as above)
- `DEFAULT_MODEL`: required (`executor/app/core/engine.py` reads `os.environ["DEFAULT_MODEL"]`)
- `WORKSPACE_PATH`: workspace mount path (default `/workspace`)

Optional:

- `WORKSPACE_GIT_IGNORE`: extra ignore rules written to `.git/info/exclude` (comma or newline separated)
- `DEBUG` / `LOG_LEVEL` / `LOG_TO_FILE` etc. (same as above)

## Frontend (Next.js)

Frontend now uses a **same-origin API proxy** (`/api/v1/* -> Backend`) by default, so backend URL can be set at **runtime**.

Runtime:

- `BACKEND_URL`: Backend base URL used by the Next.js server to proxy `/api/v1/*` (Compose default: `http://backend:8000`; local dev: `http://localhost:8000`; legacy env: `POCO_BACKEND_URL`)

Optional (build-time only, for direct browser access or static deployment):

- `NEXT_PUBLIC_API_URL`: Backend base URL used by the browser (e.g. `http://localhost:8000`). This variable is inlined by Next.js at build time.

Note: the following variables are also **build-time** and are inlined into the output (see `docker/frontend/Dockerfile` build args):

- `NEXT_PUBLIC_SESSION_POLLING_INTERVAL`: session polling interval (ms, default `2500`)
- `NEXT_PUBLIC_MESSAGE_POLLING_INTERVAL`: message polling interval (ms, default `2500`)

## Postgres (Docker image)

- `POSTGRES_DB` (default `poco`)
- `POSTGRES_USER` (default `postgres`)
- `POSTGRES_PASSWORD` (default `postgres`)
- `POSTGRES_PORT` (default `5432`, host-mapped port)

## RustFS (S3-compatible storage)

Docker Compose uses `rustfs/rustfs:latest` as the local S3-compatible implementation (service name `rustfs`). To replace it with another S3-compatible service, adjust image variables and ensure Backend/Executor Manager `S3_*` are valid.

- `RUSTFS_IMAGE`: storage image (default `rustfs/rustfs:latest`)
- `S3_PORT` (default `9000`)
- `S3_CONSOLE_PORT` (default `9001`)
- `RUSTFS_DATA_DIR`: data directory (default `./oss_data`, host path, bind-mounted to `/data`)
- On Linux, `RUSTFS_DATA_DIR` must be writable. If Docker creates it as `root:root`, you may hit `Permission denied (os error 13)`.
- `S3_ACCESS_KEY` / `S3_SECRET_KEY`: credentials for S3 API (must match rustfs config)
- `S3_BUCKET`: bucket name (default `poco`, can be created via `rustfs-init` profile or console)
