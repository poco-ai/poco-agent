# Configuration Guide (Environment Variables)

This project includes 4 services: `backend` / `executor-manager` / `executor` / `frontend`.

Dependencies:

- `postgres`
- S3-compatible object storage (optional local `rustfs`, or cloud providers like Cloudflare R2)

Below are common environment variables for each service (with meaning and defaults). In production, replace all `change-this-*`, weak passwords, and default secrets.

## Backend (FastAPI)

Required (otherwise it will not start or key features will fail):

- `DATABASE_URL`: PostgreSQL connection string, e.g. `postgresql://postgres:postgres@postgres:5432/poco`
- `SECRET_KEY`: backend secret key (security-related logic)
- `INTERNAL_API_TOKEN`: internal auth token (Executor Manager uses it to call Backend internal APIs)
- `S3_ENDPOINT`: S3-compatible endpoint
  - local rustfs: `http://rustfs:9000`
  - Cloudflare R2: `https://<accountid>.r2.cloudflarestorage.com`
- `S3_ACCESS_KEY` / `S3_SECRET_KEY`: S3 credentials
- `S3_BUCKET`: bucket name (must exist; local rustfs can create via `rustfs-init`; for R2 create it in the dashboard first)

Common:

- `HOST` (default `0.0.0.0`), `PORT` (default `8000`)
- `CORS_ORIGINS`: allowed origins list (JSON array), e.g. `[
  "http://localhost:3000",
  "http://127.0.0.1:3000"
]`
- `EXECUTOR_MANAGER_URL`: Executor Manager URL, e.g. `http://executor-manager:8001`
- `S3_PUBLIC_ENDPOINT`: public S3 URL for browser presigned URLs (local: `http://localhost:9000`). If unset, falls back to `S3_ENDPOINT`.
- `S3_REGION` (default `us-east-1`; Cloudflare R2 usually recommends `auto`)
- `S3_FORCE_PATH_STYLE` (default `true` for MinIO/RustFS; Cloudflare R2 usually recommends `false`)
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
- `EXECUTOR_IMAGE`: executor image name (manager launches it via Docker API). Recommended default: `ghcr.io/poco-ai/poco-executor:lite`
- `EXECUTOR_BROWSER_IMAGE`: optional, executor image with desktop/browser stack (used when `browser_enabled=true`). Recommended: `ghcr.io/poco-ai/poco-executor:full`
- `POCO_BROWSER_VIEWPORT_SIZE`: optional, browser viewport size (affects screenshots and responsive layouts), e.g. `1366x768` / `1920x1080`. The manager passes it through to executor containers (only when `browser_enabled=true`).
- `EXECUTOR_PUBLISHED_HOST`: host used to access executor containers mapped to host ports (bare metal: `localhost`; in Compose: `host.docker.internal`)
- `WORKSPACE_ROOT`: workspace root (**must be a host path**, bind-mounted into executor containers)
- `S3_ENDPOINT` / `S3_ACCESS_KEY` / `S3_SECRET_KEY` / `S3_BUCKET`: used to export workspaces to object storage
  - Cloudflare R2 usually recommends: `S3_REGION=auto`, `S3_FORCE_PATH_STYLE=false`

Execution model (required to run tasks):

- `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN`: configure exactly one credential
  - Prefer `ANTHROPIC_API_KEY` for the official Anthropic API
  - Use `ANTHROPIC_AUTH_TOKEN` only for bearer-token compatible gateways
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

- `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN`: configure exactly one credential
- `ANTHROPIC_BASE_URL`: optional (same as above)
- `DEFAULT_MODEL`: required (`executor/app/core/engine.py` reads `os.environ["DEFAULT_MODEL"]`)
- `WORKSPACE_PATH`: workspace mount path (default `/workspace`)

Optional:

- `WORKSPACE_GIT_IGNORE`: extra ignore rules written to `.git/info/exclude` (comma or newline separated)
- `POCO_BROWSER_VIEWPORT_SIZE`: optional, browser viewport size (affects screenshots and responsive layouts), e.g. `1366x768` / `1920x1080` (only effective when `browser_enabled=true`)
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

## Local RustFS (S3-compatible storage, optional)

`docker-compose.yml` uses `rustfs/rustfs:latest` as the local S3-compatible implementation (service name `rustfs`). If you use Cloudflare R2 (or any external S3-compatible storage), use `docker-compose.r2.yml` and you can ignore this section.

To replace it with another S3-compatible service, adjust image variables and ensure Backend/Executor Manager `S3_*` are valid.

- `RUSTFS_IMAGE`: storage image (default `rustfs/rustfs:latest`)
- `S3_PORT` (default `9000`)
- `S3_CONSOLE_PORT` (default `9001`)
- `RUSTFS_DATA_DIR`: data directory (default `./oss_data`, host path, bind-mounted to `/data`)
- RustFS runs as non-root user `rustfs` (UID/GID=10001). The host directory should be owned by `10001:10001` or you may hit `Permission denied (os error 13)`.
- `S3_ACCESS_KEY` / `S3_SECRET_KEY`: credentials for S3 API (must match rustfs config)
- `S3_BUCKET`: bucket name (default `poco`, can be created via `rustfs-init` profile or console)
