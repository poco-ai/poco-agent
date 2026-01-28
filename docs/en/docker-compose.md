# Docker Compose Quickstart

`docker-compose.yml` includes:

- `backend` (FastAPI)
- `executor-manager` (FastAPI + APScheduler, spawns `executor` containers via Docker API)
- `executor` (debug only; not started by default, manager creates it dynamically)
- `frontend` (Next.js)
- `postgres`
- `rustfs` (default `rustfs/rustfs:latest`, S3-compatible) + `rustfs-init` (optional bucket creation)

## Prerequisites

- Docker Desktop / Docker Engine
- Docker Compose v2 (`docker compose`)
- If GHCR images are private: `docker login ghcr.io`

## Recommended: Bootstrap Script (first run)

For first-time setup, use the script to prepare `.env`, directories, permissions, pull images, and create the bucket:

```bash
./scripts/quickstart.sh
```

The script will:

- Copy `.env.example` -> `.env` if missing
- Detects and writes `DOCKER_GID`; other keys are only written when flags are provided (e.g. `--data-dir` / `--s3-*` / `--cors-origins`)
- Create `oss_data/` and `tmp_workspace/`; tries to chown `oss_data/` to `10001:10001` (RustFS user) by default
- Write `.gitignore` into `oss_data/` and `tmp_workspace/` (content is `*`)
- Pull the executor image and start services by default
- Create `S3_BUCKET` via `rustfs-init`

Common flags:

- `--no-pull-executor`: skip pulling executor image
- `--no-start`: only prepare env and directories
- `--no-init-bucket`: skip bucket creation
- `--no-chown-rustfs`: skip chowning `oss_data/` to `10001:10001`

After running the script, check `.env` and fill required values (e.g. `ANTHROPIC_AUTH_TOKEN`).

If you prefer manual steps, continue below.

## Manual Start (local / self-hosted)

Run in the repo root:

```bash
docker compose up -d
```

By default it pulls `backend` / `executor-manager` / `frontend` from GHCR and Postgres/RustFS images. The `executor` service is not started by default (`debug` profile), but `executor-manager` will start `EXECUTOR_IMAGE` when running tasks (it may auto-pull if missing).

To pin versions (e.g. `v0.1.0`):

```bash
export BACKEND_IMAGE=ghcr.io/poco-ai/poco-backend:v0.1.0
export EXECUTOR_MANAGER_IMAGE=ghcr.io/poco-ai/poco-executor-manager:v0.1.0
export EXECUTOR_IMAGE=ghcr.io/poco-ai/poco-executor:v0.1.0
export FRONTEND_IMAGE=ghcr.io/poco-ai/poco-frontend:v0.1.0

docker compose up -d
```

## Default URLs

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000` (`/docs`)
- Executor Manager: `http://localhost:8001` (`/docs`)
- RustFS(S3): `http://localhost:9000` (Console: `http://localhost:9001`)
- Executor (debug):
  - API: `http://localhost:8002/health`
  - noVNC / code-server: `http://localhost:8081`

Enable debug executor (optional, only if you want direct access):

```bash
docker compose --profile debug up -d executor
```

## Key Notes (important)

1. `executor-manager` needs Docker daemon access:

- Compose mounts `/var/run/docker.sock:/var/run/docker.sock`
- This allows it to create executor containers dynamically

2. Callback URL (Executor -> Executor Manager):

- `CALLBACK_BASE_URL` defaults to `http://host.docker.internal:8001`
- Executors are created outside the compose network, so they call back through host-mapped ports
- Compose adds `host.docker.internal:host-gateway` for `executor-manager`/`executor` (works on Linux too)

3. Workspace directory:

- Compose uses `${PWD}/tmp_workspace` as `WORKSPACE_ROOT`
- The directory is bind-mounted into executor containers at `/workspace`
- `tmp_workspace/` is already in the repo and ignored by git (`tmp_workspace/.gitignore`)

4. RustFS data directory permissions (common on Linux):

- `rustfs` bind-mounts `${RUSTFS_DATA_DIR}` to `/data`
- Default `RUSTFS_DATA_DIR=./oss_data` (repo root)
- RustFS runs as non-root user `rustfs` (UID/GID=10001); if the host directory isn't owned by `10001:10001`, it can fail with:
  `Io error: Permission denied (os error 13)`
- Fix it on the host (example uses repo `oss_data/`):

```bash
mkdir -p oss_data
sudo chown -R 10001:10001 oss_data
```

5. Public URL for RustFS presigned URLs:

- Backend uses `S3_PUBLIC_ENDPOINT` to generate browser-accessible presigned URLs; Compose default is `http://localhost:9000`
- If you access RustFS via a domain or non-9000 port, update `S3_PUBLIC_ENDPOINT`

## Common Operations

View logs:

```bash
docker compose logs -f backend executor-manager
```

Update to latest images (or your specified tags):

```bash
docker compose pull
docker compose up -d
```

Stop:

```bash
docker compose down
```

Stop and remove data (deletes Postgres/object storage volumes):

```bash
docker compose down -v
```

## Configuration

Most configuration is via environment variables (e.g. `ANTHROPIC_AUTH_TOKEN`, `S3_*`, `INTERNAL_API_TOKEN`).

See: `./configuration.md`.

## Optional: auto-create bucket

`rustfs-init` is not started by default (to avoid startup blocking due to OSS image/permission differences). To create `S3_BUCKET` automatically:

```bash
docker compose --profile init up -d rustfs-init
```
